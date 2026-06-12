from sqlalchemy.orm import Session

from app.config import get_settings
from app.generators import jinja_env
from app.services import audit
from app.services import rpz as rpz_service


def render_rpz_zone(db: Session) -> str:
    settings = get_settings()
    rows = []
    for rule in rpz_service.enabled_rules(db):
        rows.extend(rpz_service.rule_rows(rule))
    template = jinja_env.get_template("rpz.db.j2")
    return template.render(
        zone_name=settings.rpz_zone_name,
        soa_mname=settings.dns_default_soa_mname,
        soa_rname=settings.dns_default_soa_rname,
        # the global config version is monotonic, which makes it a valid SOA serial
        serial=audit.current_version(db),
        rows=rows,
        config_version=audit.current_version(db),
    )
