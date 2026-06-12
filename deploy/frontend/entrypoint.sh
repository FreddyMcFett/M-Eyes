#!/bin/sh
# Frontend container entrypoint.
#
# nginx needs a certificate present before it can open the :443 listener, but
# the real (UI-managed) certificate is published by the API a moment later. We
# therefore drop a throwaway bootstrap certificate if none exists yet, then run
# a watcher that reloads nginx whenever the API republishes TLS material.
set -e

TLS_DIR="${MEYES_TLS_DIR:-/shared/tls}"
mkdir -p "$TLS_DIR"

# Required include files must exist or nginx will refuse to start.
[ -f "$TLS_DIR/http-redirect.conf" ] || printf 'return 301 https://$host$request_uri;\n' > "$TLS_DIR/http-redirect.conf"
[ -f "$TLS_DIR/options.conf" ] || printf 'ssl_protocols TLSv1.2 TLSv1.3;\nssl_prefer_server_ciphers on;\n' > "$TLS_DIR/options.conf"

if [ ! -s "$TLS_DIR/server.crt" ] || [ ! -s "$TLS_DIR/server.key" ]; then
  echo "[entrypoint] generating bootstrap self-signed certificate ..."
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$TLS_DIR/server.key" -out "$TLS_DIR/server.crt" \
    -days 825 -subj "/CN=${MEYES_BOOTSTRAP_CN:-m-eyes.local}" \
    -addext "subjectAltName=DNS:${MEYES_BOOTSTRAP_CN:-m-eyes.local},DNS:localhost" >/dev/null 2>&1
  chmod 600 "$TLS_DIR/server.key"
fi

# Background watcher: reload nginx when the API updates the reload marker.
(
  MARKER="$TLS_DIR/reload"
  LAST=""
  while true; do
    if [ -f "$MARKER" ]; then
      CUR="$(cat "$MARKER" 2>/dev/null || true)"
      if [ "$CUR" != "$LAST" ] && [ -n "$LAST" ]; then
        echo "[entrypoint] TLS material changed; reloading nginx"
        nginx -s reload 2>/dev/null || true
      fi
      LAST="$CUR"
    fi
    sleep 5
  done
) &

exec nginx -g 'daemon off;'
