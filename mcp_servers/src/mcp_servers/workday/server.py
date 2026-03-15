"""Factory for the Workday MCP server."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.resources.types import FileResource

from ..logging import configure_logging, get_logger
from ..settings import load_shared_auth_settings
from .tools import WORKDAY_TOOL_SPECS

LOGGER = get_logger(__name__)

# Widget HTML files live alongside the package at ui/widget/
_WIDGET_DIR = Path(__file__).resolve().parent.parent / "ui" / "widget"


def build_workday_server() -> FastMCP:
    configure_logging()
    server = FastMCP(
        "workday",
    )

    try:
        _server_domain = load_shared_auth_settings().openapi_server_domain or ""
    except Exception:
        _server_domain = ""

    # ── Register tools ───────────────────────────────────────────────
    for spec in WORKDAY_TOOL_SPECS:
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

    # ── Register widget resources (matches working project pattern) ──
    server.add_resource(
        FileResource(
            uri="ui://widget/worker-profile.html",
            path=_WIDGET_DIR / "worker-profile.html",
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
            uri="ui://widget/leave-booking.html",
            path=_WIDGET_DIR / "leave-booking.html",
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
            uri="ui://widget/change-business-title.html",
            path=_WIDGET_DIR / "change-business-title.html",
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
            uri="ui://widget/learning-assignments.html",
            path=_WIDGET_DIR / "learning-assignments.html",
            mime_type="text/html+skybridge",
            meta={
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                }
            },
        )
    )

    LOGGER.info("resources_registered", count=4)
    return server


def run() -> None:
    server = build_workday_server()
    server.run()
