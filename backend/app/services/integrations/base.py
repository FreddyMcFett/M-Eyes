"""Connector framework: a registry of pluggable enterprise integrations.

A connector declares the configuration fields it needs and implements
``test_connection`` and ``sync``. Network calls are best-effort and must degrade
gracefully (return a failure tuple / raise ConnectorError) so an unreachable
device never takes the control plane down.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import ClassVar

from sqlalchemy.orm import Session

from app.models import Integration


class ConnectorError(Exception):
    """Raised when a connector cannot complete an operation."""


@dataclass
class ConfigField:
    key: str
    label: str
    type: str = "string"  # string|password|number|bool|textarea
    required: bool = False
    help: str = ""
    placeholder: str = ""
    default: str = ""
    advanced: bool = False


class Connector:
    """Base connector. Subclasses override the class attributes and methods."""

    kind: ClassVar[str] = ""
    label: ClassVar[str] = ""
    category: ClassVar[str] = "fortinet"  # fortinet|microsoft
    description: ClassVar[str] = ""
    capabilities: ClassVar[list[str]] = []
    # Generic credential fields the UI should render (in addition to `settings`).
    uses_base_url: ClassVar[bool] = True
    base_url_label: ClassVar[str] = "Base URL"
    base_url_placeholder: ClassVar[str] = "https://device.example.com"
    uses_username: ClassVar[bool] = False
    username_label: ClassVar[str] = "Username"
    uses_secret: ClassVar[bool] = True
    secret_label: ClassVar[str] = "API token"
    fields: ClassVar[list[ConfigField]] = []

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        raise NotImplementedError

    def sync(self, db: Session, integration: Integration) -> dict:
        raise NotImplementedError

    # ---- helpers -------------------------------------------------------- #
    def descriptor(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "capabilities": self.capabilities,
            "uses_base_url": self.uses_base_url,
            "base_url_label": self.base_url_label,
            "base_url_placeholder": self.base_url_placeholder,
            "uses_username": self.uses_username,
            "username_label": self.username_label,
            "uses_secret": self.uses_secret,
            "secret_label": self.secret_label,
            "fields": [asdict(f) for f in self.fields],
        }


REGISTRY: dict[str, Connector] = {}


def register(connector: Connector) -> Connector:
    REGISTRY[connector.kind] = connector
    return connector


def get_connector(kind: str) -> Connector:
    connector = REGISTRY.get(kind)
    if connector is None:
        raise ConnectorError(f"Unknown integration kind {kind!r}")
    return connector


def connector_catalog() -> list[dict]:
    return [c.descriptor() for c in sorted(REGISTRY.values(), key=lambda c: (c.category, c.label))]
