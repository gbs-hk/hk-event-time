# Student Azure access (Epic 14)

Access is configured **remotely** on Entra group [`hk-event-time-student-agents`](https://portal.azure.com/#view/Microsoft_AAD_IAM/GroupDetailsMenuBlade/~/Overview/groupId/9353131a-4e06-42f8-9d04-5d58c86f59b4). If you are in that group, you do **not** need repo scripts or Azure CLI for Epic 14 portal work.

Sign in at [https://portal.azure.com](https://portal.azure.com) with the **guest account** invited to directory `acuhlmanngmail.onmicrosoft.com` (your Gmail/Outlook as B2B guest). Use the links below — they open the correct directory and subscription.

## Portal links

| Story | Task | Link |
|-------|------|------|
| 2.2 | Availability tests / Monitor | [App Insights → Availability](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/providers/microsoft.insights/components/appinsights-hk-event-time/availability) |
| 2.2 | Action groups | [Action groups (RG)](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/providers/Microsoft.Insights/actiongroups) |
| 2.3 | Logs / KQL | [App Insights → Logs](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/providers/microsoft.insights/components/appinsights-hk-event-time/logs) |
| 2.3 | Metric / log alerts | [App Insights → Alerts](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/providers/microsoft.insights/components/appinsights-hk-event-time/alerts) |
| — | Resource group overview | [hk-event-time](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/overview) |

Story **2.1** (`/health`) is code in GitHub only — no Azure portal required.

## If a link shows “access denied”

1. Confirm you accepted the **Azure invitation** email for `acuhlmanngmail.onmicrosoft.com`.
2. In the portal, open **Settings → Directories + subscriptions** and switch to **acuhlmanngmail.onmicrosoft.com**, then retry the same link.
3. Ask a teacher to confirm you are in `hk-event-time-student-agents` and that group RBAC is applied (see [operations.md](operations.md#students-hk-event-time-student-agents)).

Teachers: role matrix and runbook in [operations.md](operations.md).
