# Mail and runbook — 2026-08-19

Brief: `docs/briefs/MAIL_AND_RUNBOOK_2026-08-20.md`  
H1 remains period id=2, `draft` / `is_active=false`. No workflow was modified.

Architect statements about the code were treated as hypotheses. Where live code disagreed, the code won; disagreements are listed below.

---

## Verdict

SMTP is Google, SPF already covers it, and `verify-invite` already keys on the real client IP behind Caddy. No throttle change and no dump. The launch runbook is `docs/LAUNCH_RUNBOOK_H1.md`.

**DKIM is still unpublished** (`google._domainkey.sedamedical.com` has no TXT). Both test messages were accepted by `smtp.gmail.com:465`. Inbox vs spam and the Authentication-Results lines are **unverified in this session**: the Cursor browser hit a Google login wall, and this Mac has no IMAP password for either mailbox. Alexander must open the two messages (markers below) and say inbox or spam plus `spf=` / `dkim=` / `dmarc=`.

**26 Aug recommendation without those headers:** **go**, with the existing “check Spam” line in the invitation. Waiting for DKIM slips the waves; missing DKIM makes Spam more likely, which the wave text already covers. Upgrade to no-go only if both messages are missing (not even Spam). Publish DKIM today anyway.

---

## End state (verified after cleanup)

| Check | Value |
|---|---|
| Users | 89 |
| Evaluations | 0 |
| Active sessions | 0 |
| All sessions | 0 |
| Registered (`password_hash IS NOT NULL`) | 1 — `alexander@sedamedical.com` |
| H1 id=2 | `draft,false` |
| Email verification codes | 0 |
| Throttle rows | 0 |
| Live workflows | 60 total, **25 active** |
| Unused invite | `invite_tokens.id=4` kept (not used, not printed) |

One historical `password_reset_tokens` row remains (`id=4`, user Alexander, **used**, expired 2026-08-18). It was not created this session and is not a live login.

No dump and no 2025 fingerprint this pass: no workflow and no 2025 data were touched.

---

## 1. System mail

### SMTP credential `SMTP account` (`Owjl0MaDCmpyOksi`)

Decrypted on the host with the live `N8N_ENCRYPTION_KEY`. Secrets are not in this file.

| Field | Value |
|---|---|
| Host | `smtp.gmail.com` |
| Port | not stored on the credential; n8n SMTP default is **465** / SSL. Login on 465 succeeded. |
| Auth user domain | `sedamedical.com` |
| Stored keys | `host`, `user`, `password` (no `port`, no `secure`) |

From-address in the live nodes remains `noreply@sedamedical.com`.

### SPF / DKIM / DMARC at test time

| Record | Observed 2026-08-19 |
|---|---|
| SPF | `v=spf1 include:_spf.google.com ~all` |
| SPF coverage | **covers this host.** Mail is submitted to Google, so the IPs that hit the recipient MX are Google’s, inside `_spf.google.com`. No SPF change. Do not switch `~all` → `-all` until DKIM is live. |
| MX | Google Workspace |
| DMARC | `v=DMARC1; p=none; rua=mailto:eziz@sedamedical.com` |
| DKIM | **absent.** Checked: `default`, `google`, `k1`, `selector1`, `selector2`, `mail`, `s1`, `s2`, `dkim`, `google2024`, `google2025` on `_domainkey.sedamedical.com`. Rechecked after send: still empty. |

TXT Alexander must publish / check: **`google._domainkey.sedamedical.com`** (Google Workspace Admin → Gmail → Authenticate email). Until it exists, receiving Gmail often has no aligned DKIM; expected effect is more Spam, especially at the external mailbox.

### What was sent

Architect placeholders `[COMPANY_MAILBOX]` / `[EXTERNAL_MAILBOX]` were empty. Fallback used the only two mail identities on this workstation:

| Role | Address | Marker | Path |
|---|---|---|---|
| Company | `alexander@sedamedical.com` | `EPE-MAIL-20260819-A` | same credential, `smtp.gmail.com:465`, From `noreply@sedamedical.com` |
| External | `a.petrosov@gmail.com` | `EPE-MAIL-20260819-B` | same |

Live `POST /api/send-verification-code` and `POST /api/request-password-reset` both require `@sedamedical.com` and refuse an already-registered user. They cannot deliver to the external mailbox or to Alexander’s registered company address. A one-shot send through the same `SMTP account` was the clean path. No n8n workflow was created or edited.

Both `sendmail` calls returned without error (`smtp_login ok`, `ALL_SENT 2`).

### Received-header verdicts

| Mailbox | Placement | SPF | DKIM | DMARC |
|---|---|---|---|---|
| `alexander@sedamedical.com` | **unverified** — open message `EPE-MAIL-20260819-A` | unverified | unverified (public DKIM absent; expect fail / missing) | unverified |
| `a.petrosov@gmail.com` | **unverified** — open message `EPE-MAIL-20260819-B` | unverified | unverified (same) | unverified |

How to read them: Gmail → the message → ⋮ → Show original → `Authentication-Results`. Need `spf=`, `dkim=`, `dmarc=` and whether the message sat in Inbox or Spam.

---

## 2. Throttle

Hypothesis was: behind Caddy the IP is the proxy, so the 30 / 5 min limit is global.

**Code already disagrees.** `API: Verify Invite` → node `Extract Token` reads `x-forwarded-for` / `x-real-ip`, first hop, then keys `epe-throttle:verify-invite:<ip>`. No other per-IP pre-auth limit exists (the verification-code limit is per email, 60 s).

Live Caddyfile matches the repo: `reverse_proxy host.docker.internal:5678`. Port **5678 is DROP** on `EPE-DOCKER-USER` from `eth0` (759 drops counted); from this Mac `connect` to `:5678` did not succeed. Caddy is the only public path. That is why the forwarding header is safe to trust: a client on the internet cannot hit n8n except through Caddy, and Caddy as the edge **does not honour a client-supplied `X-Forwarded-For`**.

### Proof — two real client IPs, two counters

Invalid token `epe-mail-runbook-probe-*` (not the live invite).

| Call | Source | Bucket written | Count |
|---|---|---|---|
| A | Mac via `https://epe.sedamedical.com` | `epe-throttle:verify-invite:216.147.123.249` | 2 |
| B | same Mac + spoofed `X-Forwarded-For: 203.0.113.77` | **same** `216.147.123.249` (no `203.0.113.77` row) | (included in the 2) |
| C | VPS hairpin to the public origin | `epe-throttle:verify-invite:92.51.45.147` | 1 |

Independent counters. The 31st request from one IP still cannot starve the other. No workflow change. Probe rows deleted.

Reasoning kept on the record even though no edit was required: 5678 is closed to the internet; Caddy is the sole path; Caddy overwrites `X-Forwarded-For` with the connecting client.

---

## 3. Runbook

`docs/LAUNCH_RUNBOOK_H1.md` — one page, Russian, for Alexander.

UI facts used there, verified:

- Click path is **Администрирование → Периоды → «Активировать»** on **H1-2026**, then the confirm dialog. There is no separate “Deactivate” control; an active row shows only «Текущий период».
- `in_scope_count` / `participant_count` render as `87 / 89` (live participants: 87 in scope, 89 total).
- Empty campaign copy on the dashboard: «Кампания ещё не открыта».
- Manager task chip appears only when the campaign is active and in-scope subordinates exist.
- Registration badge: **Администрирование → Сотрудники**, «Зарегистрирован» / «Не зарегистрирован».
- Coefficient write freezes when any period is `is_active` or `status='active'`. Classification write freezes after the first evaluation in the active period (`CLASSIFICATION_FROZEN`, 409).
- Period switch after any evaluation in the current active period is 409 (`ACTIVE_PERIOD_HAS_EVALUATIONS`).
- **Annual 2025** is `closed`; activate SQL skips `status = 'closed'`. After H1 is on, the UI cannot turn it off. Emergency stop is this chat (SQL back to `draft,false`), not a button.

---

## Disagreements vs architect hypotheses

- `verify-invite` behind Caddy sees the **real client IP**, not the proxy. The limit is not global. No header patch and no removal.
- `[COMPANY_MAILBOX]` / `[EXTERNAL_MAILBOX]` were not named. Used `alexander@sedamedical.com` and `a.petrosov@gmail.com` (only two mail identities on this Mac).
- Neither the verification-code path nor the reset path can send to an external mailbox (both require `@sedamedical.com`). Reset also refuses Alexander (`already_registered` / no-send). Inbox proof used the same SMTP credential directly.
- “Deactivate the period” is not a click. There is no such button; the only other period is closed.
- HANDOVER §2 still says all workflows inactive; live state after launch-prep is **25 active**. Not re-litigated; noted.

---

## Surface for decision

1. **SPF.** Host is Google. **No SPF change.** Leave `v=spf1 include:_spf.google.com ~all` until DKIM is live; then consider `-all`.
2. **DKIM / 26 Aug.** Record to publish: `google._domainkey.sedamedical.com`. Recommendation **go** on 26 Aug with the Spam warning already in the invite. Confirm the two test messages (markers `EPE-MAIL-20260819-A` / `B`) so the header table can be closed. No-go only if the messages never arrive.
3. **Second admin.** There is none. Only `alexander@sedamedical.com` has `role=admin`. The runbook cannot name a deputy. Decide who it is before 31 Aug; without that, a locked or sick admin account stops the launch.
4. **Emergency stop.** Accept “write in this chat” as the stop button, or ask for a real Deactivate control (out of this brief; would be a new write path).

---

## Files

- `docs/briefs/MAIL_AND_RUNBOOK_2026-08-20.md`
- `docs/LAUNCH_RUNBOOK_H1.md`
- `docs/MAIL_AND_RUNBOOK_2026-08-19.md`
- `docs/HANDOVER.md` §7
