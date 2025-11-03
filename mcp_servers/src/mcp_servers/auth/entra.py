"""Microsoft Entra ID JWT validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import httpx
import jwt
from jwt import PyJWKClient

from ..logging import get_logger
from ..settings import SharedAuthSettings, load_shared_auth_settings

LOGGER = get_logger(__name__)


class TokenValidationError(Exception):
    """Raised when an Entra access token cannot be validated."""


@dataclass(slots=True)
class TokenValidationOptions:
    audience: str
    issuer: str
    scopes: Iterable[str]
    allowed_tenants: Iterable[str]


class EntraTokenValidator:
    """Validate Microsoft Entra access tokens using JWKS."""

    def __init__(self, settings: Optional[SharedAuthSettings] = None) -> None:
        self.settings = settings or load_shared_auth_settings()
        self._jwks_client: Optional[PyJWKClient] = None

    @property
    def jwks_client(self) -> PyJWKClient:
        if self._jwks_client is None:
            jwks_uri = self._discover_jwks_uri(self.settings.aad_app_tenant_id)
            self._jwks_client = PyJWKClient(jwks_uri)
        return self._jwks_client

    async def validate(self, token: str) -> Dict[str, Any]:
        options = TokenValidationOptions(
            audience=self.settings.aad_app_client_id,
            issuer=f"https://login.microsoftonline.com/{self.settings.aad_app_tenant_id}/v2.0",
            scopes=["workday_read"],
            allowed_tenants=[self.settings.aad_app_tenant_id],
        )
        return await self.validate_with_options(token, options)

    async def validate_with_options(
        self,
        token: str,
        options: TokenValidationOptions,
    ) -> Dict[str, Any]:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=options.audience,
                issuer=options.issuer,
            )
        except Exception as exc:  # noqa: BLE001
            raise TokenValidationError(str(exc)) from exc

        if "tid" not in payload or payload["tid"] not in options.allowed_tenants:
            raise TokenValidationError("Token tenant is not allowed")

        scopes = self._extract_scopes(payload)
        if options.scopes and not any(scope in scopes for scope in options.scopes):
            raise TokenValidationError("Token scope missing required permissions")

        return payload

    def _discover_jwks_uri(self, tenant: str) -> str:
        metadata_url = f"https://login.microsoftonline.com/{tenant}/.well-known/openid-configuration"
        LOGGER.info("fetching_openid_metadata", url=metadata_url)
        response = httpx.get(metadata_url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        jwks_uri = data.get("jwks_uri")
        if not jwks_uri:
            raise TokenValidationError("jwks_uri not found in OpenID configuration")
        return jwks_uri

    @staticmethod
    def _extract_scopes(payload: Dict[str, Any]) -> Iterable[str]:
        scopes: Iterable[str]
        if "scp" in payload:
            raw_scopes = payload["scp"]
            scopes = raw_scopes.split(" ") if isinstance(raw_scopes, str) else raw_scopes
        elif "roles" in payload:
            roles = payload["roles"]
            scopes = roles if isinstance(roles, list) else [roles]
        else:
            scopes = []
        return scopes
