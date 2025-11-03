"""Smoke tests for Workday tools."""

import pytest

from mcp_servers.workday.tools import WORKDAY_TOOL_SPECS


@pytest.mark.asyncio
async def test_tool_registry_contains_expected_tools() -> None:
    expected = {
        "get_worker",
        "get_leave_balances",
        "get_direct_reports",
        "get_inbox_tasks",
        "get_learning_assignments",
        "get_pay_slips",
        "get_time_off_entries",
        "prepare_request_leave",
        "book_leave",
        "change_business_title",
        "search_learning_content",
    }
    registered = {spec["name"] for spec in WORKDAY_TOOL_SPECS}
    assert expected.issubset(registered)
