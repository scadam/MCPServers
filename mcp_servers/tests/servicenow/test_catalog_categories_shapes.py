"""Regression tests for ServiceNow catalog categories response parsing."""

from types import SimpleNamespace

import pytest

from mcp_servers.servicenow import tools


class _DummyResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


class _DummyClient:
    def __init__(self, responses: list[_DummyResponse], sink: dict):
        self._responses = responses
        self._sink = sink

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, params=None, headers=None):
        self._sink.setdefault("calls", []).append({"url": url, "params": params or {}})
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_list_catalog_categories_parses_nested_shapes(monkeypatch) -> None:
    captured: dict = {}

    async def _fake_token() -> str:
        return "token"

    responses = [
        _DummyResponse(
            {
                "result": {
                    "catalogs": [
                        {"sys_id": {"value": "catalog-123"}, "title": "Default"}
                    ]
                }
            }
        ),
        _DummyResponse(
            {
                "result": {
                    "categories": [
                        {
                            "sys_id": {"value": "cat-1"},
                            "name": "Hardware",
                            "short_description": "Devices",
                            "item_count": 7,
                        }
                    ]
                }
            }
        ),
    ]

    monkeypatch.setattr(
        tools,
        "load_servicenow_settings",
        lambda: SimpleNamespace(instance_url="https://example.service-now.com"),
    )
    monkeypatch.setattr(tools, "_get_servicenow_token", _fake_token)
    monkeypatch.setattr(
        tools,
        "create_async_client",
        lambda *args, **kwargs: _DummyClient(responses, captured),
    )

    result = await tools.tool_list_catalog_categories(limit=10)

    assert result["total_returned"] == 1
    assert result["categories"] == [
        {
            "sys_id": "cat-1",
            "title": "Hardware",
            "description": "Devices",
            "item_count": 7,
        }
    ]
    assert "catalog-123" in captured["calls"][1]["url"]
