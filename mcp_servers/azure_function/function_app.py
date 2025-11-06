"""Azure Functions entry point that bridges requests to the FastMCP Workday server."""

from __future__ import annotations

import azure.functions as func
from azure.functions import AsgiMiddleware

from mcp_servers.workday import build_workday_server

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Build the FastMCP ASGI app once so that each request reuses the same server instance.
_fastmcp_server = build_workday_server()
_asgi_adapter = AsgiMiddleware(_fastmcp_server.streamable_http_app())


@app.route(route="{*mcp_path}", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def handle_request(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    """Forward the HTTP trigger invocation to the FastMCP ASGI application."""
    return await _asgi_adapter.handle_async(req, context)
