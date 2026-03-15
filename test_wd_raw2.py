"""Standalone Workday API inspection (no mcp_servers package)."""
import asyncio
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Load environment from local.settings.json or .env
env_file = Path("mcp_servers/azure_function/local.settings.json")
if env_file.exists():
    import json as _j
    with open(env_file) as f:
        cfg = _j.load(f)
    for k, v in cfg.get("Values", {}).items():
        os.environ.setdefault(k, str(v))

# Try .env files
for envf in ["mcp_servers/.env", ".env", "mcp_servers/azure_function/.env"]:
    if Path(envf).exists():
        load_dotenv(envf, override=False)
        print(f"Loaded {envf}")

TOKEN_URL = os.environ.get("WORKDAY_TOKEN_URL", "")
CLIENT_ID = os.environ.get("WORKDAY_CLIENT_CREDENTIALS", "")
CLIENT_SECRET = os.environ.get("WORKDAY_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("WORKDAY_REFRESH_TOKEN", "")
WORKERS_API_URL = os.environ.get("WORKDAY_WORKERS_API_URL", "")
ANON_EMPLOYEE_ID = os.environ.get("WORKDAY_ANONYMOUS_EMPLOYEE_ID", "")

print(f"TOKEN_URL: {TOKEN_URL[:50] if TOKEN_URL else 'NOT SET'}")
print(f"CLIENT_ID: {CLIENT_ID[:20] if CLIENT_ID else 'NOT SET'}")
print(f"ANON_EMPLOYEE_ID: {ANON_EMPLOYEE_ID or 'NOT SET'}")


async def get_token():
    async with httpx.AsyncClient() as c:
        r = await c.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def get_worker_id(token: str):
    """Get workday ID for employee."""
    url = WORKERS_API_URL
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as c:
        r = await c.get(url, headers=headers, params={"Employee_ID": ANON_EMPLOYEE_ID, "format": "json"})
        r.raise_for_status()
        data = r.json()
    # Try to get workday ID from response
    entries = data.get("Report_Entry", []) or data.get("data", []) or []
    if entries:
        entry = entries[0]
        print(f"Worker entry keys: {list(entry.keys())}")
        return entry.get("Worker_Reference_ID") or entry.get("worker_reference_id") or ANON_EMPLOYEE_ID
    return ANON_EMPLOYEE_ID


async def main():
    if not TOKEN_URL:
        print("ERROR: WORKDAY_TOKEN_URL not set")
        return

    token = await get_token()
    print(f"\nGot token: {token[:40]}...")

    wid = await get_worker_id(token)
    print(f"Using WID: {wid}")

    # === Inbox Tasks ===
    url = f"https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/workers/{wid}/inboxTasks"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as c:
        r = await c.get(url, headers=headers)
        data = r.json()

    items = data.get("data", [])
    print(f"\n=== INBOX TASKS ({len(items)}) ===")
    if items:
        print(f"All keys in first task: {list(items[0].keys())}")
        for i, item in enumerate(items[:2]):
            print(f"\n--- Task {i} ---")
            print(json.dumps(item, indent=2))

    # === Learning Assignments ===
    url2 = (
        f"https://wd2-impl-services1.workday.com/ccx/service/customreport2/"
        f"microsoft_dpt6/svasireddy/Required_Learning"
        f"?Worker_s__for_Learning_Assignment%21WID={wid}&format=json"
    )
    async with httpx.AsyncClient() as c:
        r2 = await c.get(url2, headers=headers)
        data2 = r2.json()

    entries = data2.get("Report_Entry", [])
    print(f"\n=== LEARNING ASSIGNMENTS ({len(entries)}) ===")
    if entries:
        print(f"All keys in first entry: {list(entries[0].keys())}")
        for i, e in enumerate(entries[:2]):
            print(f"\n--- Assignment {i} ---")
            print(json.dumps(e, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
