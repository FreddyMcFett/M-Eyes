"""Seed demo data so the UI is not empty on first run.

Usage: python -m app.scripts.seed
Idempotent: skips seeding when networks already exist.
"""

import logging

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models import Base, BlocklistEntry, Feed, Network, Tag, User
from app.security import hash_password
from app.services import dhcp as dhcp_service
from app.services import dns as dns_service
from app.services import events
from app.services import extattrs as extattr_service
from app.services import host as host_service
from app.services import ipam
from app.services import rpz as rpz_service

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("meyes.seed")

ACTOR = "seed"


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)) is None:
            db.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
            db.commit()
        if db.scalar(select(Network).limit(1)) is not None:
            logger.info("Database already seeded; nothing to do.")
            return

        logger.info("Seeding demo data ...")

        guest_tag = Tag(name="guest-wifi", color="#f0ad4e")
        server_tag = Tag(name="servers", color="#4caf50")
        db.add_all([guest_tag, server_tag])
        db.flush()

        ipam.create_network(db, ACTOR, {"cidr": "10.0.0.0/8", "name": "Corporate", "is_container": True})
        ipam.create_network(db, ACTOR, {"cidr": "10.10.0.0/16", "name": "HQ Zurich",
                                        "is_container": True, "site": "Zurich"})
        servers = ipam.create_network(db, ACTOR, {"cidr": "10.10.1.0/24", "name": "Servers",
                                                  "vlan": 101, "site": "Zurich",
                                                  "tag_ids": [server_tag.id]})
        clients = ipam.create_network(db, ACTOR, {"cidr": "10.10.20.0/24", "name": "Clients",
                                                  "vlan": 120, "site": "Zurich"})
        ipam.create_network(db, ACTOR, {"cidr": "10.10.30.0/24", "name": "Guest WiFi", "vlan": 130,
                                        "site": "Zurich", "tag_ids": [guest_tag.id]})
        dmz = ipam.create_network(db, ACTOR, {"cidr": "192.168.100.0/24", "name": "DMZ",
                                              "vlan": 200, "tag_ids": [server_tag.id]})

        dns_service.create_zone(db, ACTOR, {"name": "corp.m-eyes.local", "kind": "forward"})
        dns_service.create_zone(db, ACTOR, {"name": "1.10.10.in-addr.arpa", "kind": "reverse",
                                            "network_id": servers.id})
        dns_service.create_zone(db, ACTOR, {"name": "100.168.192.in-addr.arpa", "kind": "reverse",
                                            "network_id": dmz.id})

        # DHCP scope on the clients network
        subnet = dhcp_service.create_subnet(db, ACTOR, {"network_id": clients.id})
        dhcp_service.create_range(db, ACTOR, subnet,
                                  {"start_ip": "10.10.20.100", "end_ip": "10.10.20.200"})
        dhcp_service.set_option(db, ACTOR, {"name": "routers", "value": "10.10.20.1"}, subnet=subnet)
        dhcp_service.set_option(db, ACTOR, {"name": "domain-name-servers",
                                            "value": "10.10.1.53"}, subnet=subnet)
        dhcp_service.set_option(db, ACTOR, {"name": "domain-name", "value": "corp.m-eyes.local"})
        dhcp_service.create_reservation(db, ACTOR, subnet,
                                        {"mac": "00:09:0f:aa:bb:01", "ip": "10.10.20.50",
                                         "hostname": "printer-zh-01"})

        # Composite hosts (IP + A + PTR)
        for name, ip in [("ns1", "10.10.1.53"), ("web1", "10.10.1.80"), ("fortigate", "10.10.1.1")]:
            host_service.create_host(db, ACTOR, f"{name}.corp.m-eyes.local", servers.id, ip=ip)

        # A few standalone allocations
        for last_octet, hostname in [(10, "esx-01"), (11, "esx-02"), (20, "backup-01")]:
            ipam.create_ip(db, ACTOR, servers, {"ip": f"10.10.1.{last_octet}", "status": "used",
                                                "hostname": hostname})
        for last_octet in (5, 6):
            ipam.create_ip(db, ACTOR, dmz, {"ip": f"192.168.100.{last_octet}", "status": "used",
                                            "hostname": f"dmz-web-{last_octet}"})

        db.add_all([
            BlocklistEntry(value="203.0.113.13", reason="Known C2 server", created_by=ACTOR),
            BlocklistEntry(value="198.51.100.0/24", reason="Scanning subnet", created_by=ACTOR),
        ])

        db.add_all([
            Feed(slug="networks", name="All networks", kind="networks"),
            Feed(slug="blocklist", name="Blocked addresses", kind="blocklist"),
            Feed(slug="fqdn", name="Known FQDNs", kind="fqdn"),
            Feed(slug="servers", name="Server networks (tag)", kind="tag", tag_id=server_tag.id),
        ])

        # Extensible attributes (Infoblox-style typed metadata)
        extattr_service.create_def(db, ACTOR, {"name": "Owner", "type": "string",
                                               "comment": "Responsible team or person"})
        extattr_service.create_def(db, ACTOR, {"name": "Environment", "type": "enum",
                                               "allowed_values": ["prod", "staging", "dev"]})
        extattr_service.create_def(db, ACTOR, {"name": "Location", "type": "string",
                                               "comment": "Rack / room / site detail"})
        extattr_service.set_for_object(db, ACTOR, "network", servers.id,
                                       {"Owner": "infrastructure", "Environment": "prod"})

        # DNS firewall (RPZ) demo rules
        rpz_service.create_rule(db, ACTOR, {"fqdn": "malware.example.com", "action": "block",
                                            "comment": "Demo: blocked domain"})
        rpz_service.create_rule(db, ACTOR, {"fqdn": "tracker.example.net", "action": "substitute",
                                            "substitute": "10.10.1.80",
                                            "comment": "Demo: walled garden"})

        events.emit(db, "info", "system", "Demo data seeded")
        db.commit()
        logger.info("Done. Login with admin/admin.")


if __name__ == "__main__":
    seed()
