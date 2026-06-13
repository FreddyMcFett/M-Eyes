"""Enterprise integration connectors (Fortinet and Microsoft).

Importing this package registers every built-in connector into the registry
exposed by :mod:`app.services.integrations.base`.
"""

from app.services.integrations import (  # noqa: F401  (import-for-side-effect: registration)
    entra,
    fortianalyzer,
    fortiauthenticator,
    fortigate,
    fortimanager,
    microsoft_dns,
)
from app.services.integrations.base import (  # noqa: F401
    REGISTRY,
    ConfigField,
    Connector,
    connector_catalog,
    get_connector,
)
