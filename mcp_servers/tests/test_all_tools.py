"""Smoke-test every MCP server's tools against the running server.

Usage:
    1. Start: python -m mcp_servers.cli all --transport both --port 8080
    2. Run:   python tests/test_all_tools.py
"""

import asyncio
import json
import sys
import traceback

import httpx

BASE = "http://127.0.0.1:8080"

# Each entry: (server_name, tool_name, arguments_dict)
TOOL_TESTS = [
    # ── Salesforce ───────────────────────────────────────────────────
    ("salesforce", "list_tasks", {}),
    ("salesforce", "list_approvals", {}),
    # ── Jira ─────────────────────────────────────────────────────────
    ("jira", "list_issues", {}),
    # ── TaskServer ───────────────────────────────────────────────────
    ("taskserver", "list_items", {}),
    # ── Workday (will fail if no env but shows connectivity) ─────────
    ("workday", "get_worker", {}),
    # ── ServiceNow (will fail if no env but shows connectivity) ──────
    ("servicenow", "list_incidents", {}),
]


class StreamableHTTPClient:
    """Minimal MCP Streamable-HTTP client for testing."""

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.url = f"{BASE}/{server_name}/mcp"
        self._id = 0
        self._session_id: str | None = None

    async def _post(self, payload: dict, client: httpx.AsyncClient) -> dict | None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id

        r = await client.post(self.url, json=payload, headers=headers)

        # Capture session id from response
        sid = r.headers.get("mcp-session-id")
        if sid:
            self._session_id = sid

        if r.status_code == 202:
            return None

        ct = r.headers.get("content-type", "")
        if "text/event-stream" in ct:
            # Parse SSE events from the response body
            for line in r.text.splitlines():
                if line.startswith("data: "):
                    try:
                        return json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
            return None
        else:
            r.raise_for_status()
            return r.json()

    async def initialize(self, client: httpx.AsyncClient) -> None:
        self._id += 1
        result = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke-test", "version": "1.0"},
                },
            },
            client,
        )
        # Send initialized notification
        await self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            client,
        )
        await asyncio.sleep(0.2)

    async def tools_list(self) -> list[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            await self.initialize(client)
            self._id += 1
            result = await self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._id,
                    "method": "tools/list",
                    "params": {},
                },
                client,
            )
            if result and "result" in result:
                return [t["name"] for t in result["result"].get("tools", [])]
            return []

    async def call_tool(self, tool_name: str, args: dict) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            await self.initialize(client)
            self._id += 1
            result = await self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._id,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": args},
                },
                client,
            )
            if result and "result" in result:
                content = result["result"].get("content", [])
                texts = [c.get("text", str(c)) for c in content]
                return "\n".join(texts)
            if result and "error" in result:
                return f"ERROR: {result['error']}"
            return str(result)


async def main():
    print("=" * 70)
    print("MCP TOOL SMOKE TESTS")
    print("=" * 70)

    servers = ["taskserver", "workday", "servicenow", "salesforce", "jira"]
    all_ok = True

    # Phase 1: List tools on each server
    print("\n-- Phase 1: tools/list -----------------------------------------\n")
    for name in servers:
        try:
            mcp = StreamableHTTPClient(name)
            tools = await mcp.tools_list()
            print(f"  OK   {name:15s} -> {len(tools)} tools: {', '.join(tools)}")
        except Exception as exc:
            print(f"  FAIL {name:15s} -> ERROR: {exc}")
            traceback.print_exc()
            all_ok = False

    # Phase 2: Call specific tools
    print("\n-- Phase 2: tool calls -----------------------------------------\n")
    for server_name, tool_name, args in TOOL_TESTS:
        label = f"{server_name}/{tool_name}"
        try:
            mcp = StreamableHTTPClient(server_name)
            result = await mcp.call_tool(tool_name, args)
            preview = result[:300] + "..." if len(result) > 300 else result
            print(f"  OK   {label:35s}")
            for line in preview.splitlines()[:5]:
                print(f"       {line}")
        except Exception as exc:
            print(f"  FAIL {label:35s} -> {exc}")
            all_ok = False

    print("\n" + "=" * 70)
    if all_ok:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED (see errors above)")
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
