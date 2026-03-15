"""Comprehensive wire-format verification for live MCP server (SSE transport)."""
import asyncio
import json
import sys

from fastmcp import Client
from fastmcp.client.transports import SSETransport


# Per-server endpoints
SERVICENOW_SSE = "https://m365copilot-mcp-app.redground-c0937a09.eastus.azurecontainerapps.io/servicenow/sse"
WORKDAY_SSE = "https://m365copilot-mcp-app.redground-c0937a09.eastus.azurecontainerapps.io/workday/sse"


async def main():
    transport = SSETransport(url=SERVICENOW_SSE)
    async with Client(transport=transport) as client:

        # ══════════════════════════════════════════════════════════════
        # 1. tools/list
        # ══════════════════════════════════════════════════════════════
        tools = await client.list_tools()
        print("=" * 70)
        print(f"tools/list  →  {len(tools)} tools")
        print("=" * 70)
        for t in tools:
            meta = t.annotations if hasattr(t, "annotations") else None
            ot = None
            if meta and hasattr(meta, "outputTemplate"):
                ot = meta.outputTemplate
            print(f"  {t.name:30s}  outputTemplate={ot}")

        # ══════════════════════════════════════════════════════════════
        # 2. resources/list
        # ══════════════════════════════════════════════════════════════
        resources = await client.list_resources()
        print("\n" + "=" * 70)
        print(f"resources/list  →  {len(resources)} resources")
        print("=" * 70)
        for r in resources:
            print(f"  uri={r.uri}  mimeType={r.mimeType}")

        # ══════════════════════════════════════════════════════════════
        # 3. resources/read  (incident-list widget)
        # ══════════════════════════════════════════════════════════════
        if resources:
            uri = str(resources[0].uri)
            contents = await client.read_resource(uri)
            print(f"\nresources/read({uri})")
            for c in contents:
                text = str(c) if not hasattr(c, "text") else c.text
                print(f"  length={len(text)}  first300={text[:300]}")

        # ══════════════════════════════════════════════════════════════
        # 4. tools/call  –  list_incidents  (THE CRITICAL TEST)
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("tools/call  →  list_incidents")
        print("=" * 70)
        result = await client.call_tool("list_incidents", {})
        print(f"  result type: {type(result).__name__}")
        print(f"  result repr[:500]: {repr(result)[:500]}")

        # ══════════════════════════════════════════════════════════════
        # 5. tools/call  –  get_worker  (workday tool)
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("tools/call  →  get_worker")
        print("=" * 70)
        try:
            result2 = await client.call_tool("get_worker", {"employee_id": "test"})
            print(f"  result type: {type(result2).__name__}")
            print(f"  result repr[:500]: {repr(result2)[:500]}")
        except Exception as e:
            print(f"  Error (expected if no Workday creds): {e}")

    print("\n✅ All SSE verification checks complete.")


if __name__ == "__main__":
    asyncio.run(main())

