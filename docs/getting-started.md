# Getting Started

## Option 1 — Docker Compose (full stack)

```bash
git clone https://github.com/FreddyMcFett/M-Eyes.git
cd M-Eyes
docker compose up -d --build
```

| Service | URL |
|---|---|
| Web UI | **https://localhost:8443** |
| API / OpenAPI docs | http://localhost:8000/docs |
| Fortinet feeds | https://localhost:8443/feeds/&lt;slug&gt;.txt |
| BIND9 (DNS) | localhost:5353 |

The web UI is served over **HTTPS on port 8443**. Plain HTTP on
`http://localhost:8080` redirects to HTTPS, so always open the UI with
`https://` — pointing a browser at `:8080` directly can fail with
`ERR_SSL_PROTOCOL_ERROR` when the browser forces TLS on the HTTP port.

On first start M-Eyes generates a **self-signed certificate**, so your browser
will warn until you import a CA-signed one (do this from
*System → Settings → HTTPS / TLS*). Set `MEYES_HOSTNAME` before the first start
to control the certificate's CN/SAN.

Login with **admin / admin** (change the password in *System → Settings*).
Demo data is seeded automatically; set `MEYES_SEED_DEMO=false` to skip.

Try it:

```bash
# deploy zones to BIND from the UI (DNS -> Deploy to BIND), then:
dig @localhost -p 5353 ns1.corp.m-eyes.local

# fetch a Fortinet feed (token shown on the Feeds page):
curl -k "https://localhost:8443/feeds/networks.txt?token=<token>"
```

!!! warning "Production notes"
    - Put a TLS terminator in front (feeds use HTTP basic auth).
    - Regenerate `deploy/bind9/rndc.key` (`rndc-confgen -a`) — the committed key is dev-only.
    - Set `MEYES_JWT_SECRET`.
    - Real DHCP service needs L2 access; run the Kea container with `network_mode: host`.

## Option 2 — Local development (no Docker)

Backend:

```bash
cd backend
pip install -e ".[dev]"
python -m app.scripts.seed          # SQLite + demo data
uvicorn app.main:app --reload       # http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173 (proxies /api + /feeds)
```

Run the tests:

```bash
cd backend && pytest
```

## Environment variables

All backend settings are prefixed `MEYES_` (see `backend/app/config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `MEYES_DATABASE_URL` | `sqlite:///./meyes.db` | SQLAlchemy URL (PostgreSQL in compose) |
| `MEYES_JWT_SECRET` | dev value | JWT signing secret |
| `MEYES_BIND_OUTPUT_DIR` | `./out/bind` | Where zone files are published |
| `MEYES_KEA_OUTPUT_DIR` | `./out/kea` | Where `kea-dhcp4.conf` is published |
| `MEYES_RNDC_HOST` / `MEYES_RNDC_PORT` | `127.0.0.1` / `953` | BIND control channel |
| `MEYES_RNDC_KEY_FILE` | `./deploy/bind9/rndc.key` | rndc key |
| `MEYES_KEA_CA_URL` | `http://127.0.0.1:8001` | Kea Control Agent |
