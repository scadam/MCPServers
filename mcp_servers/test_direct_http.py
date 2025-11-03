#!/usr/bin/env python3
"""
Test direct FastMCP HTTP app creation.
"""

import sys
sys.path.insert(0, r'c:\Users\scadam\AgentsToolkitProjects\MCPServers\mcp_servers\src')

from mcp_servers.workday import build_workday_server
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response


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

def test_direct_http():
    """Test creating HTTP app directly."""
    print("🔧 Creating Workday MCP server...")
    
    try:
        server = build_workday_server()
        print("✅ Server created successfully")
        
        print("🌐 Creating HTTP app...")
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
        print("✅ HTTP app created successfully")
        print(f"App type: {type(app)}")
        
        print("🚀 Starting HTTP server...")
        print("   URL: http://127.0.0.1:8080")
        print("   Press Ctrl+C to stop")
        
        uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_http()