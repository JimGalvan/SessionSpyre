#!/bin/bash
set -eu

# DB_NAME/DB_USER/DB_PASSWORD come from the Dockerfile's ENV — fixed at build
# time since Postgres lives in this same container and we own both sides.

# --- Start Postgres (already initialized by the postgresql package) and
# create the app's role/database on first run ---
service postgresql start

until su postgres -c "pg_isready -q"; do
  sleep 1
done

if ! su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\"" | grep -q 1; then
  su postgres -c "psql -c \"CREATE ROLE \\\"$DB_USER\\\" LOGIN PASSWORD '$DB_PASSWORD';\""
fi

if ! su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\"" | grep -q 1; then
  su postgres -c "psql -c \"CREATE DATABASE \\\"$DB_NAME\\\" OWNER \\\"$DB_USER\\\";\""
fi

# --- Django setup ---
cd /workspace
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# --- App server ---
# The default CMD runs daphne as PID 1. An interactive start ("... sessionspyre
# bash") replaces that CMD, so nothing would listen on 8000; background the
# server for those sessions instead. The PID-1 path is left untouched.
if [ "${1:-}" != "daphne" ]; then
  daphne -b 0.0.0.0 -p 8000 SessionSpyre.asgi:application > /tmp/daphne.log 2>&1 &
  for _ in $(seq 30); do
    # Any HTTP response proves the port is accepting; -f would reject a 404.
    curl -s -o /dev/null "http://127.0.0.1:8000/" && break
    sleep 1
  done
  echo "daphne listening on :8000  (log: /tmp/daphne.log)"
fi

# --- Public tunnel (optional) ---
# ngrok is installed in the image but starts only when a token is supplied:
#   docker run ... -e NGROK_AUTHTOKEN=<token> ...
# The agent reads NGROK_AUTHTOKEN itself, so the token never touches disk.
# NGROK_DOMAIN optionally pins a reserved domain instead of a random one.
if [ -n "${NGROK_AUTHTOKEN:-}" ]; then
  if [ -n "${NGROK_DOMAIN:-}" ]; then
    ngrok http 8000 --domain "$NGROK_DOMAIN" --log stdout > /tmp/ngrok.log 2>&1 &
  else
    ngrok http 8000 --log stdout > /tmp/ngrok.log 2>&1 &
  fi
  NGROK_URL=""
  for _ in $(seq 30); do
    NGROK_URL=$(curl -sf http://127.0.0.1:4040/api/tunnels 2>/dev/null \
      | python -c "import sys,json; t=json.load(sys.stdin)['tunnels']; print(t[0]['public_url'] if t else '')" 2>/dev/null || true)
    [ -n "$NGROK_URL" ] && break
    sleep 1
  done
  if [ -n "$NGROK_URL" ]; then
    echo "ngrok tunnel: $NGROK_URL"
  else
    echo "ngrok failed to start - see /tmp/ngrok.log" >&2
  fi
fi

AUTH_DIR=/claude-auth
mkdir -p "$AUTH_DIR" /root/.claude

# A persisted credential means this is NOT the first run: restore it and mark
# onboarding complete so Claude skips the first-run flow (theme, login, trust).
# On the first run there is no credential, so onboarding runs once and the
# background saver below persists the resulting credential.
if [ -f "$AUTH_DIR/.credentials.json" ]; then
  cp "$AUTH_DIR/.credentials.json" /root/.claude/.credentials.json
  chmod 600 /root/.claude/.credentials.json
  echo '{ "hasCompletedOnboarding": true, "projects": { "/workspace": { "hasTrustDialogAccepted": true } } }' > /root/.claude.json
fi

# Save the credential whenever it changes, so login survives any exit. Save
# when the persisted copy is missing (first login) or older than the live one;
# temp-file + chmod + atomic mv keeps the copy safe on the shared volume.
( set +e
  while true; do
    if [ -f /root/.claude/.credentials.json ] && \
       { [ ! -f "$AUTH_DIR/.credentials.json" ] || \
         [ /root/.claude/.credentials.json -nt "$AUTH_DIR/.credentials.json" ]; }; then
      tmp=$(mktemp "$AUTH_DIR/.credentials.json.tmp.XXXXXX")
      cp /root/.claude/.credentials.json "$tmp"
      chmod 600 "$tmp"
      mv -f "$tmp" "$AUTH_DIR/.credentials.json"
    fi
    sleep 5
  done ) &

# exec so the command runs as PID 1 (correct signal handling / reaping).
exec "$@"
