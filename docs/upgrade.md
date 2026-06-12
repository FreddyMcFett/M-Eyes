# Upgrading & Backup

M-Eyes is designed to be upgraded in place: **your data always survives an
upgrade**. Everything lives in named Docker volumes (`pgdata` for the
database, plus the engine-config and TLS volumes), and database schema
migrations (Alembic) run automatically every time the API container starts —
old databases are migrated forward without manual steps.

## Upgrading a Docker install

Every release publishes versioned images to GitHub Container Registry
(`ghcr.io/freddymcfett/m-eyes-api` and `ghcr.io/freddymcfett/m-eyes-frontend`),
so an upgrade is just:

```bash
docker compose pull
docker compose up -d
```

The UI tells you when a new release is available: **System → Settings →
Backup & Updates** compares the running version against the latest GitHub
release.

### Pinning a version

By default compose follows the `latest` tag. For controlled upgrades pin a
release in `.env`:

```bash
MEYES_VERSION=1.3.0
```

then bump the value and `docker compose pull && docker compose up -d` when
you decide to move.

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
