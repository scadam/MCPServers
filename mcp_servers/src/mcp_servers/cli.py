"""CLI entry point for running MCP servers."""

from __future__ import annotations

import argparse
import asyncio

from .logging import configure_logging, get_logger
from .workday import build_workday_server
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware

LOGGER = get_logger(__name__)


def _add_preflight_handler(app, path: str) -> None:
    async def options_endpoint(request):
        origin = request.headers.get("origin", "*")
        requested_headers = request.headers.get(
            "access-control-request-headers",
            "authorization, content-type, accept, mcp-session-id, mcp-protocol-version",
        )
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": requested_headers,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
        return Response(status_code=204, headers=headers)

    app.add_route(path, options_endpoint, methods=["OPTIONS"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MCP servers")
    parser.add_argument("server", choices=["workday"], help="Server to run")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mechanism for MCP (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for websocket transport")
    parser.add_argument("--port", type=int, default=8080, help="Port for websocket transport")
    args = parser.parse_args()

    configure_logging()
    if args.server == "workday":
        server = build_workday_server()
    else:
        raise ValueError(f"Unsupported server {args.server}")

    if args.transport == "stdio":
        server.run()
    elif args.transport == "http":
        import uvicorn
        app = server.streamable_http_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-protocol-version"],
            allow_credentials=True,
        )
        _add_preflight_handler(app, server.settings.streamable_http_path)
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        raise ValueError(f"Unsupported transport {args.transport}")


if __name__ == "__main__":  # pragma: no cover
    main()
