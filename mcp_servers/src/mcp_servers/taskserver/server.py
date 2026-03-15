"""Factory for the TaskServer MCP server.

TaskServer is the unified orchestrator for tasks & approvals across
Workday, ServiceNow, Salesforce, and Jira.  See taskserver-spec.md §5.
"""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.resources.types import FileResource

from ..logging import configure_logging, get_logger
from ..settings import load_shared_auth_settings
from .tools import TASKSERVER_TOOL_SPECS

LOGGER = get_logger(__name__)

# Widget HTML files live alongside the package at ui/widget/
_WIDGET_DIR = Path(__file__).resolve().parent.parent / "ui" / "widget"


def build_taskserver_server() -> FastMCP:
    configure_logging()
    server = FastMCP("taskserver")

    try:
        _server_domain = load_shared_auth_settings().openapi_server_domain or ""
    except Exception:
        _server_domain = ""

    # ── Register tools ───────────────────────────────────────────────
    for spec in TASKSERVER_TOOL_SPECS:
        tool_name = spec["name"]
        tool_func = spec["func"]
        tool_meta = dict(spec.get("meta") or {})
        if "openai/outputTemplate" in tool_meta and _server_domain:
            tool_meta.setdefault("openai/widgetDomain", _server_domain)
            tool_meta["widgetMetadata"] = {"openai/widgetDomain": _server_domain}
        server.tool(
            name=tool_name,
            description=spec.get("summary", ""),
            annotations=spec.get("annotations"),
            meta=tool_meta or None,
        )(tool_func)
        LOGGER.info("tool_registered", tool=tool_name)

    # ── Register widget resources (spec §8) ──────────────────────────
    server.add_resource(
        FileResource(
            uri="ui://widget/task-list.html",
            path=_WIDGET_DIR / "task-list.html",
            mime_type="text/html+skybridge",
            meta={
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                }
            },
        )
    )

    server.add_resource(
        FileResource(
            uri="ui://widget/approval-review.html",
            path=_WIDGET_DIR / "approval-review.html",
            mime_type="text/html+skybridge",
            meta={
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                }
            },
        )
    )

    LOGGER.info("taskserver_built", tools=len(TASKSERVER_TOOL_SPECS), resources=2)
    return server
