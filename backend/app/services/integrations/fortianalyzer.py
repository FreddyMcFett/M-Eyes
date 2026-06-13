"""FortiAnalyzer connector.

M-Eyes forwards its operational event stream to FortiAnalyzer (or any collector)
as syslog — configured under System → Settings → Advanced Logging. This connector
verifies reachability of the FortiAnalyzer host/port and surfaces the syslog
target in one place alongside the other Fortinet integrations.
"""

from __future__ import annotations

import socket

from sqlalchemy.orm import Session

from app.models import Integration
from app.services import app_settings
from app.services.integrations.base import ConfigField, Connector, register


class FortiAnalyzerConnector(Connector):
    kind = "fortianalyzer"
    label = "FortiAnalyzer"
    category = "fortinet"
    description = "Forward M-Eyes events to FortiAnalyzer via syslog and verify collector reachability."
    capabilities = ["syslog", "test"]
    uses_base_url = False
    uses_secret = False
    fields = [
        ConfigField("host", "FortiAnalyzer host", required=True, placeholder="faz.example.com"),
        ConfigField("port", "Syslog port", type="number", default="514"),
        ConfigField("protocol", "Protocol", default="udp", help="udp or tcp", advanced=True),
    ]

    def _target(self, integration: Integration) -> tuple[str, int, str]:
        s = integration.settings or {}
        return s.get("host", ""), int(s.get("port", 514) or 514), s.get("protocol", "udp")

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        host, port, protocol = self._target(integration)
        if not host:
            return False, "FortiAnalyzer host is not configured"
        try:
            if protocol == "tcp":
                with socket.create_connection((host, port), timeout=5):
                    return True, f"TCP connection to {host}:{port} succeeded"
            # UDP is connectionless; a successful sendto only proves the socket layer.
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5)
                sock.sendto(b"<14>m-eyes connectivity test", (host, port))
            return True, f"UDP probe sent to {host}:{port} (delivery not guaranteed)"
        except OSError as exc:
            return False, f"Could not reach {host}:{port}: {exc}"

    def sync(self, db: Session, integration: Integration) -> dict:
        host, port, protocol = self._target(integration)
        # Mirror the integration target into the live syslog forwarder settings.
        app_settings.set_many(db, {
            "syslog_enabled": "true",
            "syslog_host": host,
            "syslog_port": str(port),
            "syslog_protocol": protocol,
        })
        from app.services import events

        events.reset_syslog()
        detail = f"Syslog forwarding enabled to {host}:{port}/{protocol}"
        events.emit(db, "info", "integration", f"FortiAnalyzer ({integration.name}): {detail}")
        return {"detail": detail}


register(FortiAnalyzerConnector())
