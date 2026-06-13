# SAML Single Sign-On

M-Eyes ships an enterprise-grade **SAML 2.0 Service Provider (SP)**. Your users
authenticate against your own Identity Provider (IdP) and land in M-Eyes already
signed in — no second password, central account lifecycle, and **group-driven
role assignment**.

This guide walks through wiring M-Eyes (SP) to **FortiAuthenticator** (IdP) end to
end, then covers generic IdPs (Microsoft Entra ID, Okta, Keycloak, ADFS) and every
advanced setting.

!!! tip "Why FortiAuthenticator?"
    If you already run the Fortinet fabric, FortiAuthenticator is the natural IdP:
    it federates your AD/LDAP users and MFA, and M-Eyes treats its SAML groups as
    role grants. It is the **recommended** IdP and the only one with a one-to-one
    walkthrough below.

---

## How it works

```
                 1. user clicks "Sign in with FortiAuthenticator"
   Browser ───────────────────────────────────────────────►  M-Eyes (SP)
       ▲                                                          │
       │                                          2. redirect (SAML AuthnRequest)
       │                                                          ▼
       │                                              FortiAuthenticator (IdP)
       │   4. POST signed SAMLResponse to the ACS               │
       └──────────────────────────────────────────────────◄────┘
                                                   3. user authenticates (AD/LDAP/MFA)

   5. M-Eyes verifies the assertion signature, validates the conditions,
      maps the IdP groups to an M-Eyes role, provisions/updates the user,
      and issues a session token.
```

M-Eyes verifies the assertion's **XML signature** against the IdP certificate,
enforces the **validity window** (`NotBefore`/`NotOnOrAfter` with configurable
clock skew) and the **audience restriction**, and only then trusts the identity.
Tampered or expired assertions are rejected.

---

## Endpoints (Service Provider metadata)

Set **M-Eyes base URL** first (System → SSO / SAML), then these are generated for
you and shown on the page with copy buttons:

| Field | Value |
|---|---|
| **SP entity ID** | `https://<your-meyes>/api/v1/sso/metadata` (override allowed) |
| **ACS (reply) URL** | `https://<your-meyes>/api/v1/auth/sso/acs` |
| **SP metadata URL** | `https://<your-meyes>/api/v1/sso/metadata` |
| **Binding** | HTTP-POST (ACS), HTTP-Redirect (AuthnRequest) |

The metadata URL returns standards-compliant SP metadata XML you can import
directly into most IdPs.

---

## Part 1 — Configure FortiAuthenticator (IdP)

> Tested with FortiAuthenticator 6.4+. Menu labels may differ slightly by version.

### 1. Create the SAML IdP portal (if you don't have one)

1. **Authentication → SAML IdP → General**.
2. Enable **SAML IdP**.
3. Set the **Server address** to the FortiAuthenticator FQDN clients reach
   (e.g. `fac.example.com`). This forms the IdP URLs.
4. Choose the **Default IdP certificate** (a server certificate FortiAuthenticator
   signs assertions with). Note it — you will export it for M-Eyes in step 4.
5. Bind a **realm** (the AD/LDAP/local user source) and, optionally, an MFA policy.

### 2. Add M-Eyes as a Service Provider

1. **Authentication → SAML IdP → Service Providers → Create New**.
2. **SP name**: `M-Eyes`.
3. **SP entity ID**: paste the value from the M-Eyes SSO page
   (`https://<your-meyes>/api/v1/sso/metadata`).
4. **ACS (Assertion Consumer Service) URL**: paste the M-Eyes ACS URL
   (`https://<your-meyes>/api/v1/auth/sso/acs`).
5. **SP certificate**: leave empty unless you enable *signed AuthnRequests* in
   M-Eyes (see [Advanced](#advanced-settings)).

### 3. Publish the user attributes M-Eyes consumes

Under the SP's **SAML attributes** (or *Assertion Attributes*), add:

| Attribute name (SAML) | FortiAuthenticator value | Used by M-Eyes for |
|---|---|---|
| `username` | Username | the M-Eyes username |
| `email` | Email | the user's email |
| `displayname` | Full name / Display name | display name |
| `groups` | **Group membership** (multi-valued) | **role mapping** |

Set the **NameID** to the user's email or username (match the *NameID format* you
pick in M-Eyes; email is the default).

!!! important "Groups are how roles are granted"
    Make sure the **groups** attribute is *multi-valued* and emits the group names
    you will map to M-Eyes roles (e.g. `meyes-admins`, `meyes-operators`). In
    FortiAuthenticator these are usually your AD/LDAP groups or local user groups.

### 4. Export the IdP signing certificate

1. **System → Certificates → Local Services** (or **CA Certificates** if the IdP
   cert is CA-signed).
2. Export the **certificate used by the SAML IdP** (the one from step 1.4) in
   **PEM** (Base64) format. You need the certificate only — *not* the private key.

### 5. Note the IdP URLs

From **Authentication → SAML IdP → General**, record:

- **IdP entity ID** (e.g. `https://fac.example.com/saml-idp/<name>/metadata/`)
- **Single Sign-On URL** / login URL (e.g. `https://fac.example.com/saml-idp/<name>/login/`)
- **Single Logout URL** (optional)

FortiAuthenticator can also serve **IdP metadata** — if so, you can read all three
values from there.

---

## Part 2 — Configure M-Eyes (SP)

Open **System → SSO / SAML** (admin only).

1. **M-Eyes base URL** — the external HTTPS URL users reach M-Eyes on
   (`https://meyes.example.com`). This drives the SP entity ID, ACS and metadata
   URLs shown above. Copy those into FortiAuthenticator if you didn't already.
2. **Identity Provider**:
   - **IdP entity ID** — from step 5.
   - **IdP Single Sign-On URL** — the login URL from step 5.
   - **IdP Single Logout URL** — optional.
   - **IdP signing certificate** — paste the PEM from step 4 (a bare base64 blob
     also works; M-Eyes normalises it).
3. **Attribute & role mapping**:
   - **Username attribute**: `username` (or leave blank to use the NameID).
   - **Email attribute**: `email`.
   - **Display-name attribute**: `displayname`.
   - **Groups attribute**: `groups`.
   - **Group → role mappings**: e.g. `meyes-admins → admin`,
     `meyes-operators → operator`. If a user is in several mapped groups, the
     **highest** role wins.
   - **Default role**: applied when no mapping matches (`viewer` is safe).
   - **Just-in-time provisioning**: leave on to create accounts automatically on
     first login; turn off to require pre-created accounts.
4. Tick **Enable SAML SSO on the login page** and **Save configuration**.

A **"Sign in with SSO"** button now appears on the M-Eyes login page.

---

## Roles

M-Eyes has three built-in roles (least → most privilege):

| Role | Can do |
|---|---|
| `viewer` | Read-only across all pages |
| `operator` | Everything a viewer can, plus change DDI data, run integrations & automation, deploy |
| `admin` | Everything, plus user management, integrations/automation config and SSO settings |

SSO users have their role **re-evaluated from group mappings on every login**, so
revoking a group in your directory revokes the privilege in M-Eyes automatically.
Local (non-SSO) admins are never downgraded by SSO mappings.

---

## Test it

1. Open M-Eyes in a private window → **Sign in with SSO**.
2. Authenticate at FortiAuthenticator.
3. You should return to M-Eyes signed in. Check **System → Users & Roles** — the
   user appears with `Source: saml` and the role from your group mapping.

Every step is logged under **Log & Report → Events** (`auth` category), including
rejections with the reason.

---

## Advanced settings

Reveal these with **Show advanced settings** on the SSO page.

| Setting | Default | Notes |
|---|---|---|
| **NameID format** | emailAddress | Must match what the IdP emits (email / persistent / transient / unspecified). |
| **Allowed clock skew (seconds)** | 120 | Tolerance for `NotBefore`/`NotOnOrAfter` to absorb clock drift between SP and IdP. |
| **Signature algorithm** | RSA-SHA256 | Used when M-Eyes signs AuthnRequests. Keep SHA-256; SHA-1 is legacy only. |
| **Require signed assertions** | on | Reject responses whose assertion isn't signed. Recommended. |
| **Require signed response** | off | Also require a signature over the whole `<Response>`. Enable if your IdP signs the response. |
| **Sign AuthnRequests** | off | Sign the request M-Eyes sends. Requires an **SP keypair** (below) and the SP cert uploaded to the IdP. |
| **Force re-authentication** | off | Sets `ForceAuthn`, forcing the IdP to re-prompt even with an active IdP session. |
| **SP private key / certificate** | — | PEM keypair used only when *Sign AuthnRequests* is on. The private key is write-only and never returned by the API. |

!!! note "Signed AuthnRequests"
    Most deployments don't need them — the security guarantee comes from verifying
    the **IdP's** signature on the assertion. Enable SP-side signing only if your
    IdP requires it; then upload the **SP certificate** to the FortiAuthenticator
    SP entry (step 2.5).

### Encrypted assertions

M-Eyes expects **signed but unencrypted** assertions (FortiAuthenticator's
default). If your IdP enforces assertion encryption, disable it for this SP.

---

## Other Identity Providers

The flow is identical; only the field names differ.

=== "Microsoft Entra ID"

    1. **Entra admin center → Enterprise applications → New application →
       Create your own → Integrate any other application (non-gallery)**.
    2. **Single sign-on → SAML**:
       - **Identifier (Entity ID)** = M-Eyes SP entity ID.
       - **Reply URL (ACS)** = M-Eyes ACS URL.
    3. **Attributes & Claims**: emit `email`, a display name, and a **groups**
       claim (Group Claims → Groups assigned to the application). Note the claim
       names and use them as the attribute mappings in M-Eyes.
    4. **SAML Signing Certificate** → download **Certificate (Base64)** → paste
       into M-Eyes' IdP certificate.
    5. Use the **Login URL** and **Microsoft Entra Identifier** as the M-Eyes
       *SSO URL* and *IdP entity ID*.

=== "Okta / Keycloak / ADFS"

    Create a SAML app/client with:

    - **SP Entity ID / Audience** = M-Eyes SP entity ID.
    - **ACS / Single Sign-On URL** = M-Eyes ACS URL.
    - A **groups** (or roles) attribute statement for role mapping.
    - Export the **IdP signing certificate** (PEM) into M-Eyes.

    Then fill the IdP entity ID, SSO URL and certificate on the M-Eyes SSO page.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `SAML signature verification failed` | Wrong/old IdP certificate in M-Eyes, or the IdP re-keyed. Re-export and paste the current PEM. |
| `Assertion has expired (NotOnOrAfter)` | Clock drift. Increase **allowed clock skew** or fix NTP on both ends. |
| `Assertion audience does not match this SP's entity ID` | The IdP's *Audience*/SP entity ID doesn't equal the M-Eyes SP entity ID. Copy it exactly from the SSO page. |
| `Could not determine a username` | The username attribute name is wrong, or the IdP doesn't emit a NameID. Set the **Username attribute** or fix the NameID. |
| User logs in but gets the wrong role | Check the **groups** attribute name and the group → role mappings; remember the highest matched role wins. |
| `No M-Eyes account … just-in-time provisioning is off` | Enable JIT provisioning, or pre-create the user in **Users & Roles**. |
| Button doesn't appear | SSO not enabled, or the IdP SSO URL is empty. |

All rejections are recorded under **Log & Report → Events** with the exact reason,
which is the fastest way to diagnose a failing exchange.

!!! warning "Always run M-Eyes behind HTTPS for SSO"
    SAML assertions and the session token travel over the browser. Terminate TLS
    in front of M-Eyes (see the HTTPS / TLS settings) before enabling SSO in
    production.
