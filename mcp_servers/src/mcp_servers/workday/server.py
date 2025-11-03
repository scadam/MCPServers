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
    
    # Register tools using standard FastMCP approach
    for spec in WORKDAY_TOOL_SPECS:
        tool_name = spec["name"]
        tool_func = spec["func"]
        
        # Register tool with description - FastMCP will generate schema from function signature
        server.tool(
            name=tool_name,
            description=spec.get("summary", "")
        )(tool_func)
        
        LOGGER.info("tool_registered", tool=tool_name)
    
    return server


def run() -> None:
    server = build_workday_server()
    server.run()
