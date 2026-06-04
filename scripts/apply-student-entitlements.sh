#!/usr/bin/env bash
# Apply Azure RBAC + Azure DevOps project access for hk-event-time students.
# Run as subscription Owner after: az login && az extension add --name azure-devops
set -euo pipefail

ORG_URL="${ORG_URL:-https://dev.azure.com/gbs-hk}"
PROJECT="${PROJECT:-hk-event-time}"
GROUP_ID="${GROUP_ID:-9353131a-4e06-42f8-9d04-5d58c86f59b4}"
RG_NAME="${RG_NAME:-hk-event-time}"
APP_NAME="${APP_NAME:-appinsights-hk-event-time}"
WEBAPP_NAME="${WEBAPP_NAME:-hk-event-time}"

# Entra group members (must match hk-event-time-student-agents)
STUDENT_EMAILS=(
  ezraboehm07@gmail.com
  ferdinand.schoenfels@gmail.com
  jonahbusch@web.de
  LeoZille@outlook.de
)

# GitHub handles with push access (add org/repo collaborator manually if gh lacks admin:org)
GITHUB_USERNAMES=(
  ezraboehm07
  jonahbusch
)

SUB="$(az account show --query id -o tsv)"
RG="/subscriptions/${SUB}/resourceGroups/${RG_NAME}"
APP="${RG}/providers/Microsoft.Web/sites/${WEBAPP_NAME}"
WS="$(az monitor app-insights component show -g "$RG_NAME" -a "$APP_NAME" --query workspaceResourceId -o tsv)"
AI="${RG}/providers/microsoft.insights/components/${APP_NAME}"

assign_role() {
  local role="$1" scope="$2"
  az role assignment create \
    --assignee-object-id "$GROUP_ID" \
    --assignee-principal-type Group \
    --role "$role" \
    --scope "$scope" \
    >/dev/null 2>&1 || true
}

echo "== Azure RBAC for Entra group ${GROUP_ID} =="
for role in Reader "Monitoring Reader" "Monitoring Contributor" "Load Test Owner" "Website Contributor" "Log Analytics Contributor"; do
  assign_role "$role" "$RG"
done
assign_role Reader "/subscriptions/${SUB}"
assign_role "Application Insights Component Contributor" "$AI"
assign_role "Monitoring Contributor" "$AI"
assign_role "Log Analytics Reader" "$WS"
assign_role "Log Analytics Contributor" "$WS"
assign_role "Website Contributor" "$APP"
assign_role "Monitoring Metrics Publisher" "$APP"

echo "== Azure DevOps (${ORG_URL}, project ${PROJECT}) =="
az devops configure --defaults organization="$ORG_URL" project="$PROJECT" >/dev/null

CONTRIB="$(az devops security group list --project "$PROJECT" -o json | python3 -c "
import json,sys
for g in json.load(sys.stdin)['graphGroups']:
    if g['displayName']=='Contributors': print(g['descriptor'])
")"
TEAM="$(az devops security group list --project "$PROJECT" -o json | python3 -c "
import json,sys
for g in json.load(sys.stdin)['graphGroups']:
    if g['displayName']=='${PROJECT} Team': print(g['descriptor'])
")"
BUILD="$(az devops security group list --project "$PROJECT" -o json | python3 -c "
import json,sys
for g in json.load(sys.stdin)['graphGroups']:
    if g['displayName']=='Build Administrators': print(g['descriptor'])
")"

for email in "${STUDENT_EMAILS[@]}"; do
  echo "  ADO: ${email}"
  az devops security group membership add --group-id "$CONTRIB" --member-id "$email" >/dev/null 2>&1 || true
  az devops security group membership add --group-id "$TEAM" --member-id "$email" >/dev/null 2>&1 || true
  az devops security group membership add --group-id "$BUILD" --member-id "$email" >/dev/null 2>&1 || true
  az devops user add --license-type advanced --email "$email" --send-email false >/dev/null 2>&1 || true
done

echo "== GitHub repo collaborators (optional; needs gh auth with admin:org or repo admin) =="
if command -v gh >/dev/null; then
  for user in "${GITHUB_USERNAMES[@]}"; do
    if gh api "repos/gbs-hk/hk-event-time/collaborators/${user}" -X PUT -f permission=push >/dev/null 2>&1; then
      echo "  GitHub push: ${user}"
    else
      echo "  SKIP GitHub ${user} (grant Write at https://github.com/gbs-hk/hk-event-time/settings/access)"
    fi
  done
else
  echo "  gh not installed; add collaborators in GitHub UI."
fi

echo "Done. Verify IAM: Portal → ${RG_NAME} → Access control → filter hk-event-time-student-agents"
