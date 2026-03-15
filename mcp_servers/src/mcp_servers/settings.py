"""Central configuration loading utilities."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class BaseEnvSettings(BaseSettings):
    """Base settings that enforce case sensitivity for env vars."""

    model_config = {"env_file": None, "case_sensitive": True, "extra": "ignore"}


class SharedAuthSettings(BaseEnvSettings):
    """Settings needed for Microsoft Entra ID validation."""

    aad_app_client_id: str = Field(..., alias="AAD_APP_CLIENT_ID")
    aad_app_tenant_id: str = Field(..., alias="AAD_APP_TENANT_ID")
    openapi_server_domain: Optional[str] = Field(None, alias="OPENAPI_SERVER_DOMAIN")


class WorkdayOAuthSettings(BaseEnvSettings):
    """Settings for Workday OAuth refresh-token flow."""

    token_url: str = Field(..., alias="WORKDAY_TOKEN_URL")
    workers_api_url: str = Field(..., alias="WORKDAY_WORKERS_API_URL")
    client_id: str = Field(..., alias="WORKDAY_CLIENT_CREDENTIALS")
    client_secret: str = Field(..., alias="WORKDAY_CLIENT_SECRET")
    refresh_token: str = Field(..., alias="WORKDAY_REFRESH_TOKEN")
    anonymous_employee_id: Optional[str] = Field(None, alias="WORKDAY_ANONYMOUS_EMPLOYEE_ID")


class GraphSettings(BaseEnvSettings):
    """Application credentials for Microsoft Graph fallbacks."""

    client_id: str = Field(..., alias="GRAPH_CLIENT_ID")
    client_secret: str = Field(..., alias="GRAPH_CLIENT_SECRET")
    tenant_id: str = Field(..., alias="GRAPH_TENANT_ID")


class ServiceNowSettings(BaseEnvSettings):
    """Settings for ServiceNow OAuth client-credentials flow."""

    instance_url: str = Field(..., alias="SERVICENOW_INSTANCE_URL")
    client_id: str = Field(..., alias="SERVICENOW_CLIENT_ID")
    client_secret: str = Field(..., alias="SERVICENOW_CLIENT_SECRET")


class SalesforceOAuthSettings(BaseEnvSettings):
    """Settings for Salesforce OAuth client-credentials flow."""

    domain: str = Field(..., alias="SALESFORCE_DOMAIN")
    client_id: str = Field(..., alias="SALESFORCE_CLIENT_ID")
    client_secret: str = Field(..., alias="SALESFORCE_CLIENT_SECRET")


class JiraSettings(BaseEnvSettings):
    """Settings for Jira API token authentication.

    API token (basic auth) is simplest for demos (impl notes §6).
    """

    base_url: str = Field(..., alias="JIRA_BASE_URL")
    email: str = Field(..., alias="JIRA_EMAIL")
    api_token: str = Field(..., alias="JIRA_API_TOKEN")
    project_key: Optional[str] = Field(None, alias="JIRA_PROJECT_KEY")


class TaskServerSettings(BaseEnvSettings):
    """Settings for the TaskServer orchestrator."""

    approval_review_ttl_seconds: int = Field(
        900, alias="TASKSERVER_APPROVAL_TTL"
    )


def _resolve_env_file(explicit: Optional[str] = None, prefix: str = "workday") -> Optional[str]:
    """Determine the environment file to load configuration from.

    *prefix* controls which env-file names are probed (e.g. "workday" or
    "servicenow").  The search order is:
    1. *explicit* path
    2. Well-known environment variables
    3. ``env/<prefix>.env``, ``env/<prefix>.local.env``, ``env/<prefix>.example.env``
    4. ``env/.env`` (catch-all)
    """

    candidates: list[Path] = []

    if explicit:
        candidates.append(Path(explicit).expanduser())

    for env_var in ("MCP_SERVERS_ENV_FILE", "WORKDAY_ENV_FILE"):
        value = os.getenv(env_var)
        if value:
            candidates.append(Path(value).expanduser())

    project_root = Path(__file__).resolve().parents[2]
    env_dir = project_root / "env"
    candidates.extend(
        [
            project_root / f".env.{prefix}",
            env_dir / f"{prefix}.env",
            env_dir / f"{prefix}.local.env",
            env_dir / f"{prefix}.example.env",
            project_root / ".env",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


@lru_cache(maxsize=1)
def load_shared_auth_settings(env_file: Optional[str] = None) -> SharedAuthSettings:
    return SharedAuthSettings(_env_file=_resolve_env_file(env_file))


@lru_cache(maxsize=1)
def load_workday_oauth_settings(env_file: Optional[str] = None) -> WorkdayOAuthSettings:
    return WorkdayOAuthSettings(_env_file=_resolve_env_file(env_file))


@lru_cache(maxsize=1)
def load_graph_settings(env_file: Optional[str] = None) -> GraphSettings:
    return GraphSettings(_env_file=_resolve_env_file(env_file))


@lru_cache(maxsize=1)
def load_servicenow_settings(env_file: Optional[str] = None) -> ServiceNowSettings:
    return ServiceNowSettings(_env_file=_resolve_env_file(env_file, prefix="servicenow"))


@lru_cache(maxsize=1)
def load_salesforce_settings(env_file: Optional[str] = None) -> SalesforceOAuthSettings:
    return SalesforceOAuthSettings(_env_file=_resolve_env_file(env_file, prefix="salesforce"))


@lru_cache(maxsize=1)
def load_jira_settings(env_file: Optional[str] = None) -> JiraSettings:
    return JiraSettings(_env_file=_resolve_env_file(env_file, prefix="jira"))


@lru_cache(maxsize=1)
def load_taskserver_settings(env_file: Optional[str] = None) -> TaskServerSettings:
    return TaskServerSettings(_env_file=_resolve_env_file(env_file, prefix="taskserver"))


def reset_settings_cache() -> None:
    load_shared_auth_settings.cache_clear()  # type: ignore[attr-defined]
    load_workday_oauth_settings.cache_clear()  # type: ignore[attr-defined]
    load_graph_settings.cache_clear()  # type: ignore[attr-defined]
    load_servicenow_settings.cache_clear()  # type: ignore[attr-defined]
    load_salesforce_settings.cache_clear()  # type: ignore[attr-defined]
    load_jira_settings.cache_clear()  # type: ignore[attr-defined]
    load_taskserver_settings.cache_clear()  # type: ignore[attr-defined]
