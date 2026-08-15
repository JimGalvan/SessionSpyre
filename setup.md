# SessionSpyre — Agent Sandbox Setup

How to run a coding agent against this repo safely: what it can reach, what it cannot, and how those boundaries were verified.

**Target Codebase:** SessionSpyre — a self-hosted session-recording and replay tool. A JavaScript snippet embedded on a customer site captures DOM events with `rrweb`, streams them over WebSockets into Django Channels, and a dashboard replays them.

---

## 1. Codebase inspection — what the agent actually needs

Findings from `requirements.txt`, `pytest.ini`, `manage.py`, `SessionSpyre/settings/*`, `.env.example`, and `templates/base.html`. Every tool in the Dockerfile traces back to one of these lines.

| Question | Finding |
|---|---|
| Language / runtime | Python 3.12 |
| Package manager | pip, single `requirements.txt` |
| Test framework | pytest + `pytest-django` + `pytest-playwright` |
| Local services | **PostgreSQL only.** `development.py` hardcodes `django.db.backends.postgresql` with no SQLite fallback, so the agent cannot run migrations or tests without a real Postgres. Redis appears in `prod.py` but dev uses `InMemoryChannelLayer`, so Redis is **not** installed. |
| Env vars / credentials referenced | `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (`.env.example`); `DATABASE_URL` + `REDIS_URL` in prod only |
| Which can be mocked or omitted | All of them. Postgres runs inside the container, so the credentials are throwaway values the sandbox itself defines. `DATABASE_URL`/`REDIS_URL` are prod-only and omitted entirely. No real credential enters the image. |
| Build / run commands the repo defines | `manage.py migrate`, `manage.py collectstatic`, `daphne SessionSpyre.asgi:application` (ASGI — Channels overrides `runserver`) |
| Smallest folder safely mountable | The repo root. The agent edits `session_tracker/`, `templates/`, `SessionSpyre/settings/`, and `tests/`, and pytest resolves from `pytest.ini` at the root — so the root is the smallest coherent unit. Nothing above it is needed. |
| Does the agent need network? | **Yes, but only for two specific reasons** — see §5. This was measured, not assumed. |

Tools chosen from those findings: `postgresql` (no SQLite fallback), Playwright + Chromium (the test suite is browser-driven), `nodejs`/`npm` (only to install Claude Code), `git` (diffs and history), `curl` + `ca-certificates` (package installs, egress checks), `procps` (inspecting the background server).

---

## 2. Build

> All host commands are **Windows PowerShell** (PowerShell 7+), run from the repo root, with Docker Desktop running. Verify Docker first with `docker --version` and `docker info`.

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

The main entry point. Starts the sandbox and drops you into a shell at `/workspace`, so everything afterwards runs *inside* the container.

```powershell
docker run -it --rm -p 8000:8000 `
  -v sessionspyre-pgdata:/var/lib/postgresql `
  -v sessionspyre-claude-auth:/claude-auth `
  -v "${PWD}:/workspace" `
  sessionspyre bash
```

**Mounted path:** `${PWD}` (the repo root) → `/workspace`. Nothing else from the host is mounted.

> **Use PowerShell, not Git Bash.** Git Bash rewrites the container-side `/workspace` into a Windows path, so the bind mount silently lands somewhere useless and the agent's edits never reach the host. If you must use Git Bash, prefix the command with `MSYS_NO_PATHCONV=1`.

Before handing over the shell, the entrypoint starts Postgres, creates the app role/database if absent (idempotent), and runs `migrate` and `collectstatic`. `--rm` deletes the container on exit; everything worth keeping lives on the volumes.

---

## 4. Filesystem boundaries

| Path | Backing | Lifetime | Why |
|---|---|---|---|
| `/workspace` | bind mount → repo root | **persists** | The only host path exposed. Source edits must survive. |
| `/var/lib/postgresql` | volume `sessionspyre-pgdata` | persists | Recorded sessions and accounts survive container exit. |
| `/claude-auth` | volume `sessionspyre-claude-auth` | persists | Agent login survives restarts. |
| `/tmp`, `/root`, `/usr` | container layer | **ephemeral** | Scratch files, caches, bytecode — destroyed by `--rm`. |

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

- `/root/.ssh` is **empty** — container-local, not the host's SSH folder. `/root/.aws`, `/host`, `/mnt/c`, and `/c/Users/jimmy` do not exist in the container.
- `/workspace/.env` **is** readable — a known gap, see Q6.
- `/tmp` is empty at start.

---

## 5. Network mode

Egress was **measured**, not assumed. This project has two hard requirements that make full isolation impossible, and both were proven by experiment.

### Locked-down mode — `--network none`

Add `--network none` for any task that does not need the internet (static analysis, reading code, unit tests, docs). Egress check from inside the container:

```bash
curl -sS --max-time 5 https://api.anthropic.com; echo "curl exit: $?"
curl -sS --max-time 5 https://pypi.org; echo "curl exit: $?"
```

Copy-pasted output — **outbound requests fail**:

```
curl: (6) Could not resolve host: api.anthropic.com
curl exit: 6
curl: (6) Could not resolve host: pypi.org
curl exit: 6
```

### Why the default is `bridge`, not `none`

Two measured constraints:

1. **Claude Code needs `api.anthropic.com`.** With egress blocked the agent cannot start at all.
2. **The dashboard loads its frontend from public CDNs.** `templates/base.html` pulls Tailwind, htmx, Alpine, and rrweb-player from `cdn.jsdelivr.net`, `unpkg.com`, and `cdnjs.cloudflare.com`. With `--network none` those never load, so every htmx-driven control is dead. Running the browser smoke test with egress blocked fails exactly there:

```
E  playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
E    - waiting for locator("#name") to be visible

SMOKE_RESULT_JSON={"status": "failed", "completed_steps": ["user_registered", "user_logged_in"],
"failed_step": "site_creation", ...}
```

Registration and login pass (server-rendered), then site creation dies because the htmx "Add New Site" button never loaded. That failure is useful evidence: it maps the exact blast radius of blocking egress, and it exposes a real supply-chain dependency documented in Q6.

**Current setting:** default `bridge`, only port `8000` published. Outbound is unrestricted — the largest remaining gap, with the concrete fix in Q6.

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

That test drives the real UI end to end in headless Chromium: registers an account, logs in, creates a site, opens the Install Code modal, copies the tracking snippet through the clipboard, injects it into a throwaway copy of the todo app, generates a recorded session, then opens that session and confirms the rrweb player renders it.

Copy-pasted agent session output:

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

`docker diff` lists changes to the container's own layer. Bind mounts and volumes are excluded from it, so **everything it prints is by definition a write outside the project mount**:

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

Every write outside `/workspace` landed in `/tmp`, `/root`, or `/usr` — all inside the disposable container layer, all destroyed by `--rm`. No host path outside the repo folder was touched. Meanwhile the agent's durable output (source edits, `staticfiles/`) appeared on the host at `C:\Users\jimmy\PycharmProjects\SessionSpyre`, confirming the bind mount carried it through.

---

## 7. Security decisions

**1. Why did you mount only this folder?**

`/workspace` maps to the repo root and nothing above it. That is the smallest coherent unit for this project: pytest resolves from `pytest.ini` at the root, and the agent edits `session_tracker/`, `templates/`, `SessionSpyre/settings/`, and `tests/` together — a narrower mount would break test collection without reducing meaningful risk.

**The risk this prevents:** my host home directory holds `~/.ssh` (keys with push access to this repo's remote), `~/.aws`, browser profiles, and unrelated client projects. If I had mounted `C:\Users\jimmy` instead, a misbehaving or prompt-injected agent could read a private key and push to any repo I have access to, or copy credentials into a file it then serves over the published port. The verification in §4 confirms the boundary holds: `/root/.ssh` inside the container is empty, and no host user path is reachable. Damage from a bad `rm` or a runaway script is bounded by one git-tracked folder.

**2. What did you choose to keep ephemeral?**

`/tmp`, `/root`, and `/usr` — scratch files, pip/npm caches, Python bytecode, Chromium's NSS cert database, `daphne.log`, and the temp copies of `todo-app.html` the smoke test generates. The `docker diff` in §6c shows exactly what lands there: 143 bytecode files, Chromium runtime state, two log/temp entries. All regenerable, none worth persisting.

The container itself is ephemeral by design — `--rm` deletes it on exit. That is deliberate: it forces every dependency to be declared in the Dockerfile rather than hand-installed in a long-lived container, so the environment cannot silently drift from what a teammate would get.

**3. What did you choose to persist?**

Three things, each for a specific reason:

- **`/workspace`** (bind mount) — the actual work product. Source edits are the point.
- **`sessionspyre-pgdata`** — recorded sessions and accounts. Without it, every exit wipes the database and the smoke test has no history to replay.
- **`sessionspyre-claude-auth`** — the agent credential only, `chmod 600` in a named volume, deliberately *not* baked into the image so it never ends up in a layer that could be pushed to a registry.

The distinction that matters: persistence is granted per path for a stated reason, not by default. Everything unlisted is ephemeral.

**4. What dependencies did you include in your extended Docker image?**

Each traceable to a finding in §1:

| Dependency | Traced to |
|---|---|
| `python:3.12-slim` + `requirements.txt` | Django 5.1 / Channels / Daphne stack |
| `postgresql` | `development.py` hardcodes the Postgres engine — no SQLite fallback, so migrations and tests need a live server |
| Playwright + headless **Chromium** (+ ~15 shared libs) | `pytest-playwright` in `requirements.txt`; the smoke test is browser-driven. Largest addition to the image, and the only way to prove the recording pipeline works. |
| `nodejs` / `npm` | Solely to `npm install -g @anthropic-ai/claude-code` |
| `git` | Agent inspects diffs and history |
| `curl`, `ca-certificates` | Package installs over HTTPS; the egress check in §5 |
| `procps` | Inspecting the backgrounded daphne process |

Removed from the starter image: **`nano`** (the agent edits through its own tools, not a terminal editor) and **`opencode-ai`** (a second, unused agent). **`ngrok`** is the one judgment call — the agent does not need it, but SessionSpyre's core function is a tracking script loaded by *external* sites, and verifying that requires a public origin. It stays because it serves a demonstrated project need; if this sandbox were narrowed to agent tasks only, it should be the first thing dropped.

Chromium's OS libraries are listed explicitly rather than via `playwright install --with-deps`, because that flag assumes Ubuntu and fails on Debian trixie looking for `ttf-unifont` and `ttf-ubuntu-font-family`.

**5. What did your smoke test prove?**

Not just that the agent could run a test — it confirmed three specific boundaries were working simultaneously.

- **The filesystem boundary held while doing real work.** The agent started a server, ran migrations, wrote temp files, and drove a browser. `docker diff` (§6c) shows **zero** changes under `/workspace` in the container layer — every write there went through the bind mount to the host — while everything else it touched stayed in `/tmp`, `/root`, and `/usr` inside the disposable layer. Nothing escaped to a host path outside the repo.
- **The sandbox is self-sufficient.** Postgres, Django, Channels, and Chromium all ran in-container. The test registered a user, wrote to the database, opened a WebSocket, recorded a session, and replayed it — with only `/workspace` mounted from the host.
- **The persistence split behaves as designed.** Durable output reached the host repo folder; scratch output did not, and vanished with `--rm`.

The complementary experiment in §5 proved the *network* boundary is real in the other direction: with `--network none`, the same test fails at a precise, explainable point rather than silently degrading.

**6. What risks remain?**

**Third-party CDN scripts execute in the replay dashboard — the most serious project-specific risk.** `templates/base.html` loads Tailwind, htmx, Alpine, `alpine-morph`, and `rrweb-player` from `cdn.jsdelivr.net`, `unpkg.com`, and `cdnjs.cloudflare.com`, and several are unpinned (`htmx.org@latest`, `alpinejs@3.x.x`, `rrweb-player@latest`). Those scripts run on the page that renders **recorded user sessions**, which by design contain other people's form input and browsing behaviour. A compromised CDN or a malicious `@latest` release would execute with full access to that replay data and to the logged-in dashboard session, and could exfiltrate it to any host — an outcome that needs no agent involvement at all. *Mitigation:* vendor these locally the way `js/vendor/rrweb.min.js` already is, or pin exact versions with Subresource Integrity hashes, and pair that with the egress allowlist below so an injected script has nowhere to send data.

Also outstanding:

- **Unrestricted outbound network.** §5 shows `--network none` blocks egress cleanly, but the agent needs `api.anthropic.com` and the UI needs the CDNs, so the default is open `bridge`. Anything running in the container can reach any host. *Mitigation:* a proxy sidecar or `--network` with an allowlist limited to `api.anthropic.com` plus the three CDN hosts, then re-run the §5 curl check to confirm everything else still fails.
- **`.env` and `.git` are readable at `/workspace`.** `.dockerignore` keeps them out of the image but does not apply to the bind mount (verified in §4). Combined with open egress, a prompt-injected agent could read `.env` and POST it outward. *Mitigation:* move real secrets out of the repo root, and treat the current dev values as compromised-by-default.
- **Secrets baked into the image.** `SECRET_KEY` and `DB_PASSWORD` are `ENV` instructions; Docker flags this at build (`SecretsUsedInArgOrEnv`). Throwaway values today, but this image must never be pushed to a shared registry. *Mitigation:* pass them at runtime with `--env` instead.
- **Everything runs as root in one container.** The agent, the web server, and Postgres share a root-owned namespace, so there is no privilege separation between the agent and the session data it can read. *Mitigation:* add a non-root `USER` and run Postgres under its own account.
- **The agent can rewrite git history.** Write access to `/workspace` includes `.git`; the remote is the real backstop. *Mitigation:* commit before handing work to an agent, so any destructive rewrite is recoverable from the remote.
