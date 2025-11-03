"""Factory for the Workday MCP server."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..logging import configure_logging, get_logger
from .tools import WORKDAY_TOOL_SPECS

LOGGER = get_logger(__name__)


def build_workday_server() -> FastMCP:
    configure_logging()
    server = FastMCP(
        "workday",
        json_response=True,
        stateless_http=True,
    )
    
    # Register tools
    for spec in WORKDAY_TOOL_SPECS:
        server.tool(name=spec["name"])(spec["func"])
        LOGGER.info("tool_registered", tool=spec["name"])
    
    return server


def run() -> None:
    server = build_workday_server()
    server.run()
