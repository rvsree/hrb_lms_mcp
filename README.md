# hrb_lms_mcp

Leave Management MCP server for the HRB chatbot platform - real-time leave
balance/history/approval data that can't come from the RAG knowledge base
(policy documents), served to `hrb_chatbot_service` over the Model Context
Protocol with real app-to-app OAuth2, not a static document.

## For reviewers / new team members (5 minutes)

1. Run it locally (below) and hit the real health endpoint.
2. The Environments and MCP tools tables below - what's actually deployed,
   what's actually callable.
3. [Security](#security) - the real OAuth2 flow, and what it replaced.
4. No architecture diagrams exist for this repo yet, unlike the other 7 -
   a real gap, not an oversight; see `hrb_chatbot_service`'s own
   `docs/agent-reference/RAG-ROADMAP.md` Phase 118 for the deployment
   story instead.

## What this is

A **solo-developer capstone/portfolio project**, not a team-owned service -
no separate platform team, on-call rotation, or change-request process. All
code, AWS infra, and database schema changes are one person, through this
repo's own working branch.

Pure FastMCP server (no FastAPI wrapper) exposing 6 tools over JSON-RPC 2.0:
`get_leave_balance`, `get_leave_history`, `submit_leave_request`,
`get_pending_approvals`, `create_hitl_request`, `get_hitl_status` - each
with its own Pydantic validation model (`src/app/models/`), backed by a
real Postgres database via SQLAlchemy, not mocked.

## Environments

This project has exactly **two** real environments - no dev/staging tier
exists, and never has.

| App | Local | AWS (production) |
| --- | --- | --- |
| **This repo** (`hrb_lms_mcp`) | `http://127.0.0.1:8190` | `https://hrb-lms-mcp.rvsree.dev` |
| Backend (`hrb_chatbot_service`) | `http://127.0.0.1:8093` | `https://hrb-chatbot.rvsree.dev` |
| Frontend (`hrb_chatbot_ui`) | `http://localhost:5173` | `https://hrb-chatbot-ui.rvsree.dev` |

This server is only ever called by `hrb_chatbot_service`'s backend, never
directly by the `hrb_chatbot_ui` frontend.

| | Local | AWS (production) |
| --- | --- | --- |
| **Deployment** | `uvicorn src.app.api.main:app --host 127.0.0.1 --port 8190` | AWS App Runner - one service, no ECS/Fargate, no staging tier, no Multi-AZ |
| **Database** | Local Postgres, database `hr_chatbot` | Neon-hosted Postgres, database `HR_Benefits` - **the same database `hrb_chatbot_service` uses**, different schemas (`hrb_emp_lms`, `hrb_lms_mcp_auth`) |
| **Secrets** | `.env` (gitignored) | AWS Secrets Manager (`hrb-lms-mcp/JWT_SECRET_KEY`, plus the shared `hrb-chatbot/POSTGRES_DB_*` secrets reused read-only) |
| **CI/CD** | n/a | `.github/workflows/deploy.yml` - push to this repo's working branch builds, pushes to ECR, and redeploys App Runner |

Deployed 2026-10-07. One real bug found and fixed along the way: FastMCP's
default Host-header allowlist only accepts `localhost`/`127.0.0.1`, which
rejected every real deployed hostname with a 421 until `mcp_server.py`
explicitly disabled `transport_security`.

## Quick start

```bash
pip install -r requirements.txt
uvicorn src.app.api.main:app --host 127.0.0.1 --port 8190 --reload
curl http://127.0.0.1:8190/hrb_emp_lms/health/app
```

`GET /hrb_emp_lms/health/app` confirms the process is up; `GET
/hrb_emp_lms/health/postgres` additionally confirms a real DB round-trip.

Local database setup: create a Postgres database (default name
`hr_chatbot`), then run `resources/db_scripts/database-setup.sql` and
`db-script-sample-data.sql`.

## MCP tools

| Tool | What it does |
|---|---|
| `get_leave_balance` | Employee's leave balance by type (PTO, sick, FMLA, etc.) for a given year |
| `get_leave_history` | Employee's past leave requests, filterable by date/type/status |
| `submit_leave_request` | Files a new leave request |
| `get_pending_approvals` | A manager's queue of requests awaiting their decision |
| `create_hitl_request` | Escalates to a human-in-the-loop review |
| `get_hitl_status` | Status of an existing HITL escalation |

Protocol: JSON-RPC 2.0 over HTTP, FastMCP streamable-http transport,
stateless (no session ID), endpoint `POST /mcp`. Tools are discovered at
runtime via `tools/list`; `hrb_chatbot_service` is the real MCP client.

## Security

**Real app-to-app OAuth2, client-credentials flow**: `POST /oauth/token`
issues a Bearer JWT, required on every `POST /mcp` call via
`BearerAuthMiddleware`. An `X-API-Key` header shows up in some older
scripts/examples elsewhere as a design precursor - it was never actually
enforced and has been fully replaced by this OAuth2 flow; any example
still showing `X-API-Key` is stale.

Role-based access (employee vs. manager) is handled separately, by the
`manager_id` hierarchy in `hrb_emp_lms.employees` - a different concern
from OAuth2 client scopes, not a second auth layer.

## Tech stack

| Layer | What's actually used |
|---|---|
| Framework | Pure FastMCP (`mcp>=1.2.0,<2` - pinned below 2.x; v2 renamed `FastMCP` to `MCPServer` and changed its import path) |
| Transport | FastMCP streamable-http, stateless mode, JSON responses - no FastAPI wrapper |
| Data | SQLAlchemy ORM over `psycopg[binary]>=3.1` (psycopg v3, not psycopg2) |
| Auth | `pyjwt[crypto]` - OAuth2 Bearer JWT issuing/verification |
| Deployment | AWS App Runner (Docker) |

## If something's broken

- Health: `GET /hrb_emp_lms/health/app` (process up), `GET
  /hrb_emp_lms/health/postgres` (real DB round-trip) - both on the URL
  from the Environments table above.
- Logs: CloudWatch log group `/aws/apprunner/hrb-lms-mcp/<service-id>/application`
  (production), or the terminal running `uvicorn` (local).
- OAuth2 failures: a 401 from `/mcp` means a missing/expired/invalid
  Bearer token - get a fresh one from `/oauth/token`. A 421 means the
  DNS-rebinding Host check regressed - `transport_security` should stay
  disabled in `mcp_server.py`.

## Known gaps

- No architecture diagrams exist for this repo (current-state/target-state/
  deployment), unlike the platform's other 7 repos - not yet built.
- No `ROADMAP.md` phase history exists for this repo.
- Uptime/latency/error-rate/concurrency figures are not tracked anywhere in
  this project - any number claiming otherwise in older doc versions was
  unverified and has been removed, not reported here as unknown.
