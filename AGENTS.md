# Agent Notes

- This repo intentionally uses a single Flask stack: `app/`, `templates/`, `static/`, `run.py`, and `wsgi.py`.
- Deployments are handled by `.github/workflows/azure-deploy.yml` on pushes to `main`.
- The Azure App Service name is `hk-event-time`, resource group `hk-event-time`, and the public URL is `https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/`.
- If `az` is available and authenticated, verify production with `az webapp log tail --name hk-event-time --resource-group hk-event-time` and `az webapp config show --name hk-event-time --resource-group hk-event-time`.
- Do not reintroduce the removed FastAPI/Next.js duplicate stack unless the deployment architecture is intentionally changed.
- Azure DevOps work tracking lives at [gbs-hk / hk-event-time](https://dev.azure.com/gbs-hk/hk-event-time) (Kanban/backlog uses the **Basic** process). Canonical Git remote is GitHub [`gbs-hk/hk-event-time`](https://github.com/gbs-hk/hk-event-time).
- Student access uses **Basic (express)** licensing for the known members of Entra security group [`hk-event-time-student-agents`](https://portal.azure.com/#view/Microsoft_AAD_IAM/GroupDetailsMenuBlade/~/Overview/groupId/9353131a-4e06-42f8-9d04-5d58c86f59b4). Each is also in project **Contributors** and **hk-event-time Team**. Graph materialization of that AAD group into the org failed against the org backing directory (VS860016); adding the same people by identity preserves the intended permissions. If you later align the org’s directory with that tenant, add the group under **Organization settings → Users** and nest it into **Contributors** for easier membership churn.
- To link commits/PRs to work items, use **Project settings → GitHub connections** and authorize the [`gbs-hk/hk-event-time`](https://github.com/gbs-hk/hk-event-time) repository (OAuth; requires org/project admin plus GitHub rights). This does not replace GitHub Actions deploy.
- **Azure DevOps MCP** (same server for all tools): npm package [`@tiberriver256/mcp-server-azure-devops@0.1.45`](https://github.com/Tiberriver256/mcp-server-azure-devops), org `https://dev.azure.com/gbs-hk`, default project `hk-event-time`. **Cursor Azure plugin** (App Service, Monitor, etc.) is separate — see [.cursor/settings.json](.cursor/settings.json).
  - **Cursor:** [.cursor/mcp.json](.cursor/mcp.json) — `mcpServers`; reload under Settings → MCP ([Cursor docs](https://cursor.com/docs)).
  - **VS Code + GitHub Copilot Chat:** [.vscode/mcp.json](.vscode/mcp.json) — `servers` + `type: stdio`; use Agent mode, then MCP: List Servers ([VS Code MCP](https://code.visualstudio.com/docs/copilot/customization/mcp-servers), [Copilot + MCP](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp)).
  - **GitHub Copilot CLI:** [.github/mcp.json](.github/mcp.json) — `mcpServers` + `type: local`; trust the workspace folder when prompted ([Copilot CLI MCP](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)).
  - **Kilo Code:** [kilo.jsonc](kilo.jsonc) — `mcp` → local stdio; Settings → Agent Behaviour → MCP Servers ([Kilo MCP](https://kilo.ai/docs/automate/mcp/using-in-kilo-code)). On Windows for `npx` stdio hosts, prefer `cmd` plus `/c`, `npx`, `-y`, … per Kilo’s platform notes.
  - **OpenAI Codex:** [.codex/config.toml](.codex/config.toml) — `[mcp_servers.azure_devops]`; merge into `~/.codex/config.toml` if your build only reads user config ([Codex MCP](https://developers.openai.com/codex/mcp)).
  - **Auth:** Run [`az login`](https://learn.microsoft.com/cli/azure/authenticate-azure-cli), install the boards extension (`az extension add --name azure-devops`), and use `AZURE_DEVOPS_AUTH_METHOD=azure-cli`. Contributors need access to org `gbs-hk` / project `hk-event-time`. For PAT-only setups, switch to `pat` plus `AZURE_DEVOPS_PAT` in local secrets — never commit tokens.

## Cursor Cloud specific instructions

Single-process Flask app; no Docker Compose or separate database service for local dev (SQLite file `events.db` in the repo root).

### Commands (see [README.md](README.md))

| Task | Command (from repo root, with `.venv` activated) |
| --- | --- |
| Install / refresh deps | `pip install -r requirements.txt` |
| Run dev server | `python run.py` → http://127.0.0.1:5050 |
| Tests | `python -m unittest discover -s tests` |
| Production-style smoke | `gunicorn --bind 127.0.0.1:8000 wsgi:app` (Azure uses port **8000** via `startup.sh`) |

There is no repo-configured linter or CI lint job. Optional: `pip install ruff && ruff check app tests`.

### Gotchas

- **Virtualenv:** Use `/workspace/.venv` (`python3 -m venv .venv`). On fresh Debian/Ubuntu images, `python3 -m venv` fails until `python3.12-venv` is installed (`sudo apt-get install -y python3.12-venv`). CI/deploy pin **Python 3.10** (`runtime.txt`); local **3.12** is fine for development.
- **Long-running server:** Start `python run.py` in a **tmux** session (e.g. `flask-dev-server`), not a one-shot background shell, so it stays up across agent steps.
- **Scheduler:** APScheduler runs only when `FLASK_ENV=production` or in the Flask debug **reloader child** (`WERKZEUG_RUN_MAIN=true`). Local `python run.py` does not run the daily scrape in the parent process; use `POST /api/scrape-now` to populate data (first run can take a few minutes while hitting external sources).
- **Sample data:** `SCRAPE_INCLUDE_SAMPLE=1` by default; events still appear after a scrape, not on a bare `create_all` alone.
- **Env file:** Optional `cp .env.example .env`. Prefer live keys in `app/config.py` over stale keys in `.env.example` that are no longer read.
- **PostgreSQL:** Only needed if `DATABASE_URL` is set; default SQLite needs no extra service.
