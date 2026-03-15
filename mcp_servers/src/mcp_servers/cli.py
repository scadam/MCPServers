"""CLI entry point for running MCP servers.

Architecture
────────────
Each sub-server is exposed at its **own URL prefix** (``/<name>/…``) so clients
connect to a per-service endpoint.  Both SSE and Streamable-HTTP transports are
available simultaneously.

Endpoint layout  (for each ``<name>`` — ``servicenow``, ``workday``, …)
~~~~~~~~~~~~~~~
* ``GET  /<name>/sse``        – SSE event-stream
* ``POST /<name>/messages/``  – JSON-RPC messages for an SSE session
* ``POST /<name>/mcp``        – Streamable-HTTP JSON-RPC endpoint
* ``GET  /<name>/mcp``        – Streamable-HTTP server-sent notifications
* ``DELETE /<name>/mcp``      – Streamable-HTTP session termination
* ``GET  /healthz``           – Container health-check
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List

import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .jira import build_jira_server
from .logging import configure_logging, get_logger
from .salesforce import build_salesforce_server
from .servicenow import build_servicenow_server
from .taskserver import build_taskserver_server
from .workday import build_workday_server

LOGGER = get_logger(__name__)

# Registry of all available MCP servers keyed by their URL prefix.
SERVER_BUILDERS: Dict[str, callable] = {
    "taskserver": build_taskserver_server,
    "workday": build_workday_server,
    "servicenow": build_servicenow_server,
    "salesforce": build_salesforce_server,
    "jira": build_jira_server,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mount_server(
    server: FastMCP,
    name: str,
    transport: str,
) -> tuple[Mount, list]:
    """Create a Starlette ``Mount`` for *server* at ``/<name>/``.

    *transport* controls which transports are wired up:

    * ``"sse"``  – SSE only  (``/<name>/mcp`` SSE stream + ``/<name>/messages/``)
    * ``"http"`` – Streamable-HTTP only  (``/<name>/mcp``)
    * ``"both"`` – SSE at ``/<name>/sse`` **and** Streamable-HTTP at ``/<name>/mcp``

    Returns ``(mount, lifespan_apps)`` where *lifespan_apps* must have their
    ASGI lifespans managed by the parent application.
    """
    routes: list = []
    lifespan_apps: list = []

    if transport in ("sse", "both"):
        sse_path = "/sse" if transport == "both" else "/mcp"
        sse_app = server.http_app(path=sse_path, transport="sse")
        routes.extend(sse_app.routes)
        lifespan_apps.append(sse_app)

    if transport in ("http", "both"):
        http_app = server.http_app(path="/mcp", transport="streamable-http")
        routes.extend(http_app.routes)
        lifespan_apps.append(http_app)

    return Mount(f"/{name}", routes=routes), lifespan_apps


def build_app(
    server_names: List[str] | None = None,
    transport: str = "both",
    middleware: list | None = None,
) -> Starlette:
    """Build a Starlette ASGI app with per-server URL prefixes.

    Each requested server is mounted at ``/<name>/`` with SSE and/or
    Streamable-HTTP transports according to *transport*.
    """
    names = server_names or list(SERVER_BUILDERS.keys())

    all_routes: list = []
    all_lifespan_apps: list = []

    for name in names:
        builder = SERVER_BUILDERS.get(name)
        if builder is None:
            raise ValueError(f"Unknown MCP server: {name}")

        server = builder()
        mount, lifespan_apps = _mount_server(server, name, transport)
        all_routes.append(mount)
        all_lifespan_apps.extend(lifespan_apps)
        LOGGER.info(
            "server_mounted",
            server=name,
            transport=transport,
            prefix=f"/{name}",
        )

    # Health-check --------------------------------------------------------
    async def health(request):
        return JSONResponse({"status": "ok"})

    all_routes.append(Route("/healthz", health))

    # Combined lifespan that enters/exits every sub-app's lifespan --------
    @asynccontextmanager
    async def lifespan(app):
        managers = []
        for sub_app in all_lifespan_apps:
            mgr = sub_app.lifespan(sub_app)
            await mgr.__aenter__()
            managers.append(mgr)
        try:
            yield
        finally:
            for mgr in reversed(managers):
                await mgr.__aexit__(None, None, None)

    return Starlette(
        routes=all_routes,
        lifespan=lifespan,
        middleware=middleware or [],
    )


async def build_combined_server(server_names: List[str] | None = None) -> FastMCP:
    """Create a single FastMCP server that imports all requested sub-servers.

    Used for **stdio** transport where only one server instance is needed.
    """
    names = server_names or list(SERVER_BUILDERS.keys())

    root = FastMCP("m365copilot-mcp")

    for name in names:
        builder = SERVER_BUILDERS.get(name)
        if builder is None:
            raise ValueError(f"Unknown MCP server: {name}")

        server: FastMCP = builder()
        await root.import_server(server)
        LOGGER.info("mcp_server_imported", server=name)

    LOGGER.info("combined_server_ready", servers=names)
    return root


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MCP servers")
    parser.add_argument(
        "server",
        nargs="?",
        choices=[*SERVER_BUILDERS.keys(), "all"],
        default="all",
        help="Server to run (default: all)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http", "both"],
        default="stdio",
        help=(
            "Transport: stdio (single server), sse (SSE only), "
            "http (Streamable HTTP only), both (SSE + Streamable HTTP)"
        ),
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    configure_logging()

    # --- stdio: run a single server in standard I/O mode -----------------
    if args.transport == "stdio":
        if args.server == "all":
            parser.error("stdio transport requires a specific server name, not 'all'")
        builder = SERVER_BUILDERS.get(args.server)
        if builder is None:
            raise ValueError(f"Unknown server: {args.server}")
        builder().run()
        return

    # --- network: per-server paths with chosen transport(s) --------------
    server_names = None if args.server == "all" else [args.server]

    cors = Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        allow_credentials=True,
    )

    app = build_app(server_names, transport=args.transport, middleware=[cors])

    LOGGER.info(
        "starting_server",
        transport=args.transport,
        host=args.host,
        port=args.port,
    )

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
