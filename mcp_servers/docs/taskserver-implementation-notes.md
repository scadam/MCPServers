# TaskServer – Implementation Notes
## Supporting Guidance (Non‑Authoritative)

This document contains **practical implementation notes** and platform‑specific caveats.
It must **not override** the canonical spec.

If there is any conflict:
> **taskserver-spec.md wins**

---

## 1. General Guidance

- Treat TaskServer as the **only orchestrator**
- Providers must be **thin** and system‑of‑record only
- Do not let providers implement cross‑system logic

---

## 2. Widget & Skybridge Notes

- Always populate `structuredContent`
- Keep payloads small (avoid dumping raw API responses)
- Use stable field names; widget JS should not infer structure
- Skybridge HTML should be framework‑free and synchronous

---

## 3. Workday Notes

- Inbox tasks come from `/workers/{id}/inboxTasks`
- Only inbox tasks with `stepType == "Approval"` are approvable
- Non‑approval inbox tasks must be treated as regular tasks
- Approve/reject APIs will fail if stepType is not Approval
- Use integration user’s worker ID in demo mode

---

## 4. ServiceNow Notes

- “My work” spans multiple tables extending `task`
- `sysapproval_approver` is the approvals table
- Approval updates may fail due to:
  - Dictionary read‑only flags
  - Field‑level ACLs
- Comments and work notes are journal fields and require PATCH
- Filtering by `assigned_to` is more reliable than `opened_by`

---

## 5. Salesforce Notes

- OAuth Client Credentials requires a “run‑as” integration user
- Approval work items are `ProcessInstanceWorkitem`
- Approval comments are not the same as Task comments
- Use SOQL defensively; objects differ by org config

---

## 6. Jira Notes

- API token (basic auth) is simplest for demos
- OAuth2 service account works but requires cloudId routing
- Issue transitions require transition ID lookup
- JSM approvals are only present if Service Management is enabled

---

## 7. Error Handling & Debugging

- Provider failures must not break TaskServer
- Partial results are acceptable
- Always surface provider errors in logs, not widgets

---

## End of Implementation Notes
