#!/usr/bin/env python3
"""
Test MCP HTTP server with proper SSE protocol.
MCP uses Server-Sent Events for HTTP transport.
"""

import requests
import json
import uuid
import time

def test_mcp_http_server():
    """Test MCP server using proper HTTP/SSE protocol."""
    
    base_url = "http://127.0.0.1:8080"
    
    # Step 1: Start a session
    session_id = str(uuid.uuid4())
    
    print("🔧 Testing MCP HTTP Server")
    print(f"   URL: {base_url}")
    print(f"   Session ID: {session_id}")
    print()
    
    # Step 2: Try to initialize
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache'
    }
    
    # Test if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server responding: {response.status_code}")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return
    
    # Try SSE endpoint
    try:
        print("📋 Testing SSE endpoint...")
        sse_url = f"{base_url}/sse"
        
        response = requests.get(sse_url, headers=headers, stream=True, timeout=10)
        print(f"SSE Response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SSE endpoint available")
            # Read a few lines
            for i, line in enumerate(response.iter_lines(decode_unicode=True)):
                if i > 5:  # Just read first few lines
                    break
                if line:
                    print(f"   {line}")
        else:
            print(f"❌ SSE endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ SSE endpoint error: {e}")
    
    # Try some common MCP endpoints
    endpoints_to_test = [
        "/",
        "/sse", 
        "/session",
        "/tools",
        "/resources",
        "/prompts"
    ]
    
    print("\n📋 Testing common endpoints:")
    for endpoint in endpoints_to_test:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5)
            print(f"   {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   {endpoint}: ERROR - {e}")

if __name__ == "__main__":
    test_mcp_http_server()