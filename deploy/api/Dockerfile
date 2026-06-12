FROM python:3.12-slim

# bind9-utils provides rndc + named-checkzone used by the BIND deployer
RUN apt-get update \
    && apt-get install -y --no-install-recommends bind9-utils bind9-dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/m-eyes

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN pip install --no-cache-dir .

COPY deploy/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
