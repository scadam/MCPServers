"""Quick smoke test for the ServiceNow MCP server.

Starts the server as a subprocess, runs MCP calls, then tears down.
"""
import httpx, json, os, signal, subprocess, sys, threading, time

PORT = 8091
BASE = f"http://localhost:{PORT}/servicenow/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def _post(body: dict, session_id: str | None = None) -> httpx.Response:
    """Send a JSON-RPC request and return the response.

    Uses a *fresh* httpx.Client with streaming iteration (``iter_bytes``)
    for every call.  The MCP StreamableHTTP transport uses chunked
    transfer-encoding and HTTP/1.1 keep-alive; ``httpx.post()`` (eager
    mode) and ``resp.read()`` both hang waiting for the connection to
    close, whereas ``iter_bytes()`` correctly detects the chunked
    terminator and returns.
    """
    h = dict(HEADERS)
    if session_id:
        h["mcp-session-id"] = session_id
    with httpx.Client(timeout=120) as client:
        with client.stream("POST", BASE, json=body, headers=h) as resp:
            # Consume via iterator — this reliably detects end-of-body
            # even when the server keeps the connection open.
            raw = b"".join(resp.iter_bytes())
    # Attach consumed content so .json() / .text keep working.
    resp._content = raw
    return resp


def wait_for_server(timeout: int = 15) -> bool:
    """Poll until the server is ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"http://localhost:{PORT}/servicenow/mcp", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    env = {
        **os.environ,
        "SERVICENOW_INSTANCE_URL": "https://dev352314.service-now.com",
        "SERVICENOW_CLIENT_ID": "9b8958a5c4a14c36924c9b1c7ae8240c",
        "SERVICENOW_CLIENT_SECRET": "NV?}Pjyxv8IA[oy@ZF(FKeNTa]Xz:1SK",
    }

    print(f"Starting MCP server on port {PORT} ...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_servers.cli", "servicenow",
         "--transport", "http", "--port", str(PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    # Drain subprocess stdout in background to prevent pipe-buffer deadlock.
    # On Windows the pipe buffer is small (~4-8 KB); if it fills up the server
    # blocks on its next log write and never sends the HTTP response.
    server_logs: list[str] = []
    def _drain() -> None:
        assert proc.stdout
        for raw_line in proc.stdout:
            server_logs.append(raw_line.decode("utf-8", errors="replace").rstrip())
    threading.Thread(target=_drain, daemon=True).start()

    try:
        if not wait_for_server():
            print(f"Server failed to start.\n" + "\n".join(server_logs[-20:]))
            sys.exit(1)
        print("Server ready.\n")

        # 1. Initialize
        print(">>> MCP initialize")
        r = _post({
            "jsonrpc": "2.0", "id": "init-1", "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                       "clientInfo": {"name": "smoketest", "version": "1.0"}}
        })
        sid = r.headers.get("mcp-session-id")
        print(f"  status={r.status_code}  session={sid}")
        init_data = r.json()
        print(f"  server: {json.dumps(init_data.get('result',{}).get('serverInfo',{}))}")

        # 2. Initialized notification
        _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id=sid)
        print("  initialized notification sent")

        # 3. List tools
        print("\n>>> tools/list")
        r = _post({"jsonrpc": "2.0", "id": "tools-1", "method": "tools/list", "params": {}},
                   session_id=sid)
        tools = r.json().get("result", {}).get("tools", [])
        for t in tools:
            print(f"  - {t['name']}: {t.get('description','')[:80]}")

        # 4. Call list_incidents (no filters)
        print("\n>>> tools/call  list_incidents (no filters, limit=2)")
        r = _post({"jsonrpc": "2.0", "id": "call-1", "method": "tools/call",
                   "params": {"name": "list_incidents", "arguments": {"limit": 2}}},
                  session_id=sid)
        result = r.json()
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            sys.exit(1)
        content = result.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                data = json.loads(c["text"])
                print(f"  total_returned: {data['total_returned']}")
                for inc in data["incidents"]:
                    desc = (inc.get('short_description') or '')[:60]
                    print(f"    {inc.get('number','?')}  {inc.get('state','?')}  {desc}")

        # 5. Search by text
        print("\n>>> tools/call  list_incidents (search_text='email', limit=3)")
        r = _post({"jsonrpc": "2.0", "id": "call-2", "method": "tools/call",
                   "params": {"name": "list_incidents",
                              "arguments": {"search_text": "email", "limit": 3}}},
                  session_id=sid)
        result = r.json()
        content = result.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                data = json.loads(c["text"])
                print(f"  total_returned: {data['total_returned']}")
                for inc in data["incidents"]:
                    desc = (inc.get('short_description') or '')[:60]
                    print(f"    {inc.get('number','?')}  {inc.get('state','?')}  {desc}")

        # 6. Create incident
        print("\n>>> tools/call  create_incident")
        t0 = time.time()
        r = _post({"jsonrpc": "2.0", "id": "call-3", "method": "tools/call",
                   "params": {"name": "create_incident",
                              "arguments": {
                                  "short_description": "Smoke-test incident — safe to delete",
                                  "caller": "System Administrator",
                                  "description": "Created by automated smoke test.",
                                  "category": "inquiry",
                                  "urgency": "3",
                              }}},
                  session_id=sid)
        print(f"  responded in {time.time() - t0:.1f}s")
        result = r.json()
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            sys.exit(1)
        content = result.get("result", {}).get("content", [])
        created_number = None
        for c in content:
            if c.get("type") == "text":
                data = json.loads(c["text"])
                created_number = data.get("number")
                print(f"  created: {data.get('created')}")
                print(f"  number:  {created_number}")
                print(f"  link:    {data.get('link','')[:80]}")

        # 7. Get incident (with journal)
        assert created_number, "create_incident did not return a number"
        print(f"\n>>> tools/call  get_incident ({created_number})")
        r = _post({"jsonrpc": "2.0", "id": "call-4", "method": "tools/call",
                   "params": {"name": "get_incident",
                              "arguments": {"number": created_number}}},
                  session_id=sid)
        result = r.json()
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            sys.exit(1)
        content = result.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                data = json.loads(c["text"])
                inc = data.get("incident", {})
                print(f"  number:        {inc.get('number')}")
                print(f"  state:         {inc.get('state')}")
                print(f"  journal_count: {data.get('journal_count')}")

        # 8. Update incident — add a comment
        print(f"\n>>> tools/call  update_incident ({created_number}, add comment)")
        r = _post({"jsonrpc": "2.0", "id": "call-5", "method": "tools/call",
                   "params": {"name": "update_incident",
                              "arguments": {
                                  "number": created_number,
                                  "comments": "Automated smoke-test comment.",
                                  "urgency": "2",
                              }}},
                  session_id=sid)
        result = r.json()
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            sys.exit(1)
        content = result.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                data = json.loads(c["text"])
                print(f"  updated:        {data.get('updated')}")
                print(f"  fields_changed: {data.get('fields_changed')}")
                inc = data.get("incident", {})
                print(f"  urgency:        {inc.get('urgency')}")
                print(f"  journal_count:  {data.get('journal_count')}")
                for entry in data.get("journal", []):
                    print(f"    [{entry['type']}] {entry['created_by']} @ "
                          f"{entry['created_on']}: {entry['text'][:60]}")

        print("\n✅ All tests passed")

    finally:
        print("\nStopping server ...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
