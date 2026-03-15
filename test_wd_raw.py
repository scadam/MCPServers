"""Quick script to inspect raw Workday API responses."""
import asyncio
import json
import sys
sys.path.insert(0, "mcp_servers/src")


async def main():
    from mcp_servers.workday.helpers import build_worker_context_anonymous
    from mcp_servers.settings import load_workday_oauth_settings
    from mcp_servers.http import create_async_client

    settings = load_workday_oauth_settings()
    wctx = await build_worker_context_anonymous(settings.anonymous_employee_id)
    token = wctx.workday_access_token
    wid = wctx.workday_id
    print(f"Worker ID: {wid}")

    # === Inbox Tasks ===
    url = (
        f"https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/"
        f"workers/{wid}/inboxTasks"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with create_async_client() as c:
        r = await c.get(url, headers=headers)
        data = r.json()

    items = data.get("data", [])
    print(f"\n=== INBOX TASKS ({len(items)}) ===")
    if items:
        print(f"Keys: {list(items[0].keys())}")
        for i, item in enumerate(items[:3]):
            print(f"\n--- Task {i} ---")
            print(json.dumps(item, indent=2))

    # === Learning Assignments ===
    url2 = (
        "https://wd2-impl-services1.workday.com/ccx/service/customreport2/"
        f"microsoft_dpt6/svasireddy/Required_Learning"
        f"?Worker_s__for_Learning_Assignment%21WID={wid}&format=json"
    )
    async with create_async_client() as c:
        r2 = await c.get(url2, headers=headers)
        data2 = r2.json()

    entries = data2.get("Report_Entry", [])
    print(f"\n=== LEARNING ASSIGNMENTS ({len(entries)}) ===")
    if entries:
        print(f"Keys: {list(entries[0].keys())}")
        for i, e in enumerate(entries[:3]):
            print(f"\n--- Assignment {i} ---")
            print(json.dumps(e, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
