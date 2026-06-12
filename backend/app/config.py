from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEYES_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./meyes.db"
    jwt_secret: str = "meyes-dev-secret-change-me-in-production!"
    jwt_expire_minutes: int = 480

    # Engine deployment
    bind_output_dir: str = "./out/bind"
    kea_output_dir: str = "./out/kea"
    rndc_host: str = "127.0.0.1"
    rndc_port: int = 953
    rndc_key_file: str = "./deploy/bind9/rndc.key"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
