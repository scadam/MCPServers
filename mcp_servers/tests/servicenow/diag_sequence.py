"""Reproduce the exact smoke-test sequence with the working iter_text approach.

If this hangs at create_incident, the issue is server-side.
If this works, the issue is in the test client/transport only.
"""
import subprocess, sys, time, httpx, json, os, threading

PORT = 8094
BASE = f"http://localhost:{PORT}/servicenow/mcp"

env = {
    **os.environ,
    "SERVICENOW_INSTANCE_URL": "https://dev352314.service-now.com",
    "SERVICENOW_CLIENT_ID": "9b8958a5c4a14c36924c9b1c7ae8240c",
    "SERVICENOW_CLIENT_SECRET": "NV?}Pjyxv8IA[oy@ZF(FKeNTa]Xz:1SK",
}

proc = subprocess.Popen(
    [sys.executable, "-m", "mcp_servers.cli", "servicenow",
     "--transport", "http", "--port", str(PORT)],
    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)

lines: list[str] = []
def drain():
    for line in proc.stdout:
        lines.append(line.decode("utf-8", errors="replace").rstrip())
threading.Thread(target=drain, daemon=True).start()

deadline = time.time() + 15
ready = False
while time.time() < deadline:
    try:
        httpx.get(BASE, timeout=2)
        ready = True
        break
    except Exception:
        time.sleep(0.5)

if not ready:
    print("Server failed to start")
    proc.kill()
    sys.exit(1)

print("Server ready\n")
H = {"Content-Type": "application/json", "Accept": "application/json"}


def call(label: str, body: dict, sid: str | None = None) -> dict:
    """POST to MCP, stream-read the response, return parsed JSON."""
    h = dict(H)
    if sid:
        h["mcp-session-id"] = sid
    t0 = time.time()
    with httpx.Client(timeout=120) as c:
        with c.stream("POST", BASE, json=body, headers=h) as resp:
            raw = b"".join(resp.iter_bytes())
    elapsed = time.time() - t0
    ct = resp.headers.get("content-type", "?")
    print(f"  [{label}] {resp.status_code} {ct}  ({elapsed:.1f}s, {len(raw)} bytes)")
    if raw:
        return json.loads(raw)
    return {}


try:
    # 1. Initialize
    data = call("init", {
        "jsonrpc": "2.0", "id": "i1", "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                   "clientInfo": {"name": "diag", "version": "1.0"}}
    })
    sid = None  # stateless_http=True → no session

    # 2. Initialized
    call("notif", {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)

    # 3. tools/list
    data = call("tools/list", {"jsonrpc": "2.0", "id": "t1", "method": "tools/list", "params": {}}, sid)
    tools = data.get("result", {}).get("tools", [])
    print(f"  Tools: {[t['name'] for t in tools]}")

    # 4. list_incidents — no filter
    data = call("list (no filter)", {"jsonrpc": "2.0", "id": "c1", "method": "tools/call",
        "params": {"name": "list_incidents", "arguments": {"limit": 2}}}, sid)
    content = data.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            d = json.loads(c["text"])
            print(f"  returned: {d['total_returned']}")

    # 5. list_incidents — search
    data = call("list (search)", {"jsonrpc": "2.0", "id": "c2", "method": "tools/call",
        "params": {"name": "list_incidents", "arguments": {"search_text": "email", "limit": 3}}}, sid)
    content = data.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            d = json.loads(c["text"])
            print(f"  returned: {d['total_returned']}")

    # 6. create_incident — THE CALL THAT HANGS IN SMOKE TEST
    print("\n>>> create_incident (after list_incidents calls)...")
    data = call("create", {"jsonrpc": "2.0", "id": "c3", "method": "tools/call",
        "params": {"name": "create_incident",
                   "arguments": {"short_description": "Seq diag test", "urgency": "3"}}}, sid)
    content = data.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            d = json.loads(c["text"])
            print(f"  created: {d.get('number')}")

    # 7. get_incident
    num = None
    for c in content:
        if c.get("type") == "text":
            num = json.loads(c["text"]).get("number")
    if num:
        print(f"\n>>> get_incident ({num})...")
        data = call("get", {"jsonrpc": "2.0", "id": "c4", "method": "tools/call",
            "params": {"name": "get_incident", "arguments": {"number": num}}}, sid)
        content = data.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                d = json.loads(c["text"])
                print(f"  state: {d.get('incident',{}).get('state')}  journal: {d.get('journal_count')}")

    # 8. update_incident
    if num:
        print(f"\n>>> update_incident ({num})...")
        data = call("update", {"jsonrpc": "2.0", "id": "c5", "method": "tools/call",
            "params": {"name": "update_incident",
                       "arguments": {"number": num, "comments": "Diag test comment", "urgency": "2"}}}, sid)
        content = data.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                d = json.loads(c["text"])
                print(f"  updated: {d.get('updated')}  fields: {d.get('fields_changed')}")
                print(f"  journal: {d.get('journal_count')}")

    print("\n✅ All steps passed")

finally:
    print("\n--- Server logs (last 30) ---")
    for l in lines[-30:]:
        print(f"  {l}")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
