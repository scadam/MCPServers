"""Unified data models for TaskServer MCP.

Implements the data model defined in §6 of the TaskServer spec.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UnifiedAction(BaseModel):
    """An action available on a unified item."""

    actionId: str  # review | approve | reject | complete | transition
    label: str
    requiresReview: bool = True
    requiresWriteApproval: bool = True


class UnifiedItem(BaseModel):
    """Normalized task or approval from any provider system.

    The ``id`` field uses the format ``system:type:id`` to ensure global
    uniqueness across providers.
    """

    id: str
    system: str  # workday | servicenow | salesforce | jira
    kind: str  # task | approval | learning
    title: str
    summary: str = ""
    status: str = ""
    priority: Optional[str] = None
    dueDate: Optional[str] = None
    createdDate: Optional[str] = None
    link: Optional[str] = None
    assignee: Optional[str] = None
    overdue: Optional[bool] = None
    required: Optional[bool] = None
    actions: List[UnifiedAction] = []
    # Learning-specific fields (Workday)
    contentProvider: Optional[str] = None
    courseDuration: Optional[str] = None
    comments: Optional[str] = None


class ApprovalReviewPackage(BaseModel):
    """Review package returned by ``taskserver.prepare_approval_review``."""

    item: UnifiedItem
    detail: Dict[str, Any] = {}
    nonce: str
    expiresAt: str  # ISO8601
    provider: str
    approvalId: str
