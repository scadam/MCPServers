#!/usr/bin/env python3
"""
Demo script showing how to interact with the MCP server locally
This simulates what an MCP client would do
"""

import asyncio
import json
from mcp_servers.workday.server import build_workday_server

async def demo_tool_calls():
    """Demonstrate how tools are called and what the authentication looks like."""
    
    print("=== MCP Server Tool Call Demo ===\n")
    
    # Build the server
    server = build_workday_server()
    
    # Get list of available tools
    tools = await server.list_tools()
    print(f"Available tools ({len(tools)}):")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description or 'No description'}")
    
    print("\n=== Tool Call Structure ===")
    
    # Example 1: get_worker tool call
    print("\n1. Example: get_worker tool call")
    print("   URL: Not applicable (MCP uses stdio/websocket transport)")
    print("   Method: MCP 'tools/call' request")
    print("   Payload structure:")
    
    get_worker_payload = {
        "method": "tools/call",
        "params": {
            "name": "get_worker",
            "arguments": {
                "auth_token": "your_bearer_token_here"  # This is the access token
            }
        }
    }
    
    print(json.dumps(get_worker_payload, indent=2))
    
    print("\n   ⚠️  Note: auth_token should be just the token value, NOT prefixed with 'Bearer'")
    print("   ⚠️  The server automatically adds 'Bearer' prefix when making HTTP calls to Workday")
    
    # Example 2: get_leave_balances tool call  
    print("\n2. Example: get_leave_balances tool call")
    print("   Payload structure:")
    
    get_leave_balances_payload = {
        "method": "tools/call", 
        "params": {
            "name": "get_leave_balances",
            "arguments": {
                "auth_token": "your_bearer_token_here"
            }
        }
    }
    
    print(json.dumps(get_leave_balances_payload, indent=2))
    
    # Example 3: book_leave tool call with parameters
    print("\n3. Example: book_leave tool call (with additional parameters)")
    print("   Payload structure:")
    
    book_leave_payload = {
        "method": "tools/call",
        "params": {
            "name": "book_leave", 
            "arguments": {
                "auth_token": "your_bearer_token_here",
                "absence_type_id": "some_absence_type_id",
                "start_date": "2024-12-01",
                "end_date": "2024-12-05",
                "comment": "Personal time off"
            }
        }
    }
    
    print(json.dumps(book_leave_payload, indent=2))
    
    print("\n=== Authentication Details ===")
    print("• Access Token: Pass your OAuth access token in the 'auth_token' argument")
    print("• Bearer Prefix: Do NOT include 'Bearer' prefix - the server adds it automatically")
    print("• Token Type: Should be a valid Workday API access token")
    print("• HTTP Headers: Server automatically sets 'Authorization: Bearer <token>' for Workday API calls")
    
    print("\n=== Server Transport Options ===")
    print("1. stdio (default): For MCP clients")
    print("   Command: python -m mcp_servers.cli workday")
    print("   Usage: Standard MCP protocol over stdin/stdout")
    
    print("\n2. websocket: For testing (if supported)")
    print("   Command: python -m mcp_servers.cli workday --transport websocket --port 8080")
    print("   Usage: Connect via WebSocket to ws://localhost:8080")
    
    print("\n=== How Internal HTTP Calls Work ===")
    print("When you call a tool, the server makes HTTP requests like this:")
    print("  GET https://wd2-impl-services1.workday.com/ccx/api/absenceManagement/v1/microsoft_dpt6/workers/worker_id/...")
    print("  Headers:")
    print("    Authorization: Bearer <your_token>")
    print("    Content-Type: application/json")
    
    print("\n=== Next Steps ===")
    print("1. Configure your .env.workday file with proper credentials")
    print("2. Start the server: python -m mcp_servers.cli workday")
    print("3. Connect your MCP client to the server")
    print("4. Make tool calls with your access token in the arguments")

if __name__ == "__main__":
    asyncio.run(demo_tool_calls())