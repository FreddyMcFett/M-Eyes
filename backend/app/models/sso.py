from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SsoConfig(Base, TimestampMixin):
    """Single-row SAML 2.0 Service Provider configuration.

    M-Eyes acts as the SAML SP; the IdP (FortiAuthenticator, Microsoft Entra ID,
    Okta, …) asserts the user's identity. Only one active configuration is kept,
    pinned to id=1.
    """

    __tablename__ = "sso_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Display / button
    button_label: Mapped[str] = mapped_column(String(64), default="Sign in with SSO")

    # Identity Provider (from the IdP metadata)
    idp_entity_id: Mapped[str] = mapped_column(String(512), default="")
    idp_sso_url: Mapped[str] = mapped_column(String(512), default="")  # SingleSignOnService (Redirect)
    idp_slo_url: Mapped[str] = mapped_column(String(512), default="")  # SingleLogoutService (optional)
    idp_x509_cert: Mapped[str] = mapped_column(Text, default="")  # PEM or base64 signing certificate

    # Service Provider (this M-Eyes instance)
    sp_entity_id: Mapped[str] = mapped_column(String(512), default="")  # blank => derived from base URL
    base_url: Mapped[str] = mapped_column(String(512), default="")  # external https URL of M-Eyes

    # Attribute mapping — SAML attribute names that carry each field. Blank uses NameID for username.
    attr_username: Mapped[str] = mapped_column(String(255), default="")
    attr_email: Mapped[str] = mapped_column(String(255), default="")
    attr_display_name: Mapped[str] = mapped_column(String(255), default="")
    attr_groups: Mapped[str] = mapped_column(String(255), default="")  # attribute holding group/role names

    # Role mapping — IdP group value -> M-Eyes role. JSON object {"group": "role"}.
    role_mappings: Mapped[dict] = mapped_column(JSON, default=dict)
    default_role: Mapped[str] = mapped_column(String(32), default="viewer")
    allow_jit_provisioning: Mapped[bool] = mapped_column(Boolean, default=True)

    # Advanced settings
    name_id_format: Mapped[str] = mapped_column(
        String(128), default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    )
    sign_authn_requests: Mapped[bool] = mapped_column(Boolean, default=False)
    want_assertions_signed: Mapped[bool] = mapped_column(Boolean, default=True)
    want_response_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    force_authn: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_clock_skew_seconds: Mapped[int] = mapped_column(Integer, default=120)
    signature_algorithm: Mapped[str] = mapped_column(
        String(128), default="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    )
    # SP signing keypair (PEM) — required only when sign_authn_requests is on.
    sp_private_key: Mapped[str] = mapped_column(Text, default="")
    sp_x509_cert: Mapped[str] = mapped_column(Text, default="")
