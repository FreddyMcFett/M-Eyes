#!/bin/sh
set -e

# Bootstrap the shared engine-config volumes so BIND9 and Kea can start
# before the first deploy from the UI.
BIND_DIR="${MEYES_BIND_OUTPUT_DIR:-/shared/bind}"
KEA_DIR="${MEYES_KEA_OUTPUT_DIR:-/shared/kea}"
mkdir -p "$BIND_DIR" "$KEA_DIR"
[ -f "$BIND_DIR/zones.conf" ] || : > "$BIND_DIR/zones.conf"
if [ ! -f "$KEA_DIR/kea-dhcp4.conf" ]; then
  cat > "$KEA_DIR/kea-dhcp4.conf" <<'EOF'
{
  "Dhcp4": {
    "interfaces-config": { "interfaces": ["*"] },
    "control-socket": { "socket-type": "unix", "socket-name": "/run/kea/kea4-ctrl-socket" },
    "lease-database": { "type": "memfile", "lfc-interval": 3600 },
    "valid-lifetime": 4000,
    "subnet4": []
  }
}
EOF
fi

echo "Running database migrations ..."
alembic upgrade head

if [ "${MEYES_SEED_DEMO:-true}" = "true" ]; then
  echo "Seeding demo data (set MEYES_SEED_DEMO=false to skip) ..."
  python -m app.scripts.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
