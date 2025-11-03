"""OAuth helpers for third-party APIs like Workday."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..logging import get_logger
from ..settings import WorkdayOAuthSettings, load_workday_oauth_settings

LOGGER = get_logger(__name__)


@dataclass
class OAuthToken:
    access_token: str
    token_type: str
    expires_in: Optional[int] = None


class WorkdayTokenProvider:
    """Refresh-token based authentication for Workday."""

    def __init__(self, settings: Optional[WorkdayOAuthSettings] = None) -> None:
        self.settings = settings or load_workday_oauth_settings()

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    async def get_access_token(self) -> OAuthToken:
        auth_header = httpx.BasicAuth(self.settings.client_id, self.settings.client_secret)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.settings.refresh_token,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            LOGGER.info("requesting_workday_token", token_url=self.settings.token_url)
            response = await client.post(
                self.settings.token_url,
                data=data,
                auth=auth_header,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            payload = response.json()
        return OAuthToken(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "Bearer"),
            expires_in=payload.get("expires_in"),
        )
