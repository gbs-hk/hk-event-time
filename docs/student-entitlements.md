# Student entitlements

Students are onboarded through Entra group [`hk-event-time-student-agents`](https://portal.azure.com/#view/Microsoft_AAD_IAM/GroupDetailsMenuBlade/~/Overview/groupId/9353131a-4e06-42f8-9d04-5d58c86f59b4). Azure RBAC is granted to that **group**. Azure DevOps and GitHub access are granted **per person** (the Entra group cannot be nested into DevOps today — see [AGENTS.md](../AGENTS.md)).

## Checklist when adding a student

1. **Entra:** Add the user to `hk-event-time-student-agents` and ensure they accepted the B2B invite to `acuhlmanngmail.onmicrosoft.com`.
2. **Azure RBAC:** Re-run [`scripts/apply-student-entitlements.sh`](../scripts/apply-student-entitlements.sh) (or confirm IAM role assignments on the group — see [operations.md](operations.md#students-hk-event-time-student-agents)).
3. **Azure DevOps:** Add their email to project **Contributors**, **hk-event-time Team**, and **Build Administrators** (the script does this for known addresses; extend the script for new emails).
4. **GitHub:** Grant **Write** on [`gbs-hk/hk-event-time`](https://github.com/gbs-hk/hk-event-time) (Settings → Collaborators, or org team). Known handles: `ezraboehm07`, `jonahbusch` — confirm Ferdinand and Leo’s GitHub usernames and add them.
5. **Portal:** Student signs in with the guest directory; bookmark links in [student-azure-access.md](student-azure-access.md).

## What students can do (by system)

| System | Access |
|--------|--------|
| **Azure Portal** | Monitoring, alerts, App Insights, load tests, App Service **configuration** (app settings) on `hk-event-time` — not subscription Owner |
| **Azure DevOps** | Edit work items and boards (Contributors + Advanced license) |
| **GitHub** | Push to `main`, edit workflows (when Write is granted); deploy secrets stay in Actions |
| **Production code** | Ship via push to `main` — see [operations.md](operations.md) |

Students still **do not** replace the GitHub Actions deploy pipeline for routine app releases; they may use the portal for observability configuration and App Insights-related app settings (Epic 14–16).

## Re-apply all entitlements (teachers)

```bash
az login
az extension add --name azure-devops  # if missing
bash scripts/apply-student-entitlements.sh
```

Requires subscription **Owner** (or User Access Administrator) for role assignments and DevOps Project Collection Administrator (or equivalent) for group membership.
