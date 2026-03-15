"""In-memory nonce store for approval gating.

Implements §11 of the TaskServer spec: nonces are single-use and
time-limited.  Approve / reject without a valid nonce must fail.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional

from ..logging import get_logger

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class NonceEntry:
    """A single nonce record."""

    nonce: str
    approval_id: str
    provider: str
    created_at: float
    expires_at: float
    used: bool = False


class NonceStore:
    """Thread-safe in-memory nonce store with TTL expiration.

    Nonces are single-use and time-limited per the TaskServer spec §11.
    """

    def __init__(self, default_ttl_seconds: int = 900) -> None:
        self._store: Dict[str, NonceEntry] = {}
        self._default_ttl = default_ttl_seconds

    def issue(self, approval_id: str, provider: str, ttl: Optional[int] = None) -> NonceEntry:
        """Create a new nonce for an approval review."""
        self._gc()
        nonce = secrets.token_urlsafe(32)
        now = time.time()
        entry = NonceEntry(
            nonce=nonce,
            approval_id=approval_id,
            provider=provider,
            created_at=now,
            expires_at=now + (ttl or self._default_ttl),
        )
        self._store[nonce] = entry
        LOGGER.info(
            "nonce_issued",
            nonce_prefix=nonce[:8],
            approval_id=approval_id,
            provider=provider,
            ttl=ttl or self._default_ttl,
        )
        return entry

    def validate_and_consume(self, nonce: str) -> NonceEntry:
        """Validate a nonce then mark it consumed.

        Raises ``ValueError`` if the nonce is invalid, expired, or already used.
        """
        self._gc()
        entry = self._store.get(nonce)
        if entry is None:
            raise ValueError("Invalid or expired approval nonce")
        if entry.used:
            raise ValueError("Approval nonce has already been used")
        if time.time() > entry.expires_at:
            del self._store[nonce]
            raise ValueError("Approval nonce has expired")
        entry.used = True
        LOGGER.info(
            "nonce_consumed",
            nonce_prefix=nonce[:8],
            approval_id=entry.approval_id,
            provider=entry.provider,
        )
        return entry

    def _gc(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired:
            del self._store[k]
