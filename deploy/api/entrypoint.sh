#!/bin/sh
set -e

# Bootstrap the shared engine-config volumes so BIND9 and Kea can start
# before the first deploy from the UI.
BIND_DIR="${MEYES_BIND_OUTPUT_DIR:-/shared/bind}"
KEA_DIR="${MEYES_KEA_OUTPUT_DIR:-/shared/kea}"
mkdir -p "$BIND_DIR" "$KEA_DIR"
[ -f "$BIND_DIR/zones.conf" ] || : > "$BIND_DIR/zones.conf"
[ -f "$BIND_DIR/rpz-options.conf" ] || : > "$BIND_DIR/rpz-options.conf"

# Generate a unique rndc control key on first boot instead of shipping a static
# secret in the image/repo. BIND and the API share it through this volume.
RNDC_KEY_FILE="${MEYES_RNDC_KEY_FILE:-$BIND_DIR/rndc.key}"
if [ ! -f "$RNDC_KEY_FILE" ]; then
  RNDC_SECRET="$(head -c 32 /dev/urandom | base64)"
  cat > "$RNDC_KEY_FILE" <<EOF
key "rndc-key" {
    algorithm hmac-sha256;
    secret "$RNDC_SECRET";
};
EOF
  chmod 644 "$RNDC_KEY_FILE"
fi
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
