# TLS Cutover — epe.sedamedical.com

**Date:** 2026-08-19  
**Origin:** `https://epe.sedamedical.com`  
**Result:** TLS/static cutover completed; acceptance tests passed

The React portal and n8n webhook path now share one HTTPS origin on
`92.51.45.147`. The Azure frontend remains untouched as a fallback.

All n8n workflows are inactive after testing.

## Access reconnaissance

### Azure fallback — 135.232.120.40

Observed:

- TCP 80: open
- TCP 3389: open
- TCP 22: filtered/timeout
- TCP 443: filtered/timeout
- portal on port 8080: HTTP 200

No host entry exists in:

- `~/.ssh/config`
- OpenSSH known_hosts
- JetBrains SSH configs
- Azure CLI or gcloud sessions

Local private keys exist, but none is associated with this host by filename,
comment, config, or known_hosts. Keychain contains Microsoft Azure account
provider cache metadata, not an SSH credential.

**Non-interactive access: no.** Manual RDP remains the fallback. The VM and
`portal.sedamedical.com` were not changed.

### Old assessment host — 216.250.12.243

Observed:

- TCP 22: connection refused
- TCP 80/443: open
- `https://bk.sedamedical.com/auth`: live Seda Medical login page
- certificate: Let's Encrypt, valid through 2026-10-19

No local SSH config, known_hosts entry, or Keychain credential exists for the
IP or `bk.sedamedical.com`. The local `vpsb_backup_reader` key is configured
for another address, `216.250.12.72`.

**Non-interactive admin/backup access: no.** The host was not changed and
cannot be used for off-host backups until a new access method is issued.

## DNS evidence

System resolver, Cloudflare (`1.1.1.1`), and Google (`8.8.8.8`) agreed:

```text
epe.sedamedical.com    92.51.45.147
portal.sedamedical.com 135.232.120.40
bk.sedamedical.com     216.250.12.243
```

DNS was verified before the single production ACME attempt.

## Reverse proxy

Caddy runs in its own Compose project:

```text
project=epe-proxy
image=caddy@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d
restart=unless-stopped
```

Files:

- `infra/Caddyfile`
- `infra/caddy-compose.yml`
- remote copy: `/opt/epe-proxy`

Routing:

- `/webhook` and `/webhook/*` → n8n at host port 5678
- all other paths → React static release
- unknown SPA paths → `index.html`

Headers include HSTS, nosniff, referrer policy, and restrictive browser
permissions. Frame embedding and plugin objects are blocked by
`X-Frame-Options` and a focused Content Security Policy.

## Certificate and renewal

One ACME attempt was made. Caddy logged:

```text
authorization finalized: valid
certificate obtained successfully
issuer: Let's Encrypt production
```

Certificate:

```text
subject=CN=epe.sedamedical.com
SAN=DNS:epe.sedamedical.com
notBefore=2026-08-19 04:31:10 UTC
notAfter=2026-11-17 04:31:09 UTC
serial=064EBB537797E41E5E2518F5254AEEE8C291
```

Renewal automation verification:

1. certificate, key, and Caddy metadata exist in named persistent volume
   `epe_proxy_caddy_data`;
2. Caddy logged `started background certificate maintenance`;
3. the Caddy container was restarted;
4. the certificate serial remained identical and HTTPS returned;
5. Caddy logged its next storage-maintenance run;
6. container restart policy is `unless-stopped`.

A production renewal was not forced because that would make an unnecessary
ACME request immediately after issuance.

## Frontend build and deployment

`src/config/api.js` reads `VITE_API_URL` and now falls back safely to
same-origin `/webhook`. The former shipped bundle contained the legacy IP
because its old fallback was used at build time.

Production build:

```text
VITE_API_URL=/webhook npm run build
```

Bundle verification:

```text
/webhook present=true
92.51.45.147:5678 absent=true
/reset-password route present=true
```

Static root:

```text
/var/www/epe/current
```

Deploy command:

```bash
./scripts/deploy_epe_frontend.sh
```

The script installs locked dependencies, builds with the relative API base,
rejects a bundle containing the legacy URL, streams a timestamped release to
the VPS, validates the release before switching a relative symlink, and
restores the previous target if the swap fails. It was run repeatedly; every
completed deployment returned portal HTTP 200.

The absolute-symlink bug found on the first release was corrected. Relative
links work both on the host and inside the Caddy bind mount.

## n8n public URL and reset origin

n8n was recreated with:

```text
WEBHOOK_URL=https://epe.sedamedical.com/
VUE_APP_URL_BASE_API=https://epe.sedamedical.com/
EPE_FRONTEND_URL=https://epe.sedamedical.com
```

All unrelated operator-set environment values, the image ID, encryption key,
JWT signing secret, and restart policy were preserved.

Password-reset proof:

- real email delivered;
- generated URL scheme: HTTPS;
- host: `epe.sedamedical.com`;
- path: `/reset-password`;
- page returned HTTP 200 with a valid certificate;
- raw token was absent from the API response;
- n8n attribution footer was disabled and its removal confirmed.

Unused test reset tokens were deleted.

## Firewall

Persistent policy: `infra/epe-firewall.sh` and
`/usr/local/sbin/epe-firewall.sh`.

Changes:

- public TCP 80: allowed
- public TCP/UDP 443: allowed
- direct public TCP 5678: dropped in both Docker FORWARD and host INPUT paths
- SSH 22: unchanged
- existing database/Portainer restrictions: unchanged

External evidence from the workstation:

```text
80=open
443=open
5678=timeout_or_filtered
```

n8n remains healthy on host loopback and through the SSH tunnel. HTTPS
`/webhook/*` reaches n8n; an inactive route returns n8n's own unregistered
webhook response through Caddy.

## HTTPS authentication acceptance

The no-activation constraint conflicted with HTTP end-to-end testing.
Alexander explicitly approved temporary activation of only:

- `API: Auth Login (No Params)`
- `API: Get Employees (Smart Role Based)`

They were activated for the test window and immediately deactivated.

Evidence:

```text
registered test webhooks=2
HTTPS login status=200
HTTPS login success=true
guarded route valid token status=200
actor id=2
conflicting requested id=21
returned direct subordinates=11
forged token status=401
forged token error=TOKEN_INVALID
```

The test session was revoked. Final state:

```text
active workflows=0
registered webhooks=0
active auth sessions=0
```

## Backups and source preservation

Pre-cutover:

```text
epe_2026_before_tls.dump
SHA-256 c44c751f0fe47b89f90b018ffbe506f576a6fb29af7d2710715d7f45a96a9653

n8n_public_before_tls.dump
SHA-256 c5f804d5a9dffea3a9d4f8aa39a0eebfcf3c2234b9cb051723cf731581067179
```

Final restore-tested:

```text
epe_2026_after_tls.dump
SHA-256 40f88b1e10fa2d1ad964b127609d88745fd847a1bbf0fffb9d61070b9e9d6870

n8n_public_after_tls.dump
SHA-256 f550177eaf197b22ab9b5174d21d6669d7a4c03db2d812a75f5f2668e7ea824a
```

2025 source fingerprint:

```text
before=21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
after =21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
unchanged=true
```

No scoring table, formula, evaluation, or 2025 row was changed.

## Final acceptance

```text
HTTPS portal=200
HTTP redirect=308 to HTTPS
SPA reset route=200
certificate valid=true
HTTPS login proven=true
valid guarded request accepted=true
forged guarded request rejected=true
direct 5678 blocked=true
reset HTTPS email delivered=true
Caddy renewal maintenance active=true
Azure fallback 8080=200
```

## Remaining facts and blockers

- All workflows are inactive by design. Login and the guarded route were
  proven over HTTPS but are not currently available after the test window.
- Only one route has the reusable guard; remaining routes are the next pass.
- The production dependency audit still reports 15 advisories, including 11
  high severity.
- Azure RDP remains public because the fallback VM was explicitly left
  untouched.
- The old `.243` assessment host is reachable only as a web application; no
  backup credential exists.
