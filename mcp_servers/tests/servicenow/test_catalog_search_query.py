"""Regression tests for ServiceNow catalog search query generation."""

from types import SimpleNamespace

import pytest

from mcp_servers.servicenow import tools


class _DummyResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"result": []}


class _DummyClient:
    def __init__(self, sink: dict):
        self._sink = sink

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, params=None, headers=None):
        self._sink["url"] = url
        self._sink["params"] = params or {}
        self._sink["headers"] = headers or {}
        return _DummyResponse()


@pytest.mark.asyncio
async def test_list_catalog_items_builds_encoded_or_query(monkeypatch) -> None:
    captured: dict = {}

    async def _fake_token() -> str:
        return "token"

    monkeypatch.setattr(
        tools,
        "load_servicenow_settings",
        lambda: SimpleNamespace(instance_url="https://example.service-now.com"),
    )
    monkeypatch.setattr(tools, "_get_servicenow_token", _fake_token)
    monkeypatch.setattr(tools, "create_async_client", lambda *args, **kwargs: _DummyClient(captured))

    await tools.tool_list_catalog_items(search="laptop", limit=10)

    assert captured["params"]["sysparm_query"] == (
        "nameLIKElaptop^ORshort_descriptionLIKElaptop^active=true"
    )
