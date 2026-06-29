# M-Eyes Changelog

All notable changes are generated automatically from conventional commits.

## [1.11.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.11.0...v1.11.1) (2026-06-29)


### Bug Fixes

* **frontend:** revalidate index.html so updates show immediately ([1c54a9d](https://github.com/FreddyMcFett/M-Eyes/commit/1c54a9df7662b8894e7f1ee3f1073d1edf89808c))

# [1.11.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.10.2...v1.11.0) (2026-06-29)


### Features

* **command-center:** deeper 3D framing for the console surface ([1b6dcea](https://github.com/FreddyMcFett/M-Eyes/commit/1b6dcea998461be1a71711005761085b5c1fe747))
* **deploy:** present DNS/DHCP as native auto-applied services ([bf91733](https://github.com/FreddyMcFett/M-Eyes/commit/bf91733d149c5442f9374496afa883a151fa065f))
* **events:** export the event log as a .log file ([33c1c26](https://github.com/FreddyMcFett/M-Eyes/commit/33c1c265a9507e645e2808135d6bb2061889c69b))
* **integrations:** categorized connector picker with vendor icons ([a1cab36](https://github.com/FreddyMcFett/M-Eyes/commit/a1cab36942794933978bc52709539a557ca89743))

## [1.10.2](https://github.com/FreddyMcFett/M-Eyes/compare/v1.10.1...v1.10.2) (2026-06-17)


### Bug Fixes

* **command-center:** calmer, cleaner Command Center surface ([4a60c70](https://github.com/FreddyMcFett/M-Eyes/commit/4a60c70302f80019eed16227d80a8b2ec919c7a0))

## [1.10.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.10.0...v1.10.1) (2026-06-17)


### Bug Fixes

* **ci:** build frontend image natively to avoid slow emulated arm64 build ([6d5481b](https://github.com/FreddyMcFett/M-Eyes/commit/6d5481b5735a1ec40379f82c625cc9e328967a41))

# [1.10.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.9.0...v1.10.0) (2026-06-17)


### Features

* **command-center:** exposure-map hero with greeting & metric strip ([cdf135c](https://github.com/FreddyMcFett/M-Eyes/commit/cdf135cde8c6acb91b8f6f93354633dcb6786af6))

# [1.9.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.8.1...v1.9.0) (2026-06-15)


### Features

* **command-center:** Cortex-style threat-defense SOC console ([709a635](https://github.com/FreddyMcFett/M-Eyes/commit/709a6358d0625028e918faa8d70df2fa9c90bf1c))

## [1.8.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.8.0...v1.8.1) (2026-06-15)


### Bug Fixes

* **update:** don't offer an update until its images are published ([d1af301](https://github.com/FreddyMcFett/M-Eyes/commit/d1af301798855b6a760762dc6522dc5eba3b8eaa))

# [1.8.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.7.0...v1.8.0) (2026-06-15)


### Features

* **dashboard:** add Command Center, system status & resource monitor ([98c6f33](https://github.com/FreddyMcFett/M-Eyes/commit/98c6f333fb9759382a4c62a89771450b69768575))

# [1.7.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.6.1...v1.7.0) (2026-06-15)


### Features

* **dns,dhcp:** advanced zone/scope config, resilient update check, generic engine names ([f28f93d](https://github.com/FreddyMcFett/M-Eyes/commit/f28f93d6bfc55619eb5ab546c6355e2218a5f03b))

## [1.6.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.6.0...v1.6.1) (2026-06-15)


### Bug Fixes

* **ci:** publish GHCR images on every release ([d918d9e](https://github.com/FreddyMcFett/M-Eyes/commit/d918d9e9d9d9f0fe616dd19db52220cb50943ee1))

# [1.6.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.5.0...v1.6.0) (2026-06-14)


### Features

* **updates:** one-click in-app update with clean service restart ([b504d91](https://github.com/FreddyMcFett/M-Eyes/commit/b504d91e7232439746b856e8019e413458f0ba2e))

# [1.5.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.4.1...v1.5.0) (2026-06-14)


### Features

* in-app docs, interactive dashboard, search-icon fix, no demo data by default ([acb4f19](https://github.com/FreddyMcFett/M-Eyes/commit/acb4f1963dd055394355f182457a5b972f9d67f3))

## [1.4.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.4.0...v1.4.1) (2026-06-13)


### Bug Fixes

* **certs:** resolve cryptography/datetime deprecations; clarify IPAM scan error ([35f7bff](https://github.com/FreddyMcFett/M-Eyes/commit/35f7bff3148f6efb66c64056d4dceb2219781971))

# [1.4.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.3.1...v1.4.0) (2026-06-13)


### Features

* enterprise SSO, asset management, Fortinet/Microsoft integrations, autonomy ([71102e4](https://github.com/FreddyMcFett/M-Eyes/commit/71102e4c75e9d151faa9eb2a4278d206d0aa1b86))

## [1.3.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.3.0...v1.3.1) (2026-06-12)


### Bug Fixes

* **security:** close zone-file/RPZ injection, runbook XSS, and harden deployment secrets ([40a3f97](https://github.com/FreddyMcFett/M-Eyes/commit/40a3f97d8ccfdf0516961d454db956a271c0d171))

# [1.3.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.2.1...v1.3.0) (2026-06-12)


### Features

* pull-based upgrades with persistent data + next-gen DDI features ([75020db](https://github.com/FreddyMcFett/M-Eyes/commit/75020db997102a7bb81b7217794fc8ea92f5a7f0))

## [1.2.1](https://github.com/FreddyMcFett/M-Eyes/compare/v1.2.0...v1.2.1) (2026-06-12)


### Bug Fixes

* **ci:** enable GitHub Pages from Docs workflow; add logo and architecture diagram ([b719df7](https://github.com/FreddyMcFett/M-Eyes/commit/b719df7c90eea1fcc76b5ca25488f2f3eb10753e))

# [1.2.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.1.0...v1.2.0) (2026-06-12)


### Features

* GUI system settings + HTTPS with in-UI certificate management ([68215ec](https://github.com/FreddyMcFett/M-Eyes/commit/68215ec1f90a9f341b25574eae8bf5715fc34014))

# [1.1.0](https://github.com/FreddyMcFett/M-Eyes/compare/v1.0.0...v1.1.0) (2026-06-12)


### Features

* add Infoblox-parity features (EAs, DNS views, DNSSEC, RPZ, leases, discovery, search) ([5db67ae](https://github.com/FreddyMcFett/M-Eyes/commit/5db67ae5bb53d0408e9bf20c8b16d4c507f6c33d))

# 1.0.0 (2026-06-12)


### Features

* initial M-Eyes DDI platform ([f18d3d4](https://github.com/FreddyMcFett/M-Eyes/commit/f18d3d4327c82d3d96ef7e039c4d85db24698d9c))
