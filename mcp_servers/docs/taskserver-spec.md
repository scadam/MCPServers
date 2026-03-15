# TaskServer MCP – Unified Tasks & Approvals Platform
## Canonical Specification (Authoritative)

---

## 1. Purpose

TaskServer is an **orchestrator MCP server** that provides a **single, unified task and approval experience** across:

- Workday
- ServiceNow
- Salesforce
- Jira

TaskServer aggregates tasks and approvals, renders them via **Copilot side‑panel widgets**, and enforces **explicit human approval** for all write actions.

**Provider MCP servers own system‑of‑record actions.**  
**TaskServer owns orchestration, normalization, UI, approval gating, and auditability.**

This document is the **authoritative contract**.  
If anything conflicts with this spec, **this spec wins**.

---

## 2. Mandatory Platform Contracts

### 2.1 Widget data contract (non‑negotiable)

All widgets **must** read data from:

```
window.openai.toolOutput
```

This is populated **only** from MCP tool responses via `structuredContent`.

Free‑text fallbacks or undocumented behavior **must not** be used.

---

### 2.2 Approval safety

All approve / reject actions are **write actions** and must be:

- Explicitly reviewed by the user
- Explicitly confirmed
- **Nonce‑gated** (single‑use, time‑limited)

No provider may execute an approval without TaskServer authorization.

---

### 2.3 Widget hosting

Widgets are rendered under hashed Copilot widget‑renderer domains.  
Allow‑listing may be required in some environments.

---

## 3. Widget Implementation Standard

### ✅ HTML + Skybridge is mandatory

- **Workday MCP** and **ServiceNow MCP** already use **HTML + Skybridge**
- This implementation is **working today** in Copilot side panels
- This is the **reference and required pattern** for *all* widgets

❌ Do NOT introduce:
- React
- Custom JS frameworks
- Client‑side state stores
- Widget data fallbacks

---

## 4. Why Skybridge

Skybridge is the preferred widget implementation because it is **proven, supported, and aligned with the M365 Copilot extensibility contract today**.  
The existing **HTML + Skybridge widgets in the Workday and ServiceNow MCP servers are already working reliably**, including correct rendering, state handling, and action invocation.

Skybridge provides a thin runtime that cleanly binds MCP `structuredContent` to `window.openai.toolOutput`, avoids undocumented behavior, minimizes client complexity, and reduces risk as the Apps SDK evolves.

For these reasons, **Skybridge is the reference and required widget pattern for TaskServer and all provider MCP servers**.

---

## 5. Architecture

### 5.1 Components

**TaskServer MCP (FastMCP Python)**
- Aggregates tasks and approvals
- Owns widgets
- Owns approval gating + nonce store
- Calls provider MCP servers as a client

**Provider MCP servers (FastMCP Python)**
- Workday MCP
- ServiceNow MCP
- Salesforce MCP
- Jira MCP

---

## 6. Unified Data Model

### 6.1 UnifiedItem

```json
{
  "id": "system:type:id",
  "system": "workday|servicenow|salesforce|jira",
  "kind": "task|approval",
  "title": "string",
  "summary": "string",
  "status": "string",
  "priority": "string|null",
  "dueDate": "ISO8601|null",
  "createdDate": "ISO8601|null",
  "link": "url|null",
  "assignee": "string|null",
  "actions": [
    {
      "actionId": "review|approve|reject|complete|transition",
      "label": "string",
      "requiresReview": true,
      "requiresWriteApproval": true
    }
  ]
}
```

---

## 7. TaskServer MCP – Tool Surface

### 7.1 `taskserver.list_items`
- Fan‑out to all providers
- Normalize to `UnifiedItem[]`
- Sort: approvals → due date → created date
- Render task list widget

### 7.2 `taskserver.prepare_approval_review`
- Fetch provider approval detail
- Create review package
- Issue nonce with TTL
- Render approval widget

### 7.3 `taskserver.execute_approval_decision`
- Requires valid nonce
- Routes approve/reject to provider
- Logs outcome
- Returns updated state

---

## 8. Widgets

### 8.1 Task list widget
- Tabs: **Approvals | Tasks**
- Reads `window.openai.toolOutput.items`
- “Review” → `taskserver.prepare_approval_review`

### 8.2 Approval widget
- Reads `window.openai.toolOutput.review`
- Buttons:
  - Approve
  - Reject
  - “Ask Copilot to summarise”

---

## 9. Provider Requirements (All)

Each provider MCP server must implement:

- List tasks
- List approvals (if applicable)
- Get task / approval detail
- Execute write actions
- Return `structuredContent`

---

## 10. Provider Responsibilities (Summary)

### Workday
- Inbox tasks
- Inbox approvals
- Approve / reject inbox task

### ServiceNow
- “My work” tasks (task‑derived tables)
- Approvals (`sysapproval_approver`)
- Comments / work notes
- Approve / reject approvals

### Salesforce
- Tasks (Task object)
- Approvals (ProcessInstanceWorkitem)
- Approve / reject via Process Approvals

### Jira
- Assigned issues
- Comments
- Transitions
- (Optional) JSM approvals

---

## 11. Nonce & State Store

TaskServer must store:
- nonce
- approvalId
- provider
- expiry

Approve / reject without a valid nonce **must fail**.

---

## 12. Configuration

```yaml
providers:
  workday:
    mcp_url: https://m365copilot-mcp/mcp
  servicenow:
    mcp_url: https://snow-mcp/mcp
  salesforce:
    mcp_url: https://sf-mcp/mcp
  jira:
    mcp_url: https://jira-mcp/mcp

policy:
  approval_review_ttl_seconds: 900
```

---

## End of Canonical Spec
