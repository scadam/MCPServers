#!/usr/bin/env python3
"""
Correct MCP Server Authentication Flow Demo
This shows the proper Entra ID SSO authentication pattern.
"""

import asyncio
import json

async def demo_correct_auth_flow():
    """Demonstrate the correct Entra ID authentication flow for MCP servers."""
    
    print("🔐 **CORRECT MCP Server Authentication Flow with Entra ID SSO**\n")
    
    print("=== Step 1: Client Authentication ===")
    print("1. Client app authenticates with Entra ID")
    print("2. Client receives access token for 'MCP Server API' scope")
    print("3. Client includes token in MCP tool calls\n")
    
    print("=== Step 2: MCP Server Token Validation ===")
    print("1. MCP Server receives tool call with auth_token")
    print("2. Server validates Entra ID JWT token")
    print("3. Server extracts user identity from validated token")
    print("4. Server uses its own stored Workday credentials for API calls\n")
    
    print("=== Entra ID App Registration Setup ===")
    print("You need TWO app registrations:")
    print("\n📱 **Client App Registration:**")
    print("  - Application Type: Public client (mobile & desktop)")
    print("  - Redirect URI: http://localhost:8080/callback")
    print("  - API Permissions: 'MCP Server API' scope")
    print("  - Used by: Client applications (Claude Desktop, etc.)")
    
    print("\n🖥️  **MCP Server API Registration:**") 
    print("  - Application Type: Web application")
    print("  - Expose API: Define custom scope (e.g., 'workday.read')")
    print("  - Used by: MCP Server for token validation")
    
    print("\n=== Environment Configuration ===")
    print("Configure .env.workday with:")
    print()
    
    # Print environment configuration
    config_lines = [
        "# Entra ID - MCP Server API Registration",
        "AAD_APP_CLIENT_ID=your-mcp-server-api-client-id",
        "AAD_APP_TENANT_ID=your-tenant-id", 
        "OPENAPI_SERVER_DOMAIN=your-server-domain.com",
        "",
        "# Workday API - Server's own credentials",
        "WORKDAY_TOKEN_URL=https://wd2-impl-services1.workday.com/ccx/oauth2/token",
        "WORKDAY_WORKERS_API_URL=https://wd2-impl-services1.workday.com/ccx/api/",
        "WORKDAY_CLIENT_CREDENTIALS=your-workday-client-id",
        "WORKDAY_CLIENT_SECRET=your-workday-client-secret", 
        "WORKDAY_REFRESH_TOKEN=your-workday-refresh-token",
        "",
        "# Microsoft Graph - Fallback for user lookup",
        "GRAPH_CLIENT_ID=your-graph-client-id",
        "GRAPH_CLIENT_SECRET=your-graph-client-secret",
        "GRAPH_TENANT_ID=your-tenant-id"
    ]
    
    for line in config_lines:
        print(line)
    
    print("\n=== Correct Tool Call Flow ===")
    
    print("\n1. **Client gets Entra ID token:**")
    client_auth = {
        "client_id": "client-app-registration-id",
        "scope": "api://mcp-server-api-id/workday.read",
        "redirect_uri": "http://localhost:8080/callback"
    }
    print("   POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token")
    print("   " + json.dumps(client_auth, indent=6)[6:-1])
    
    print("\n2. **Client calls MCP tool:**")
    mcp_call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_worker",
            "arguments": {
                "auth_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6Ik..."  # Entra ID JWT
            }
        }
    }
    print("   " + json.dumps(mcp_call, indent=6)[6:-1])
    
    print("\n3. **MCP Server processes request:**")
    print("   a. Validates Entra ID JWT token")
    print("   b. Extracts user identity (UPN, Object ID)")
    print("   c. Uses server's Workday credentials to call API")
    print("   d. Returns data to client")
    
    print("\n=== HTTP Headers (for HTTP-based MCP) ===")
    print("If using HTTP transport instead of stdio:")
    print("   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6Ik...")
    print("   Content-Type: application/json")
    
    print("\n=== Security Benefits ===")
    print("✅ Client authenticates with Entra ID (SSO)")
    print("✅ MCP Server validates JWT tokens")  
    print("✅ Server uses its own Workday credentials (not exposed to client)")
    print("✅ Workday API calls use server's stored refresh token")
    print("✅ Centralized access control via Entra ID")
    
    print("\n=== Starting the Server ===")
    print("Standard MCP stdio transport:")
    print("  python -m mcp_servers.cli workday")
    print("\nThe server validates Entra ID tokens in tool calls automatically.")

if __name__ == "__main__":
    asyncio.run(demo_correct_auth_flow())