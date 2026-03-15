"""TaskServer MCP tool implementations.

Implements §7 of the TaskServer spec:
- ``list_items``              – fan-out, normalize, render task list widget
- ``prepare_approval_review`` – fetch detail, issue nonce, render approval widget
- ``execute_approval_decision`` – validate nonce, route to provider
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastmcp import Context

from ..logging import get_logger
from .models import ApprovalReviewPackage, UnifiedAction, UnifiedItem
from .nonce_store import NonceStore
from .providers import (
    execute_provider_approval,
    execute_provider_item_comment,
    execute_provider_item_transition,
    fan_out_list_items,
    get_provider_approval_detail,
    get_provider_item_detail,
)

LOGGER = get_logger(__name__)

# Module-level singleton nonce store (spec §11)
_nonce_store = NonceStore(default_ttl_seconds=900)


def _parse_unified_id(unified_id: str) -> tuple[str, str, str]:
    """Parse a unified ID ``system:type:id`` into ``(system, type, raw_id)``."""
    parts = unified_id.split(":", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Invalid unified ID format: {unified_id} (expected system:type:id)"
        )
    return parts[0], parts[1], parts[2]


# ── Tool functions ───────────────────────────────────────────────────


async def tool_list_items(
    ctx: Optional[Context] = None,
    system: Optional[str] = None,
    kind: Optional[str] = None,
) -> Dict[str, Any]:
    """List tasks and approvals across all connected systems.

    Aggregates items from Workday, ServiceNow, Salesforce, and Jira,
    normalizes them into a unified model, and renders the task list widget.
    Sorted with approvals first, then by due date and creation date.

    Args:
        system: Optional — narrow to one system: workday, servicenow, salesforce, or jira.
        kind: Optional — narrow to one kind: task or approval.
    """
    # Normalise: strip whitespace, lowercase, remove trailing 's' for plurals
    # e.g. "approvals" -> "approval", "tasks" -> "task", "ServiceNow" -> "servicenow"
    system = system.strip().lower().rstrip("s") if system else None
    kind = kind.strip().lower().rstrip("s") if kind else None

    LOGGER.info("taskserver_list_items", system=system, kind=kind)

    items = await fan_out_list_items(ctx=ctx)

    # Apply optional filters
    if system:
        items = [i for i in items if i.system == system]
    if kind:
        items = [i for i in items if i.kind == kind]

    total = len(items)
    approvals = sum(1 for i in items if i.kind == "approval")
    tasks = sum(1 for i in items if i.kind == "task")
    learning = sum(1 for i in items if i.kind == "learning")

    hint_parts = []
    if approvals:
        hint_parts.append(f"{approvals} approval{'s' if approvals != 1 else ''}")
    if tasks:
        hint_parts.append(f"{tasks} task{'s' if tasks != 1 else ''}")
    if learning:
        hint_parts.append(f"{learning} learning item{'s' if learning != 1 else ''}")
    hint_summary = ", ".join(hint_parts) if hint_parts else "no items"

    payload = {
        "_widget_hint": (
            f"SUCCESS. Task list loaded with {total} item(s): {hint_summary}. "
            "The interactive widget is now displayed to the user — do NOT describe the list "
            "in your text reply and do NOT suggest retrying. "
            "Reply with exactly one short sentence, e.g. \"Here are your tasks and approvals.\""
        ),
        "items": [item.model_dump() for item in items],
        "totalCount": total,
        "approvalCount": approvals,
        "taskCount": tasks,
        "learningCount": learning,
    }
    return payload


async def tool_prepare_approval_review(
    item_id: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Prepare a review package for an approval item.

    Fetches the approval detail from the provider, creates a nonce-gated
    review package, and renders the approval widget.  The nonce is
    single-use and time-limited (default 15 minutes).

    Args:
        item_id: The unified item ID (format: system:type:id).
    """
    provider, kind, raw_id = _parse_unified_id(item_id)
    if kind != "approval":
        raise ValueError(f"Item {item_id} is not an approval (kind={kind})")

    LOGGER.info("taskserver_prepare_review", provider=provider, raw_id=raw_id)

    # Fetch provider-specific detail
    detail = await get_provider_approval_detail(provider, raw_id, ctx=ctx)

    # Issue nonce
    nonce_entry = _nonce_store.issue(approval_id=raw_id, provider=provider)
    expires_at = datetime.fromtimestamp(
        nonce_entry.expires_at, tz=timezone.utc
    ).isoformat()

    # Build the review item
    item = UnifiedItem(
        id=item_id,
        system=provider,
        kind="approval",
        title=detail.get("title", f"Approval {raw_id}"),
        summary=detail.get("summary", ""),
        status=detail.get("status", ""),
        dueDate=detail.get("due"),
        createdDate=detail.get("assigned") or detail.get("createdDate"),
        assignee=detail.get("initiator") or detail.get("approver"),
        actions=[
            UnifiedAction(
                actionId="approve",
                label="Approve",
                requiresReview=True,
                requiresWriteApproval=True,
            ),
            UnifiedAction(
                actionId="reject",
                label="Reject",
                requiresReview=True,
                requiresWriteApproval=True,
            ),
        ],
    )

    review = ApprovalReviewPackage(
        item=item,
        detail=detail,
        nonce=nonce_entry.nonce,
        expiresAt=expires_at,
        provider=provider,
        approvalId=raw_id,
    )

    return {"review": review.model_dump()}


async def tool_execute_approval_decision(
    nonce: str,
    decision: str,
    comment: str = "",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Execute an approval decision (approve or reject).

    Requires a valid, unexpired nonce obtained from
    ``prepare_approval_review``.  Routes the decision to the appropriate
    provider and returns the outcome.  Nonces are single-use per spec §11.

    Args:
        nonce: The single-use approval nonce from the review package.
        decision: The decision: "approve" or "reject".
        comment: Optional comment for the approval/rejection.
    """
    if decision not in ("approve", "reject"):
        raise ValueError(
            f"Invalid decision: {decision}. Must be 'approve' or 'reject'."
        )

    # Validate and consume nonce — fails if invalid, expired, or reused
    entry = _nonce_store.validate_and_consume(nonce)

    LOGGER.info(
        "taskserver_execute_decision",
        provider=entry.provider,
        approval_id=entry.approval_id,
        decision=decision,
    )

    # Route to provider
    result = await execute_provider_approval(
        provider=entry.provider,
        item_id=entry.approval_id,
        decision=decision,
        comment=comment,
        ctx=ctx,
    )

    return {
        "success": True,
        "decision": decision,
        "provider": entry.provider,
        "approvalId": entry.approval_id,
        "providerResult": result,
    }


async def tool_get_item_detail(
    item_id: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Get full detail, comments, and available transitions for any task or case.

    Supported systems: salesforce (cases), jira (issues), servicenow, workday.
    Returns comments list and transitions / status options for inline widget actions.

    Args:
        item_id: Unified item ID in format system:kind:raw_id (e.g. jira:task:PROJ-123).
    """
    system, kind, raw_id = _parse_unified_id(item_id)
    LOGGER.info("taskserver_get_item_detail", system=system, kind=kind, raw_id=raw_id)
    return await get_provider_item_detail(system, kind, raw_id, ctx=ctx)


async def tool_add_item_comment(
    item_id: str,
    comment: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Add a comment to a Salesforce case or Jira issue from the task widget.

    Args:
        item_id: Unified item ID (e.g. salesforce:case:5001abc, jira:task:PROJ-1).
        comment: The comment text to post.
    """
    if not comment or not comment.strip():
        raise ValueError("Comment text is required")
    system, kind, raw_id = _parse_unified_id(item_id)
    LOGGER.info("taskserver_add_comment", system=system, kind=kind)
    return await execute_provider_item_comment(system, kind, raw_id, comment.strip(), ctx=ctx)


async def tool_execute_item_transition(
    item_id: str,
    action: str,
    comment: str = "",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Execute a status transition or status update on a task or case.

    For Salesforce cases: action is the new status string (New, Working, Escalated, Closed).
    For Jira issues: action is the numeric transition ID obtained from get_item_detail.

    Args:
        item_id: Unified item ID (e.g. salesforce:case:5001abc, jira:task:PROJ-1).
        action: New status name (Salesforce) or transition ID (Jira).
        comment: Optional comment to include with the transition.
    """
    system, kind, raw_id = _parse_unified_id(item_id)
    LOGGER.info("taskserver_execute_transition", system=system, kind=kind, action=action)
    return await execute_provider_item_transition(system, kind, raw_id, action, comment, ctx=ctx)


# ── Tool registry ───────────────────────────────────────────────────

TASKSERVER_TOOL_SPECS: list[dict] = [
    {
        "name": "list_items",
        "func": tool_list_items,
        "summary": (
            "List tasks, approvals, and learning assignments across all connected systems "
            "(Workday, ServiceNow, Salesforce, Jira). Sorted with approvals first, then "
            "by due date and creation date. "
            "Optional params: system (workday|servicenow|salesforce|jira) and "
            "kind (task|approval|learning). "
            "Results are rendered as an interactive widget. "
            "On success the response contains a _widget_hint field — follow it exactly: "
            "reply with ONE short sentence only (e.g. \"Here are your tasks and approvals.\"). "
            "Do NOT enumerate the items, describe counts, or suggest retrying."
        ),
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/task-list.html",
            "openai/toolInvocation/invoking": "Loading tasks and approvals\u2026",
            "openai/toolInvocation/invoked": "Tasks and approvals ready.",
        },
    },
    {
        "name": "prepare_approval_review",
        "func": tool_prepare_approval_review,
        "summary": (
            "Prepare a review package for an approval item. Fetches detail from "
            "the provider, issues a single-use nonce, and renders the approval "
            "review widget. Requires item_id in format system:type:id. "
            "Result is rendered as an interactive widget."
        ),
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/approval-review.html",
            "openai/toolInvocation/invoking": "Preparing approval review\u2026",
            "openai/toolInvocation/invoked": "Approval review ready.",
        },
    },
    {
        "name": "execute_approval_decision",
        "func": tool_execute_approval_decision,
        "summary": (
            "Execute an approval decision (approve or reject). Requires a valid "
            "nonce from prepare_approval_review. Routes the decision to the "
            "appropriate provider system."
        ),
        "annotations": {"readOnlyHint": False},
    },
    {
        "name": "get_item_detail",
        "func": tool_get_item_detail,
        "summary": (
            "Get full details, comments, and available status transitions for a "
            "specific task or case. Used by the task widget for inline actions. "
            "Supports Salesforce cases, Jira issues, ServiceNow, Workday."
        ),
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "add_item_comment",
        "func": tool_add_item_comment,
        "summary": (
            "Add a comment to a task or case inline from the task widget. "
            "Supports Salesforce cases (case comment) and Jira issues."
        ),
        "annotations": {"readOnlyHint": False},
    },
    {
        "name": "execute_item_transition",
        "func": tool_execute_item_transition,
        "summary": (
            "Update the status of a task or case inline from the task widget. "
            "For Salesforce: provide the new status string. "
            "For Jira: provide the numeric transition ID from get_item_detail."
        ),
        "annotations": {"readOnlyHint": False},
    },
]
