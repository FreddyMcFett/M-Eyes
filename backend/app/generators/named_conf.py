from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.generators import jinja_env
from app.models import Zone
from app.services import audit


def render_zones_conf(db: Session) -> str:
    zones = db.scalars(select(Zone).order_by(Zone.name)).all()
    template = jinja_env.get_template("zones.conf.j2")
    return template.render(
        zones=zones,
        zone_dir=get_settings().bind_zone_dir,
        config_version=audit.current_version(db),
    )
