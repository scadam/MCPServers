"""Factory for the ServiceNow MCP server."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.resources.types import FileResource

from ..logging import configure_logging, get_logger
from ..settings import load_shared_auth_settings
from .tools import SERVICENOW_TOOL_SPECS

LOGGER = get_logger(__name__)

# Widget HTML files live alongside the package at ui/widget/
_WIDGET_DIR = Path(__file__).resolve().parent.parent / "ui" / "widget"


def build_servicenow_server() -> FastMCP:
    configure_logging()
    server = FastMCP(
        "servicenow",
    )

    # Resolve the public server domain for side-panel widget support
    try:
        _server_domain = load_shared_auth_settings().openapi_server_domain or ""
    except Exception:
        _server_domain = ""

    # ── Register tools ───────────────────────────────────────────────
    for spec in SERVICENOW_TOOL_SPECS:
        tool_name = spec["name"]
        tool_func = spec["func"]
        # Inject widgetDomain into any tool that has an outputTemplate.
        # widgetMetadata is the nested key the Copilot widget-renderer reads
        # when transitioning to side-panel / maximised mode.
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

    # ── Register widget resources (matches working project pattern) ──
    server.add_resource(
        FileResource(
            uri="ui://widget/incident-list.html",
            path=_WIDGET_DIR / "incident-list.html",
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
            uri="ui://widget/create-incident.html",
            path=_WIDGET_DIR / "create-incident.html",
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
            uri="ui://widget/catalog-item.html",
            path=_WIDGET_DIR / "catalog-item.html",
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
            uri="ui://widget/catalog-list.html",
            path=_WIDGET_DIR / "catalog-list.html",
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
            uri="ui://widget/cart-summary.html",
            path=_WIDGET_DIR / "cart-summary.html",
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
            uri="ui://widget/update-incident.html",
            path=_WIDGET_DIR / "update-incident.html",
            mime_type="text/html+skybridge",
            meta={
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                }
            },
        )
    )

    LOGGER.info("resources_registered", count=6)
    return server
