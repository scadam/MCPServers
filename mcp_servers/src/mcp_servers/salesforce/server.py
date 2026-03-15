"""Factory for the Salesforce MCP server."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.resources.types import FileResource

from ..logging import configure_logging, get_logger
from ..settings import load_shared_auth_settings
from .tools import SALESFORCE_TOOL_SPECS

LOGGER = get_logger(__name__)

# Widget HTML files live alongside the package at ui/widget/
_WIDGET_DIR = Path(__file__).resolve().parent.parent / "ui" / "widget"


def build_salesforce_server() -> FastMCP:
    configure_logging()
    server = FastMCP(
        "salesforce",
    )

    try:
        _server_domain = load_shared_auth_settings().openapi_server_domain or ""
    except Exception:
        _server_domain = ""

    # ── Register tools ───────────────────────────────────────────────
    for spec in SALESFORCE_TOOL_SPECS:
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

    # ── Register widget resources ────────────────────────────────────
    server.add_resource(
        FileResource(
            uri="ui://widget/compliance-case.html",
            path=_WIDGET_DIR / "compliance-case.html",
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
            uri="ui://widget/update-task.html",
            path=_WIDGET_DIR / "update-task.html",
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
            uri="ui://widget/crm-account-360.html",
            path=_WIDGET_DIR / "crm-account-360.html",
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
            uri="ui://widget/crm-pipeline.html",
            path=_WIDGET_DIR / "crm-pipeline.html",
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
            uri="ui://widget/crm-opportunity.html",
            path=_WIDGET_DIR / "crm-opportunity.html",
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
            uri="ui://widget/crm-event.html",
            path=_WIDGET_DIR / "crm-event.html",
            mime_type="text/html+skybridge",
            meta={
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                }
            },
        )
    )

    LOGGER.info(
        "salesforce_server_built",
        tools=len(SALESFORCE_TOOL_SPECS),
        resources=6,
    )
    return server
