from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderResult:
    accepted: bool
    provider_message_id: Optional[str] = None


class ProviderRejected(Exception):
    """Meta rejected the message (e.g. template not approved, wrong token, 401/403/429)."""


class ProviderTimeout(Exception):
    """Request timed out before Meta responded."""


class ProviderUnavailable(Exception):
    """Meta returned a 5xx or the connection failed."""


class ProviderConfigError(Exception):
    """Misconfiguration detected (e.g. missing credentials or invalid settings)."""
