# Upgrading & Backup

M-Eyes is designed to be upgraded in place: **your data always survives an
upgrade**. Everything lives in named Docker volumes (`pgdata` for the
database, plus the engine-config and TLS volumes), and database schema
migrations (Alembic) run automatically every time the API container starts —
old databases are migrated forward without manual steps.

## In-app update (recommended)

You don't have to SSH into the server to upgrade. Open **System → Settings →
Backup & Updates → Software Updates**:

1. **Check now** compares the running version against the latest GitHub release.
2. When an update is available, **Update now & restart** downloads the new
   images and restarts the M-Eyes services in place — live, from the browser.
   The page shows progress, briefly loses contact while the API restarts, then
   reconnects and offers a **Reload** once the new version is running.

Your data is preserved (the database lives in a persistent volume and schema
migrations run automatically on start), and DNS/DHCP keep serving throughout —
only the control plane (API + UI) is restarted, not BIND9/Kea/PostgreSQL.

> **Just-released versions:** the container images are built and pushed a few
> minutes *after* a new release is tagged. The update check waits for those
> images before offering the update, so right after a release you may briefly
> see *"vX.Y.Z is publishing"* instead of an **Update now** button — that's
> expected; check again in a few minutes. (If an update is triggered during that
> window anyway, the updater retries the download a few times before reporting
> the images aren't available yet.)

### How it works & security

A small `updater` sidecar — the only container with access to the Docker
socket — performs `docker compose pull` + `docker compose up -d` for the app
services when you click the button. The internet-facing API never touches
Docker; it only drops a request (a validated version string) into a shared
volume that the sidecar acts on, and only the authenticated, admin-only update
API can do so.

Because mounting the Docker socket grants the sidecar root-equivalent control
of the host, you can remove the `updater` service from `docker-compose.yml` to
disable in-app updates — the UI then falls back to showing the manual commands
below.

> **Note:** in-app update reuses your `.env` for the recreated containers
> (`MEYES_JWT_SECRET`, `MEYES_HOSTNAME`, …). Keep your configuration in `.env`
> (as in `.env.example`) rather than only in the host shell, so logins survive
> the restart.

## Upgrading manually on the host

Every release publishes versioned images to GitHub Container Registry
(`ghcr.io/freddymcfett/m-eyes-api` and `ghcr.io/freddymcfett/m-eyes-frontend`),
so a manual upgrade is just:

```bash
docker compose pull
docker compose up -d
```

### Pinning a version

By default compose follows the `latest` tag. For controlled upgrades pin a
release in `.env`:

```bash
MEYES_VERSION=1.3.0
```

then bump the value and `docker compose pull && docker compose up -d` when
you decide to move.

### `docker compose pull` fails with `error from registry: denied`

A `denied` error on `ghcr.io/freddymcfett/m-eyes-api` or
`ghcr.io/freddymcfett/m-eyes-frontend` (while the third-party images pull
fine) means the registry will not serve those images to you. Two causes:

1. **The images aren't published yet.** Releases publish them automatically;
   if a release predates that automation, build them once from the
   **Actions → Publish Docker images → Run workflow** button (enter the
   version, e.g. `1.6.0`).
2. **The GHCR packages are private.** New GHCR packages default to private, so
   an unauthenticated pull is denied. For public distribution, set each
   package to public once: **GitHub → your profile/org → Packages →
   `m-eyes-api` / `m-eyes-frontend` → Package settings → Change visibility →
   Public**. To keep them private instead, authenticate on the host first:

   ```bash
   echo "$GHCR_PAT" | docker login ghcr.io -u <github-user> --password-stdin
   ```

   using a token with `read:packages`.

If you can't pull right now, you can always upgrade from source instead (see
below) — it needs no registry access.

### Source installs

If you built from a git checkout instead of pulling images:

```bash
git pull
docker compose up -d --build
```

Migrations run on start exactly the same way.

### Rolling back a release

Set `MEYES_VERSION` back to the previous release and `docker compose up -d`.
Schema migrations are forward-only, so restore a configuration backup (or a
`pg_dump`) taken before the upgrade if the newer schema is incompatible.

## Configuration backup & restore

**System → Settings → Backup & Updates → Download backup** exports the whole
configuration — networks, IPs, zones, records, DNS views, DHCP scopes, hosts,
extensible attributes, DNS firewall rules, threat feeds, Fortinet feeds,
blocklist, runtime settings and the complete change log — as one JSON file.

Restoring the file (same page) **replaces** the current configuration;
primary keys are preserved so all cross-references stay intact. User
accounts and TLS private keys are deliberately excluded from backups, so a
restore never touches logins or certificates.

The same operations are available to scripts via the API:

```bash
# nightly config backup
curl -H "X-API-Key: $KEY" https://meyes.example.com/api/v1/system/backup \
  > m-eyes-$(date +%F).json

# restore
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  --data @m-eyes-2026-06-12.json https://meyes.example.com/api/v1/system/restore
```

## Database-level backups

For disaster recovery of the full instance (including user accounts and
certificates), back up PostgreSQL itself:

```bash
docker compose exec postgres pg_dump -U meyes meyes > m-eyes-db.sql
```

Restore into a fresh stack with `psql` before the first API start, or simply
keep snapshots of the `pgdata` volume.
