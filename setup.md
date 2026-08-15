# SessionSpyre — Agent Sandbox Setup

Run a coding agent against this repo with clear limits on what it can access. The checks below show how those limits were tested.

**Target Codebase:** SessionSpyre, a self-hosted session-recording and replay tool. A JavaScript snippet on a customer site captures DOM events with `rrweb` and streams them over WebSockets to Django Channels. The dashboard replays the events.

---

## 1. Codebase inspection — what the agent actually needs

These findings come from `requirements.txt`, `pytest.ini`, `manage.py`, `SessionSpyre/settings/*`, `.env.example`, and `templates/base.html`. Each tool in the Dockerfile maps to one of them.

| Question | Finding |
|---|---|
| Language / runtime | Python 3.12 |
| Package manager | pip, single `requirements.txt` |
| Test framework | pytest + `pytest-django` + `pytest-playwright` |
| Local services | **PostgreSQL only.** `development.py` hardcodes `django.db.backends.postgresql` with no SQLite fallback, so migrations and tests need a real Postgres instance. Redis appears in `prod.py`, but development uses `InMemoryChannelLayer`, so Redis is **not** installed. |
| Env vars / credentials referenced | `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (`.env.example`); `DATABASE_URL` + `REDIS_URL` in prod only |
| Which can be mocked or omitted | All of them. Postgres runs inside the container, using throwaway credentials defined by the sandbox. `DATABASE_URL` and `REDIS_URL` apply only to production and are omitted. No real credentials enter the image. |
| Build / run commands the repo defines | `manage.py migrate`, `manage.py collectstatic`, `daphne SessionSpyre.asgi:application` (ASGI; Channels overrides `runserver`) |
| Smallest folder safely mountable | The repo root. The agent edits `session_tracker/`, `templates/`, `SessionSpyre/settings/`, and `tests/`, while pytest resolves from the root-level `pytest.ini`. Nothing above the repo root is needed. |
| Does the agent need network? | **Yes, for two reasons.** See §5 for the test results. |

Those findings account for every included tool: `postgresql` because there is no SQLite fallback; Playwright and Chromium for the browser-driven tests; `nodejs` and `npm` only to install Claude Code; `git` for diffs and history; `curl` and `ca-certificates` for package installation and egress checks; and `procps` to inspect the background server.

---

## 2. Build

> Run all host commands from the repo root in **Windows PowerShell** (PowerShell 7+) with Docker Desktop running. Check Docker first with `docker --version` and `docker info`.

```powershell
docker build -t sessionspyre .
```

Create the persistent volumes once:

```powershell
docker volume create sessionspyre-pgdata
docker volume create sessionspyre-claude-auth
```

---

## 3. Run

This command starts the sandbox and opens a shell at `/workspace`. Everything after that runs *inside* the container.

```powershell
docker run -it --rm -p 8000:8000 `
  -v sessionspyre-pgdata:/var/lib/postgresql `
  -v sessionspyre-claude-auth:/claude-auth `
  -v "${PWD}:/workspace" `
  sessionspyre bash
```

**Mounted path:** `${PWD}` (the repo root) maps to `/workspace`. No other host path is mounted.

> **Use PowerShell, not Git Bash.** Git Bash rewrites the container path `/workspace` as a Windows path. The bind mount then lands in the wrong place, and the agent's edits do not reach the host. If you must use Git Bash, prefix the command with `MSYS_NO_PATHCONV=1`.

Before opening the shell, the entrypoint starts Postgres, creates the app role and database if they do not exist (idempotently), then runs `migrate` and `collectstatic`. `--rm` deletes the container when it exits. Persistent data stays on the mounted volumes.

---

## 4. Filesystem boundaries

| Path | Backing | Lifetime | Why |
|---|---|---|---|
| `/workspace` | bind mount to repo root | **persists** | The only exposed host path. Source edits must survive. |
| `/var/lib/postgresql` | volume `sessionspyre-pgdata` | persists | Recorded sessions and accounts survive container exit. |
| `/claude-auth` | volume `sessionspyre-claude-auth` | persists | Agent login survives restarts. |
| `/tmp`, `/root`, `/usr` | container layer | **ephemeral** | Scratch files, caches, and bytecode are destroyed by `--rm`. |

### Verifying the boundary

From the container shell:

```bash
ls -la /root/.ssh; echo "---"; ls -la /workspace/.env; echo "---"; ls /tmp
```

```
total 12
drwx------ 2 root root 4096 Aug 14 22:14 .
drwx------ 1 root root 4096 Aug 15 01:54 ..
---
-rwxrwxrwx 1 root root 249 May 28 02:50 /workspace/.env
---
```

- `/root/.ssh` is **empty**. It belongs to the container, not the host. `/root/.aws`, `/host`, `/mnt/c`, and `/c/Users/jimmy` do not exist in the container.
- `/workspace/.env` **is** readable. This is a known gap covered in Q6.
- `/tmp` is empty at start.

---

## 5. Network mode

Tests confirmed that this project cannot run fully isolated because it has two network requirements.

### Locked-down mode — `--network none`

Add `--network none` for tasks that do not need the internet, such as static analysis, code review, unit tests, or documentation. Check egress from inside the container:

```bash
curl -sS --max-time 5 https://api.anthropic.com; echo "curl exit: $?"
curl -sS --max-time 5 https://pypi.org; echo "curl exit: $?"
```

The captured output confirms that **outbound requests fail**:

```
curl: (6) Could not resolve host: api.anthropic.com
curl exit: 6
curl: (6) Could not resolve host: pypi.org
curl exit: 6
```

### Why the default is `bridge`, not `none`

The default network is required for two reasons:

1. **Claude Code needs `api.anthropic.com`.** The agent cannot start when egress is blocked.
2. **The dashboard loads its frontend from public CDNs.** `templates/base.html` pulls Tailwind, htmx, Alpine, and rrweb-player from `cdn.jsdelivr.net`, `unpkg.com`, and `cdnjs.cloudflare.com`. With `--network none` those never load, so every htmx-driven control is dead. Running the browser smoke test with egress blocked fails exactly there:

```
E  playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
E    - waiting for locator("#name") to be visible

SMOKE_RESULT_JSON={"status": "failed", "completed_steps": ["user_registered", "user_logged_in"],
"failed_step": "site_creation", ...}
```

Registration and login pass because the server renders those pages. Site creation then fails because the htmx "Add New Site" button never loads. This shows exactly what breaks without egress and exposes the supply-chain dependency described in Q6.

**Current setting:** the default `bridge` network with only port `8000` published. Outbound access is unrestricted. Q6 covers this remaining gap and its proposed fix.

---

## 6. Smoke test

### 6a. Environment check

```bash
python manage.py check && python manage.py showmigrations session_tracker
```

```
System check identified no issues (0 silenced).
session_tracker
 [X] 0001_initial
```

### 6b. Agent smoke test

Launch the agent from the container shell:

```bash
claude
```

Prompt given to the agent:

```
Start the app with daphne on port 8000, then run tests/test_sessionspyre_smoke_test.py
and report whether it passed.
```

The test drives the real UI end to end in headless Chromium. It registers an account, logs in, creates a site, opens the Install Code modal, copies the tracking snippet through the clipboard, injects it into a temporary copy of the todo app, records a session, then opens the session and confirms that the rrweb player renders it.

Captured agent session output:

```
● Server is up and responding with 200. Now let's run the smoke test.

● Bash(python3 -m pytest tests/test_sessionspyre_smoke_test.py -v 2>&1 | tail -100)
  ⎿  ============================= test session starts ==============================
     platform linux -- Python 3.12.14, pytest-8.3.3, pluggy-1.5.0 -- /usr/local/bin/python3
     cachedir: .pytest_cache
     … +11 lines (ctrl+o to expand)

● The smoke test passed (1 passed in 7.34s). Daphne is running in the background on port 8000
  (PID logged, output in /tmp/claude-0/-workspace/.../scratchpad/daphne.log) — the full
  registration → login → site creation → snippet injection → recording → playback flow
  completed successfully.
```

### 6c. Confirming output persisted, and that nothing was written outside `/workspace`

`docker diff` lists changes to the container layer. It excludes bind mounts and volumes, so **every listed path is a write outside the project mount**:

```
=== changed paths grouped by top-level dir ===
Count Name
----- ----
  143 usr          # .pyc bytecode caches
   11 root         # Chromium NSS cert db + playwright runtime
    5 run
    4 tmp          # /tmp/daphne.log, /tmp/sessionspyre_todo_app_*/todo-app.html
    4 var
    1 claude-auth

=== any change under /workspace? ===
0

=== any host path escape (/root, /home)? ===
(only /root/.pki and /root/.cache/ms-playwright — both container-local)
```

Every write outside `/workspace` went to `/tmp`, `/root`, or `/usr` inside the disposable container layer and is destroyed by `--rm`. No host path outside the repo was touched. The agent's persistent output, including source edits and `staticfiles/`, appeared on the host at `C:\Users\jimmy\PycharmProjects\SessionSpyre`, confirming that the bind mount worked.

---

## 7. Security decisions

**1. Why did you mount only this folder?**

`/workspace` maps to the repo root and nothing above it. This is the smallest practical unit because pytest resolves from the root-level `pytest.ini`, while the agent works across `session_tracker/`, `templates/`, `SessionSpyre/settings/`, and `tests/`. A narrower mount would break test collection without meaningfully reducing risk.

**The risk this prevents:** my host home directory contains `~/.ssh` keys with push access to this repo's remote, `~/.aws`, browser profiles, and unrelated client projects. Mounting `C:\Users\jimmy` would let a misbehaving or prompt-injected agent read a private key and push to any accessible repo. It could also copy credentials into a file and serve them over the published port. The checks in §4 show that the boundary holds: `/root/.ssh` inside the container is empty, and no host user path is reachable. A bad `rm` command or runaway script can damage only this git-tracked folder.

**2. What did you choose to keep ephemeral?**

`/tmp`, `/root`, and `/usr` remain ephemeral. They hold scratch files, pip and npm caches, Python bytecode, Chromium's NSS certificate database, `daphne.log`, and the temporary `todo-app.html` copies created by the smoke test. The `docker diff` in §6c shows 143 bytecode files, Chromium runtime state, and two log or temporary entries in these locations. They are all reproducible and do not need to persist.

The container is also ephemeral because `--rm` deletes it on exit. This forces every dependency into the Dockerfile instead of leaving manually installed packages in a long-lived container. A teammate therefore gets the same environment.

**3. What did you choose to persist?**

Three paths persist:

- **`/workspace`** (bind mount) contains the source edits.
- **`sessionspyre-pgdata`** stores recorded sessions and accounts. Without it, exiting the container wipes the database and leaves the smoke test with no history to replay.
- **`sessionspyre-claude-auth`** contains only the agent credential. It is `chmod 600` in a named volume and is not baked into an image layer that could be pushed to a registry.

Persistence is limited to these paths. Everything else is ephemeral.

**4. What dependencies did you include in your extended Docker image?**

Each dependency traces back to a finding in §1:

| Dependency | Traced to |
|---|---|
| `python:3.12-slim` + `requirements.txt` | Django 5.1 / Channels / Daphne stack |
| `postgresql` | `development.py` hardcodes the Postgres engine. With no SQLite fallback, migrations and tests need a live server. |
| Playwright + headless **Chromium** (+ ~15 shared libs) | `pytest-playwright` is in `requirements.txt`, and the smoke test is browser-driven. This is the largest addition to the image and the only way to test the recording pipeline. |
| `nodejs` / `npm` | Solely to `npm install -g @anthropic-ai/claude-code` |
| `git` | Agent inspects diffs and history |
| `curl`, `ca-certificates` | Package installation over HTTPS and the egress check in §5 |
| `procps` | Inspecting the backgrounded daphne process |

The starter image included **`nano`** and **`opencode-ai`**, but both were removed. The agent uses its own editing tools instead of a terminal editor, and a second agent is unnecessary. **`ngrok`** remains even though the agent does not need it. SessionSpyre's tracking script runs on *external* sites, so testing that function requires a public origin. If the sandbox is later limited to agent tasks, `ngrok` should be removed first.

Chromium's OS libraries are listed explicitly. The alternative, `playwright install --with-deps`, assumes Ubuntu and fails on Debian trixie while looking for `ttf-unifont` and `ttf-ubuntu-font-family`.

**5. What did your smoke test prove?**

The smoke test confirmed three boundaries at the same time.

- **The filesystem boundary held during real work.** The agent started a server, ran migrations, wrote temporary files, and drove a browser. `docker diff` (§6c) shows **zero** changes under `/workspace` in the container layer because every write there passed through the bind mount to the host. Other writes stayed under `/tmp`, `/root`, and `/usr` in the disposable layer. Nothing reached a host path outside the repo.
- **The sandbox is self-sufficient.** Postgres, Django, Channels, and Chromium all ran in the container with only `/workspace` mounted from the host. The test registered a user, wrote to the database, opened a WebSocket, recorded a session, and replayed it.
- **The persistence split works as intended.** Persistent output reached the host repo. Scratch output did not and disappeared with `--rm`.

The test in §5 also confirmed the *network* boundary. With `--network none`, the same test fails at the expected step instead of silently degrading.

**6. What risks remain?**

**Third-party CDN scripts in the replay dashboard are the most serious project-specific risk.** `templates/base.html` loads Tailwind, htmx, Alpine, `alpine-morph`, and `rrweb-player` from `cdn.jsdelivr.net`, `unpkg.com`, and `cdnjs.cloudflare.com`. Several use unpinned versions: `htmx.org@latest`, `alpinejs@3.x.x`, and `rrweb-player@latest`. These scripts run on the page that renders **recorded user sessions**, which contain other people's form input and browsing behaviour. A compromised CDN or malicious `@latest` release could access the replay data and the logged-in dashboard session, then send that data to any host. This attack would not require agent involvement. *Mitigation:* store the scripts locally, as the project already does with `js/vendor/rrweb.min.js`, or pin exact versions with Subresource Integrity hashes. Combine this with the egress allowlist below so an injected script cannot send data elsewhere.

Other risks:

- **Unrestricted outbound network.** §5 shows that `--network none` blocks egress, but the agent needs `api.anthropic.com` and the UI needs the CDN hosts. The default `bridge` network therefore remains open, and anything in the container can reach any host. *Mitigation:* use a proxy sidecar or a `--network` allowlist limited to `api.anthropic.com` and the three CDN hosts. Then rerun the §5 curl check to confirm that every other destination remains blocked.
- **`.env` and `.git` are readable at `/workspace`.** `.dockerignore` excludes them from the image but does not affect the bind mount, as verified in §4. With open egress, a prompt-injected agent could read `.env` and send it elsewhere. *Mitigation:* move real secrets out of the repo root and treat the current development values as compromised by default.
- **Secrets are baked into the image.** `SECRET_KEY` and `DB_PASSWORD` use `ENV` instructions, which Docker flags during the build as `SecretsUsedInArgOrEnv`. The values are currently disposable, but the image must not be pushed to a shared registry. *Mitigation:* pass them at runtime with `--env`.
- **Everything runs as root in one container.** The agent, web server, and Postgres share a root-owned namespace. There is no privilege separation between the agent and the session data it can read. *Mitigation:* add a non-root `USER` and run Postgres under its own account.
- **The agent can rewrite git history.** Write access to `/workspace` includes `.git`, so the remote is the recovery point. *Mitigation:* commit before giving work to an agent so a destructive rewrite can be recovered from the remote.
