from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEYES_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./meyes.db"
    jwt_secret: str = "meyes-dev-secret-change-me-in-production!"
    jwt_expire_minutes: int = 480

    # Comma-separated list of allowed CORS origins, or "*" for any. The web UI is
    # served same-origin behind the bundled nginx proxy, so production deployments
    # should pin this to their own host(s) instead of the wildcard default.
    cors_allow_origins: str = "*"

    # Engine deployment
    bind_output_dir: str = "./out/bind"
    kea_output_dir: str = "./out/kea"
    rndc_host: str = "127.0.0.1"
    rndc_port: int = 953
    rndc_key_file: str = "./out/bind/rndc.key"  # generated on first boot, not committed
    kea_ca_url: str = "http://127.0.0.1:8001"
    bind_zone_dir: str = "/etc/bind/m-eyes"  # path as seen by the BIND container

    # DNS defaults
    dns_default_soa_mname: str = "ns1.m-eyes.local."
    dns_default_soa_rname: str = "hostmaster.m-eyes.local."
    dns_default_ttl: int = 3600

    # DNS firewall (Response Policy Zone)
    rpz_zone_name: str = "rpz.m-eyes"

    # TLS / HTTPS — where the active server certificate, key, trust bundle and
    # the nginx options snippet are materialized for the TLS-terminating proxy.
    tls_dir: str = "./out/tls"
    # Default identity for the auto-generated self-signed bootstrap certificate.
    tls_default_hostname: str = "m-eyes.local"

    # In-app software update — shared volume where the API drops an update
    # request and the privileged `updater` sidecar reports progress. In-app
    # update is only offered when this directory is writable (i.e. the sidecar
    # is wired up, as in the Docker compose stack).
    update_dir: str = "./out/update"


    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()] or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


DEFAULT_JWT_SECRET = Settings.model_fields["jwt_secret"].default
