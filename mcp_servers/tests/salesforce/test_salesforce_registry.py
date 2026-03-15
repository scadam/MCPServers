"""Smoke tests for Salesforce tool registry."""

from mcp_servers.salesforce.tools import SALESFORCE_TOOL_SPECS


def test_salesforce_registry_contains_crm_tools() -> None:
    expected = {
        "list_accounts",
        "list_contacts",
        "list_opportunities",
        "get_account_360",
        "get_pipeline_dashboard",
        "show_create_opportunity_form",
        "create_opportunity",
        "create_opportunity_task",
        "show_create_event_form",
        "create_event",
    }
    registered = {spec["name"] for spec in SALESFORCE_TOOL_SPECS}
    assert expected.issubset(registered)
