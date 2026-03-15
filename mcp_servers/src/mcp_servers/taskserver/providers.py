"""Provider adapters for TaskServer fan-out to backend MCP servers.

TaskServer owns orchestration, normalization, UI, approval gating, and
auditability.  Provider MCP servers own system-of-record actions.  This
module bridges those two layers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from ..logging import get_logger
from .models import UnifiedAction, UnifiedItem

LOGGER = get_logger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────


def _extract_adf_text(adf: Dict[str, Any]) -> str:
    """Extract plain text from a Jira Atlassian Document Format object."""
    parts: List[str] = []
    for node in adf.get("content", []):
        for inline in node.get("content", []):
            if inline.get("type") == "text":
                parts.append(inline.get("text", ""))
    return " ".join(parts)


# ── Normalizers ──────────────────────────────────────────────────────


def _normalize_workday_task(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Workday inbox task (non-approval) into a UnifiedItem."""
    task_id = raw.get("id", "")
    return UnifiedItem(
        id=f"workday:task:{task_id}",
        system="workday",
        kind="task",
        title=raw.get("descriptor", raw.get("subject", "")),
        summary=raw.get("overallProcess", ""),
        status=raw.get("status", ""),
        dueDate=raw.get("due"),
        createdDate=raw.get("assigned"),
        link=raw.get("link"),  # Workday inbox URL (SPA has no per-task deep link)
        assignee=raw.get("initiator"),
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
        ],
    )


def _normalize_workday_approval(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Workday inbox approval into a UnifiedItem."""
    task_id = raw.get("id", "")
    return UnifiedItem(
        id=f"workday:approval:{task_id}",
        system="workday",
        kind="approval",
        title=raw.get("descriptor", raw.get("subject", "")),
        summary=raw.get("overallProcess", ""),
        status=raw.get("status", ""),
        dueDate=raw.get("due"),
        createdDate=raw.get("assigned"),
        link=raw.get("link"),
        assignee=raw.get("initiator"),
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
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


def _normalize_servicenow_task(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a ServiceNow task into a UnifiedItem."""
    sys_id = raw.get("sys_id", "")
    return UnifiedItem(
        id=f"servicenow:task:{sys_id}",
        system="servicenow",
        kind="task",
        title=raw.get("short_description", raw.get("number", "")),
        summary=raw.get("description", ""),
        status=raw.get("state", ""),
        priority=raw.get("priority"),
        createdDate=raw.get("sys_created_on") or raw.get("opened_at"),
        link=raw.get("link"),
        assignee=raw.get("assigned_to"),
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
            UnifiedAction(
                actionId="complete",
                label="Complete",
                requiresReview=True,
                requiresWriteApproval=True,
            ),
        ],
    )


def _normalize_servicenow_approval(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a ServiceNow approval into a UnifiedItem."""
    sys_id = raw.get("sys_id", "")
    return UnifiedItem(
        id=f"servicenow:approval:{sys_id}",
        system="servicenow",
        kind="approval",
        title=raw.get("short_description", raw.get("document_id", "")),
        summary=raw.get("approver", ""),
        status=raw.get("state", ""),
        createdDate=raw.get("sys_created_on"),
        link=raw.get("link"),
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
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


def _normalize_salesforce_task(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Salesforce Task into a UnifiedItem."""
    task_id = raw.get("Id", "")
    owner = raw.get("Owner")
    assignee = owner.get("Name") if isinstance(owner, dict) else raw.get("OwnerId")
    return UnifiedItem(
        id=f"salesforce:task:{task_id}",
        system="salesforce",
        kind="task",
        title=raw.get("Subject", ""),
        summary=raw.get("Description", "") or "",
        status=raw.get("Status", ""),
        priority=raw.get("Priority"),
        dueDate=raw.get("ActivityDate"),
        createdDate=raw.get("CreatedDate"),
        link=raw.get("link"),
        assignee=assignee,
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
            UnifiedAction(
                actionId="complete",
                label="Complete",
                requiresReview=True,
                requiresWriteApproval=True,
            ),
        ],
    )


def _normalize_salesforce_approval(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Salesforce ProcessInstanceWorkitem into a UnifiedItem."""
    item_id = raw.get("Id", "")
    process = raw.get("ProcessInstance", {}) if isinstance(raw.get("ProcessInstance"), dict) else {}
    target = process.get("TargetObject", {}) if isinstance(process.get("TargetObject"), dict) else {}
    actor = raw.get("Actor")
    assignee = actor.get("Name") if isinstance(actor, dict) else raw.get("ActorId")
    return UnifiedItem(
        id=f"salesforce:approval:{item_id}",
        system="salesforce",
        kind="approval",
        title=target.get("Name", f"Approval {item_id}"),
        summary=target.get("Type", ""),
        status=process.get("Status", ""),
        createdDate=raw.get("CreatedDate"),
        link=raw.get("link"),
        assignee=assignee,
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
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


def _normalize_salesforce_case(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Salesforce Case (compliance) into a UnifiedItem."""
    case_id = raw.get("Id", "")
    case_number = raw.get("CaseNumber", "")
    return UnifiedItem(
        id=f"salesforce:case:{case_id}",
        system="salesforce",
        kind="task",
        title=raw.get("Subject", case_number),
        summary=raw.get("Description", "") or "",
        status=raw.get("Status", ""),
        priority=raw.get("Priority"),
        createdDate=raw.get("CreatedDate"),
        link=raw.get("link"),
        assignee=raw.get("OwnerId"),
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
            UnifiedAction(
                actionId="complete",
                label="Close",
                requiresReview=True,
                requiresWriteApproval=True,
            ),
        ],
    )
    return UnifiedItem(
        id=f"salesforce:approval:{item_id}",
        system="salesforce",
        kind="approval",
        title=target.get("Name", f"Approval {item_id}"),
        summary=target.get("Type", ""),
        status=process.get("Status", ""),
        createdDate=raw.get("CreatedDate"),
        assignee=assignee,
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
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


def _normalize_jira_issue(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Jira issue into a UnifiedItem."""
    fields = raw.get("fields", {})
    issue_key = raw.get("key", "")
    status = fields.get("status", {})
    priority = fields.get("priority", {})
    assignee = fields.get("assignee") or {}

    # description may be ADF (dict) or plain string
    desc = fields.get("description") or ""
    if isinstance(desc, dict):
        desc = _extract_adf_text(desc)

    link = None
    self_url = raw.get("self", "")
    if self_url and "/rest/api/" in self_url:
        base = self_url.split("/rest/api/")[0]
        link = f"{base}/browse/{issue_key}"

    return UnifiedItem(
        id=f"jira:task:{issue_key}",
        system="jira",
        kind="task",
        title=fields.get("summary", issue_key),
        summary=desc[:200],
        status=status.get("name", "") if isinstance(status, dict) else str(status),
        priority=priority.get("name") if isinstance(priority, dict) else None,
        dueDate=fields.get("duedate"),
        createdDate=fields.get("created"),
        link=link,
        assignee=assignee.get("displayName") if isinstance(assignee, dict) and assignee else None,
        actions=[
            UnifiedAction(
                actionId="review",
                label="Review",
                requiresReview=True,
                requiresWriteApproval=False,
            ),
            UnifiedAction(
                actionId="transition",
                label="Transition",
                requiresReview=True,
                requiresWriteApproval=True,
            ),
        ],
    )


# ── Fan-out helpers ──────────────────────────────────────────────────


def _normalize_workday_learning(raw: Dict[str, Any]) -> UnifiedItem:
    """Normalize a Workday learning assignment into a UnifiedItem."""
    title = raw.get("learningContentTitle") or raw.get("workdayId") or "Learning Assignment"
    return UnifiedItem(
        id=f"workday:learning:{raw.get('workdayId', '')}",
        system="workday",
        kind="learning",
        title=title,
        summary=raw.get("assignmentStatus") or "",
        status=raw.get("assignmentStatus") or "",
        dueDate=raw.get("dueDate"),
        # contentURL is the direct assignment launch URL from the report
        link=raw.get("contentURL") or raw.get("learningContentUrl"),
        overdue=raw.get("overdue", False),
        required=raw.get("required", False),
        contentProvider=raw.get("contentProvider"),
        courseDuration=raw.get("courseDuration"),
        comments=raw.get("comments"),
    )


async def _safe_call(coro, provider_name: str, operation: str) -> List:
    """Call a provider coroutine; return empty list on failure.

    Provider failures must not break TaskServer (impl notes §7).
    """
    try:
        result = await coro
        return result if isinstance(result, list) else []
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning(
            "provider_call_failed",
            provider=provider_name,
            operation=operation,
            error=str(exc),
        )
        return []


async def fan_out_list_items(ctx=None) -> List[UnifiedItem]:
    """Fan-out to all providers, normalize results, and sort.

    Sort order per spec §7.1: approvals → due date → created date.
    """
    from ..jira.tools import provider_list_tasks as jira_tasks
    from ..salesforce.tools import provider_list_approvals as sf_approvals
    from ..salesforce.tools import provider_list_cases as sf_cases
    from ..salesforce.tools import provider_list_tasks as sf_tasks
    from ..servicenow.tools import provider_list_approvals as sn_approvals
    from ..servicenow.tools import provider_list_tasks as sn_tasks
    from ..workday.tools import provider_list_approvals as wd_approvals
    from ..workday.tools import provider_list_learning as wd_learning
    from ..workday.tools import provider_list_tasks as wd_tasks

    # Fan-out to all providers concurrently
    results = await asyncio.gather(
        _safe_call(wd_tasks(ctx=ctx), "workday", "list_tasks"),
        _safe_call(wd_approvals(ctx=ctx), "workday", "list_approvals"),
        _safe_call(wd_learning(ctx=ctx), "workday", "list_learning"),
        _safe_call(sn_tasks(), "servicenow", "list_tasks"),
        _safe_call(sn_approvals(), "servicenow", "list_approvals"),
        _safe_call(sf_tasks(), "salesforce", "list_tasks"),
        _safe_call(sf_approvals(), "salesforce", "list_approvals"),
        _safe_call(sf_cases(), "salesforce", "list_cases"),
        _safe_call(jira_tasks(), "jira", "list_tasks"),
    )

    (
        wd_task_items,
        wd_approval_items,
        wd_learning_items,
        sn_task_items,
        sn_approval_items,
        sf_task_items,
        sf_approval_items,
        sf_case_items,
        jira_task_items,
    ) = results

    # Normalize all items
    items: List[UnifiedItem] = []
    for raw in wd_task_items:
        items.append(_normalize_workday_task(raw))
    for raw in wd_approval_items:
        items.append(_normalize_workday_approval(raw))
    for raw in wd_learning_items:
        items.append(_normalize_workday_learning(raw))
    for raw in sn_task_items:
        items.append(_normalize_servicenow_task(raw))
    for raw in sn_approval_items:
        items.append(_normalize_servicenow_approval(raw))
    for raw in sf_task_items:
        items.append(_normalize_salesforce_task(raw))
    for raw in sf_approval_items:
        items.append(_normalize_salesforce_approval(raw))
    for raw in sf_case_items:
        items.append(_normalize_salesforce_case(raw))
    for raw in jira_task_items:
        items.append(_normalize_jira_issue(raw))

    # Sort: approvals first → learning last → due date → created date
    def _sort_key(item: UnifiedItem):
        if item.kind == "approval":
            kind_order = 0
        elif item.kind == "learning":
            kind_order = 2
        else:
            kind_order = 1
        due = item.dueDate or "9999-12-31"
        created = item.createdDate or "9999-12-31"
        return (kind_order, due, created)

    items.sort(key=_sort_key)

    LOGGER.info("fan_out_complete", total_items=len(items))
    return items


async def get_provider_approval_detail(
    provider: str, item_id: str, ctx=None
) -> Dict[str, Any]:
    """Fetch approval detail from the specified provider."""
    if provider == "workday":
        from ..workday.tools import provider_get_approval_detail

        return await provider_get_approval_detail(item_id, ctx=ctx)
    elif provider == "servicenow":
        from ..servicenow.tools import provider_get_approval_detail

        return await provider_get_approval_detail(item_id)
    elif provider == "salesforce":
        from ..salesforce.tools import provider_get_approval_detail

        return await provider_get_approval_detail(item_id)
    elif provider == "jira":
        raise ValueError("Jira does not support standard approvals")
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def execute_provider_approval(
    provider: str, item_id: str, decision: str, comment: str = "", ctx=None
) -> Dict[str, Any]:
    """Route an approve/reject action to the appropriate provider."""
    if provider == "workday":
        from ..workday.tools import provider_execute_approval

        return await provider_execute_approval(item_id, decision, comment, ctx=ctx)
    elif provider == "servicenow":
        from ..servicenow.tools import provider_execute_approval

        return await provider_execute_approval(item_id, decision, comment)
    elif provider == "salesforce":
        from ..salesforce.tools import provider_execute_approval

        return await provider_execute_approval(item_id, decision, comment)
    elif provider == "jira":
        raise ValueError("Jira does not support standard approvals")
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def get_provider_item_detail(
    system: str, kind: str, raw_id: str, ctx=None
) -> Dict[str, Any]:
    """Get full detail (comments, transitions) for any task/case/issue."""
    if system == "salesforce" and kind in ("case", "task"):
        from ..salesforce.tools import tool_get_case

        return await tool_get_case(raw_id)
    elif system == "jira":
        from ..jira.tools import tool_get_issue

        return await tool_get_issue(raw_id)
    elif system == "servicenow":
        from ..servicenow.tools import provider_get_approval_detail

        return await provider_get_approval_detail(raw_id)
    elif system == "workday":
        from ..workday.tools import provider_get_approval_detail

        return await provider_get_approval_detail(raw_id, ctx=ctx)
    else:
        return {}


async def execute_provider_item_comment(
    system: str, kind: str, raw_id: str, comment: str, ctx=None
) -> Dict[str, Any]:
    """Add a comment to a task, case, or issue."""
    if system == "salesforce":
        from ..salesforce.tools import tool_update_case

        return await tool_update_case(raw_id, comment=comment)
    elif system == "jira":
        from ..jira.tools import tool_add_comment

        return await tool_add_comment(raw_id, comment)
    else:
        raise ValueError(f"Inline comments not supported for {system}")


async def execute_provider_item_transition(
    system: str, kind: str, raw_id: str, action: str, comment: str = "", ctx=None
) -> Dict[str, Any]:
    """Execute a status transition or status update on an item.

    For Salesforce: ``action`` is the new status string (e.g. 'Working').
    For Jira: ``action`` is the numeric transition ID from ``get_item_detail``.
    """
    if system == "salesforce":
        from ..salesforce.tools import tool_update_case

        return await tool_update_case(raw_id, status=action, comment=comment or None)
    elif system == "jira":
        from ..jira.tools import tool_transition_issue

        return await tool_transition_issue(raw_id, action, comment or None)
    else:
        raise ValueError(f"Status transitions not supported for {system}")
