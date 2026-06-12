# Versioning & Auditing

M-Eyes versions two things automatically: **your DDI configuration** (in-app) and **the
software itself** (CI release pipeline).

## Configuration versioning

Every create/update/delete of any DDI object writes an immutable changelog entry inside
the same database transaction as the change itself:

- who (actor), when, action, object type/id
- full JSON **before** and **after** snapshots

The changelog id doubles as the **global config version** shown in the top bar. Deploys
record which config version was pushed to each engine, so the UI can show drift
("BIND has v41, config is at v45").

### Rollback

Any entry can be rolled back from the Change Log page. Rollback is always a **new forward
change** — history is never rewritten:

| Original action | Rollback effect |
|---|---|
| `update` | the *before* snapshot is written back onto the object |
| `delete` | the object is recreated from its *before* snapshot |
| `create` | the object is deleted |

Rollbacks that would violate referential integrity (e.g. deleting an IP that a host still
references) fail with an explanatory `409` instead of cascading.

### Runbook

*Log & Report → Runbook* renders a complete, human-readable configuration document
(networks, zones, scopes, feeds) as Markdown, stamped with the config version and
timestamp — regenerated on demand, downloadable, never stale.

## Software release automation

The repository releases itself via **semantic-release** on every push to `main`:

1. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org)
   (`feat:`, `fix:`, `feat!:` …).
2. semantic-release computes the next version, generates release notes, updates
   `CHANGELOG.md`, bumps `backend/app/version.py`, `backend/pyproject.toml` and
   `frontend/package.json`, tags, and publishes a GitHub Release.
3. The Docs workflow regenerates the OpenAPI reference from the live FastAPI schema and
   redeploys this documentation site on every merge.
