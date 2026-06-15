#!/bin/sh
# M-Eyes in-app updater sidecar.
#
# This is the ONLY container with access to the Docker socket. It watches a
# shared volume for an update request dropped by the API (System -> Settings ->
# Backup & Updates -> "Update now") and then performs, against the host Docker
# daemon:
#
#     docker compose pull <services>
#     docker compose up -d <services>
#
# ...for the M-Eyes application services (api + frontend by default), reporting
# progress back into the same volume. Keeping Docker/host privileges in this
# tiny, fixed-purpose sidecar keeps them out of the internet-facing API.
#
# The API only ever writes a validated semver into the request, and this script
# only ever interpolates it into the image tag, so a request can never run an
# arbitrary command.
set -eu

UPDATE_DIR="${MEYES_UPDATE_DIR:-/shared/update}"
SERVICES="${MEYES_UPDATE_SERVICES:-api frontend}"
PROJECT_DIR="${MEYES_PROJECT_DIR:-/project}"
COMPOSE_FILE="${MEYES_COMPOSE_FILE:-$PROJECT_DIR/docker-compose.yml}"
POLL_SECONDS="${MEYES_UPDATE_POLL_SECONDS:-5}"
# The release pipeline publishes the GitHub release/tag a few minutes before the
# multi-arch images finish building and land in GHCR. An update triggered right
# after a release can therefore race the registry, so retry the pull a few times
# before giving up rather than failing on a transient "manifest unknown".
PULL_ATTEMPTS="${MEYES_PULL_ATTEMPTS:-5}"
PULL_RETRY_SECONDS="${MEYES_PULL_RETRY_SECONDS:-20}"

REQUEST_FILE="$UPDATE_DIR/request.json"
STATUS_FILE="$UPDATE_DIR/status.json"
LOG_FILE="$UPDATE_DIR/update.log"

mkdir -p "$UPDATE_DIR"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Make sure the compose plugin is available (most recent docker:*-cli images
# bundle it, but install it as a safety net if not).
if ! docker compose version >/dev/null 2>&1; then
  apk add --no-cache docker-cli-compose >/dev/null 2>&1 || true
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --project-directory "$PROJECT_DIR" -f "$COMPOSE_FILE" "$@"
  else
    docker-compose --project-directory "$PROJECT_DIR" -f "$COMPOSE_FILE" "$@"
  fi
}

# Pull the target images, retrying a few times so an update that races the
# post-release image build (images not in GHCR yet) recovers on its own instead
# of failing outright. Status is refreshed between attempts so the UI shows
# progress and the API never treats the in-flight update as stale.
pull_with_retry() {
  _attempt=1
  while : ; do
    echo "--- docker compose pull $SERVICES (attempt $_attempt/$PULL_ATTEMPTS) ---"
    # shellcheck disable=SC2086
    if compose pull $SERVICES; then
      return 0
    fi
    if [ "$_attempt" -ge "$PULL_ATTEMPTS" ]; then
      return 1
    fi
    write_status pulling \
      "Images for v$TARGET aren't available yet; retrying ($_attempt/$PULL_ATTEMPTS) ..." \
      "$TARGET" "$REQ_ID" null
    echo "[updater] pull attempt $_attempt/$PULL_ATTEMPTS failed; retrying in ${PULL_RETRY_SECONDS}s" \
         "(images for v$TARGET may still be publishing)"
    _attempt=$((_attempt + 1))
    sleep "$PULL_RETRY_SECONDS"
  done
}

# Extract a JSON string value for a key from a file. Inputs are produced and
# validated by the API (hex ids, semver versions), so simple extraction is safe.
json_value() {
  sed -n 's/.*"'"$1"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$2" 2>/dev/null || true
}

# Write status.json atomically. $1 phase  $2 message  $3 target  $4 id  $5 rc
write_status() {
  _msg=$(printf '%s' "$2" | tr '\n\r' '  ' | sed 's/\\/\\\\/g; s/"/\\"/g')
  cat > "$STATUS_FILE.tmp" <<EOF
{"phase":"$1","message":"$_msg","target_version":"$3","processed_id":"$4","returncode":$5,"updated_at":"$(now)"}
EOF
  mv -f "$STATUS_FILE.tmp" "$STATUS_FILE"
}

# Baseline so a sidecar restart never replays an already-processed request.
PROCESSED_ID=""
if [ -f "$STATUS_FILE" ]; then
  PROCESSED_ID=$(json_value processed_id "$STATUS_FILE")
fi
if [ -z "$PROCESSED_ID" ] && [ -f "$REQUEST_FILE" ]; then
  PROCESSED_ID=$(json_value id "$REQUEST_FILE")
fi

echo "[updater] watching $REQUEST_FILE (services: $SERVICES, compose: $COMPOSE_FILE)"

while true; do
  if [ -f "$REQUEST_FILE" ]; then
    REQ_ID=$(json_value id "$REQUEST_FILE")
    if [ -n "$REQ_ID" ] && [ "$REQ_ID" != "$PROCESSED_ID" ]; then
      TARGET=$(json_value target_version "$REQUEST_FILE")
      echo "[updater] processing request $REQ_ID -> v$TARGET"
      : > "$LOG_FILE"
      # Run the whole update in a brace group (NOT a subshell) so PROCESSED_ID
      # persists, while redirecting all command output to the log the API tails.
      {
        echo "=== M-Eyes update to v$TARGET ($(now)) ==="
        export MEYES_VERSION="$TARGET"

        write_status pulling "Downloading v$TARGET ..." "$TARGET" "$REQ_ID" null
        if pull_with_retry; then
          write_status recreating "Restarting services ($SERVICES) ..." "$TARGET" "$REQ_ID" null
          echo "--- docker compose up -d $SERVICES ---"
          # This recreates the api + frontend with the new image. This sidecar
          # uses a different (unchanged) image, so it is never recreated and
          # survives to record the result.
          # shellcheck disable=SC2086
          if compose up -d $SERVICES; then
            write_status done "Updated to v$TARGET and restarted $SERVICES." "$TARGET" "$REQ_ID" 0
            echo "[updater] update complete"
          else
            write_status error "Restart failed; see the update log." "$TARGET" "$REQ_ID" 1
            echo "[updater] 'docker compose up' failed"
          fi
        else
          write_status error \
            "Couldn't download the v$TARGET images. They may still be publishing (the release build runs for a few minutes after a new version appears) — try again shortly. See the update log." \
            "$TARGET" "$REQ_ID" 1
          echo "[updater] 'docker compose pull' failed after $PULL_ATTEMPTS attempt(s)"
        fi
        PROCESSED_ID="$REQ_ID"
      } >> "$LOG_FILE" 2>&1
    fi
  fi
  sleep "$POLL_SECONDS"
done
