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
