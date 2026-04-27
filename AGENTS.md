# Agent Notes

- This repo intentionally uses a single Flask stack: `app/`, `templates/`, `static/`, `run.py`, and `wsgi.py`.
- Deployments are handled by `.github/workflows/azure-deploy.yml` on pushes to `main`.
- The Azure App Service name is `hk-event-time`, resource group `hk-event-time`, and the public URL is `https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/`.
- If `az` is available and authenticated, verify production with `az webapp log tail --name hk-event-time --resource-group hk-event-time` and `az webapp config show --name hk-event-time --resource-group hk-event-time`.
- Do not reintroduce the removed FastAPI/Next.js duplicate stack unless the deployment architecture is intentionally changed.
