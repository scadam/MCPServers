"""Diagnostic test: stream the MCP response to see what's happening."""
import subprocess, sys, time, httpx, json, os, threading

PORT = 8093
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

# Wait for server
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

print("Server ready")
H = {"Content-Type": "application/json", "Accept": "application/json"}

# Initialize
r = httpx.post(BASE, json={
    "jsonrpc": "2.0", "id": "i1", "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
               "clientInfo": {"name": "diag", "version": "1.0"}}
}, headers=H, timeout=30)
sid = r.headers.get("mcp-session-id")
print(f"init: status={r.status_code}  session={sid}")

sh = dict(H)
if sid:
    sh["mcp-session-id"] = sid
httpx.post(BASE, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
           headers=sh, timeout=10)

# Stream create_incident response
print("\n>>> create_incident (streaming)...")
t0 = time.time()
with httpx.Client(timeout=120) as client:
    with client.stream("POST", BASE, json={
        "jsonrpc": "2.0", "id": "c1", "method": "tools/call",
        "params": {"name": "create_incident",
                   "arguments": {"short_description": "Stream diag test", "urgency": "3"}}
    }, headers=sh) as resp:
        ct = resp.headers.get("content-type", "?")
        print(f"  status={resp.status_code}  content-type={ct}")
        chunks = []
        for chunk in resp.iter_text():
            elapsed = time.time() - t0
            chunks.append(chunk)
            preview = chunk[:150].replace("\n", "\\n")
            print(f"  [{elapsed:.1f}s] chunk #{len(chunks)} ({len(chunk)} chars): {preview}")
            if elapsed > 90:
                print("  Giving up after 90s")
                break
        print(f"\nTotal: {len(chunks)} chunks in {time.time()-t0:.1f}s")

# Show server logs
time.sleep(1)
print("\n--- Server logs (last 25) ---")
for l in lines[-25:]:
    print(f"  {l}")

proc.terminate()
try:
    proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()
