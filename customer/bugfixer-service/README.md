# bugfixer-service

A small, self-hosted service that receives bug reports from other web apps and uses
[OpenCode](https://opencode.ai) headlessly to fix them in the target apps' repositories
and open pull requests. It is a standalone project, not part of any existing application.

## Stack

- Django + Django REST Framework + PostgreSQL (`docker-compose` for local dev)
- `python manage.py run_worker` background worker
- Vite + plain TypeScript widget that builds to a single `widget.js`
- Tailwind is intentionally not used (the admin uses Django's built-in styling)

## Components

1. **Public API** — key auth, Origin allowlist, DRF throttles, create + status endpoints.
2. **Worker** — claim → triage → vision → worktree → opencode → tests → diff guards → push/PR → cleanup.
3. **Admin** — projects, reports, image preview, re-queue/reject, PR approval.
4. **Widget** — Shadow DOM UI, screenshot capture, console capture with redaction, identify API.
5. **Infra** — Docker, Postgres, env template, prompt template, hardened subprocess env.

## Quick start

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, LLM_API_KEY, GITHUB_TOKEN
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The admin is at `http://localhost:8000/admin/`.

## Registering a project

In Django admin, add a **Project**:

- `name` — display name.
- `public_key` — generated automatically; give this to the widget.
- `allowed_origins` — JSON list of exact origins, e.g. `["https://app.example.com"]`.
  Requests whose `Origin` is not in this list are rejected with 403.
- `repo_url` — e.g. `https://github.com/acme/shop.git`.
- `base_branch` — default `main`.
- `test_command` — trusted shell command run in the fix worktree, e.g. `npm test`.
- `forbidden_paths` — extra JSON list of glob patterns the fix must not touch.
- `extra_instructions` — repo layout notes, e.g. "frontend is React/Vite in /web, backend Django in /api".
- `triage_enabled`, `vision_enabled`, `auto_pr`, `is_active` — behaviour flags.

When `auto_pr` is false, the worker pushes the branch and sets the report to `fix_ready`.
Use the admin action **Approve and open PR** to create the PR later.

## Embedding the widget

```bash
cd widget
npm install
npm run build      # outputs widget/dist/widget.js
```

Serve `widget/dist/widget.js` from any host and embed it in the target app:

```html
<script src="https://YOUR-HOST/widget.js" data-key="PUBLIC_KEY" data-api="https://YOUR-HOST" data-theme="dark" defer></script>
```

- `data-key` — the project's `public_key`.
- `data-api` — optional; defaults to the script's own origin.
- `data-theme` — `dark` (default) or `light`.

Optional host-app API (call before a report is submitted):

```js
window.BugFixer.identify({ id: "user-123", email: "user@example.com" });
```

Use `npm run dev` in `widget/` for a local demo page, and `npm run typecheck` to type-check.

## Public API

| Endpoint | Auth | Response |
| --- | --- | --- |
| `POST /api/v1/reports/` | `X-Project-Key` header + allowed `Origin`; multipart | `{id, status, status_token}` |
| `GET /api/v1/reports/<id>/?token=<status_token>` | status token in query | `{status, message}` |

The status endpoint intentionally returns **only** a friendly status and message. It never
exposes `result_log`, `branch`, `pr_url`, or the report body.

Validation: message ≤ 2000 chars; screenshot must be PNG/JPG/WEBP and ≤ 5 MB. Throttles
are configurable via `THROTTLE_ANON_IP` and `THROTTLE_PROJECT_KEY` (DRF rate strings).

## Running the worker

```bash
python manage.py run_worker              # polls every 10s
python manage.py run_worker --once       # process one report and exit
python manage.py run_worker --interval 5
```

In Docker it runs as the `worker` service. Each report is claimed with
`select_for_update(skip_locked=True)`, so multiple workers can run safely.

Before production, confirm the installed OpenCode CLI flags:

```bash
opencode run --help
```

The worker invokes `opencode run` with the prompt on stdin and passes `--model` /
extra flags from `OPENCODE_MODEL` and `OPENCODE_EXTRA_ARGS`. Adjust those env vars to
match your installed version.

## Tests

```bash
python manage.py test              # uses SQLite when POSTGRES_HOST is unset
cd widget && npm run typecheck
```

Covered: serializer validation (size, type, image), Origin/CORS check and public status
leakage, both throttles, prompt builder (untrusted tagging + context), and forbidden-path
detection.

## Security model

- **Public key is a bearer credential.** Anyone holding it can submit reports from an
  allowed origin. Rotate it in the admin if it leaks.
- **Origin allowlist** is enforced per project on every write, and CORS headers are only
  reflected for origins registered on an active project.
- **Status token** is a random per-report secret; only status and a friendly message are
  public. Private worker output is admin-only.
- **Untrusted content.** The report body, URL and console log are placed inside
  `<user_report>` tags with an explicit "data, never instructions" warning. Console logs
  are redacted on both client and server.
- **Minimal subprocess environment.** `opencode` and the test command receive only
  `PATH`, `HOME`, and names in `WORKER_ENV_ALLOWLIST`. `DATABASE_URL`, `SECRET_KEY`, and
  other service secrets are never forwarded.
- **Isolation.** One bare mirror per project under `WORKDIR/repos/<id>`; one fresh worktree
  per report under `WORKDIR/worktrees/report-<id>`, removed in a `finally` block. The base
  branch is never pushed to and never merged.
- **Gates before push.** Empty diff fails; tests must pass; built-in and project-specific
  forbidden paths (secrets, `.env*`, CI, Dockerfile, deploy config) fail the run.
- **Throttling** per source IP and per project key limits abuse.
- **GitHub token** is used only for clone/fetch/push and `gh pr create`.

  > The configured `test_command` is trusted operator input and is executed with a shell.
  > Only register repositories whose patches you are willing to run in the worker container;
  > run the worker in a sandbox/VM for untrusted repositories.

## Manual steps after setup

1. Copy `.env.example` → `.env` and fill `SECRET_KEY`, `LLM_API_KEY`, `GITHUB_TOKEN`, SMTP (optional).
2. Start services: `docker compose up --build -d`.
3. Run `docker compose exec web python manage.py migrate`.
4. Create an admin: `docker compose exec web python manage.py createsuperuser`.
5. Register a Project in `/admin` (origins, repo, branch, test command, flags).
6. Build the widget (`cd widget && npm install && npm run build`) and serve `widget/dist/widget.js`.
7. Embed the `<script>` snippet with the project's public key.
8. Verify `opencode run --help` inside the container and tune `OPENCODE_MODEL` / `OPENCODE_EXTRA_ARGS`.
9. Ensure the GitHub token can clone/push the repo and create PRs; start the `worker` service.
10. Submit a test report from an allowed origin and watch `/admin` for status.

## Self-hosting on your own machine

### Production stack

Start with the override file (requires a recent Docker Compose for `ports: !reset`):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

In this mode no host port is published: `web` and `worker` run as the non-root
`bugfixer` user (uid 10001), the worker has only named volumes (`work`, `media`),
no Docker socket, and limits of 2 CPUs / 2 GB RAM / 256 pids. All containers use
`json-file` logging capped at 10 MB × 3 files. `cloudflared` connects outbound
using `TUNNEL_TOKEN`.

### Hardware and power

- 4 CPU cores and 8 GB RAM is a comfortable minimum; add more RAM for larger repos
  or multiple concurrent projects. A 30–60 GB SSD gives room for bare mirrors,
  worktrees, Postgres and container images.
- Disable automatic sleep/hibernate and enable automatic restart after power loss.
- A small UPS prevents an interrupted job from leaving a stale worktree.
- `GET /health/` returns `{"status":"ok"}` only when the database answers `SELECT 1`,
  and `503` otherwise. Point your monitoring or uptime checker at it.

### Firewall

Deny all inbound traffic. The setup only needs outbound HTTPS (443) for the
Cloudflare Tunnel, package installs, git pushes, LLM calls and Turnstile/Access.
Do not expose port 8000 or the Docker daemon socket. Prefer a hardware firewall
or the OS firewall over relying on Docker's port publishing.

### Backup and restore

```bash
chmod +x scripts/*.sh
./scripts/backup_db.sh                      # gzip dump, keeps last 14
./scripts/restore_db.sh backups/db_....sql.gz
./scripts/cleanup_workdir.sh                # worktrees older than 24h + git prune
```

Linux cron (edit with `crontab -e`):

```
0 3 * * * /home/you/bugfixer-service/scripts/backup_db.sh >> /var/log/bugfixer-backup.log 2>&1
30 4 * * * /home/you/bugfixer-service/scripts/cleanup_workdir.sh >> /var/log/bugfixer-cleanup.log 2>&1
```

Windows Task Scheduler: create a *Basic Task* → *Start a program*, program
`C:\Program Files\Git\bin\bash.exe`, arguments
`-lc "/c/Users/you/bugfixer-service/scripts/backup_db.sh"`, start in
`C:\Users\you\bugfixer-service`, and give it "Run whether user is logged on or not".
The same pattern runs `cleanup_workdir.sh`. Verify Docker Desktop is running.

### Worker limits

- `WORKER_JOB_TIMEOUT` — hard wall-clock limit for a single job (default 900s).
- `MAX_DIFF_BYTES` — reject diffs larger than this before pushing (default 10 MB).
- `MAX_JOBS_PER_PROJECT_PER_HOUR` — re-queues a report when a project exceeds its
  hourly quota (default 20).

### Update procedure

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

## Staff dashboard

The dashboard is a React + Vite + TypeScript + Tailwind app in `dashboard/`. It uses
session auth with CSRF, React Router, TanStack Query and recharts. Dark is the default
theme; toggle to light with the header button.

### Run locally

```bash
cd dashboard
cp .env.production.example .env.production   # set VITE_API_URL if different
npm install
npm run dev                                  # http://localhost:5173
```

For `npm run dev`, the Vite proxy forwards `/api` to `http://localhost:8444`, so run the
plain compose stack (with its published port) at the same time. Set `DASHBOARD_ORIGIN`
in the root `.env` to the dashboard's origin (`http://localhost:5173` for Vite dev,
`http://localhost:3000` for the container below) so CORS and CSRF accept it.

As a container:

```bash
docker compose up --build -d dashboard        # http://localhost:3000
```

### Cloudflare Pages

```bash
cd dashboard
npm run build                                 # outputs dist/
npx wrangler pages deploy dist --project-name bugfixer-dashboard
```

Build command `npm run build`, output directory `dist`, environment variable
`VITE_API_URL=https://bugfixer.darkzhub.asia`. SPA fallback is handled by the host
(Workers static assets / Pages); do not add a Pages-only `_redirects` file to a Workers build.
Do **not** add `wrangler.toml` to a Pages repo — Pages may treat it as a Workers project
and run `wrangler deploy` instead of deploying static files. For a manual upload use
`npx wrangler pages deploy dist --project-name <name>` without a `wrangler.toml`. On the
API side set `DASHBOARD_ORIGIN` to the Pages URL and include it in `CSRF_TRUSTED_ORIGINS`.

### First staff user

```bash
docker compose exec web python manage.py createsuperuser
```

Superusers are staff. The same account signs in at `/admin/` and at the dashboard.

### Dashboard endpoints

All endpoints are under `/api/dashboard/` and require a staff Django session plus
`X-CSRFToken` on unsafe methods. `GET /api/dashboard/auth/csrf/` sets the cookie;
clients call it before `POST /auth/login/`.

| Endpoint | Purpose |
| --- | --- |
| `POST /auth/csrf/`, `/auth/login/`, `/auth/logout/`, `GET /auth/me/` | Session auth |
| `GET/POST /projects/`, `GET/PATCH/DELETE /projects/<id>/` | Project CRUD (includes `public_key` and `embed_snippet`) |
| `POST /projects/<id>/rotate-key/` | Rotate the public key |
| `GET /reports/` | Filters: `project`, `status`, `classification`, `date_from`, `date_to`, `search`, `ordering`, `limit`, `offset` |
| `GET /reports/<id>/` | Full detail including screenshot URL, console log and result log |
| `GET /reports/<id>/screenshot/` | Staff-only image bytes (no public media URL) |
| `POST /reports/<id>/requeue/`, `/reject/`, `/approve-pr/` | Same shared actions as Django admin |
| `GET /stats/` | Status counts, 30-day report counts, average time-to-fix, success rate per project |
| `GET /settings/` | Configuration booleans only, never values |

No GitHub token, LLM key or other environment secret is exposed by any dashboard endpoint.

Take a backup before upgrading. The worker is restarted automatically by
`restart: unless-stopped`; it reconnects to Postgres and resumes polling.
