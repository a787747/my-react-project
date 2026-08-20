# Throttle raise — 2026-08-20

**Date of work:** 2026-08-19  
**Brief outcome:** raise `GET /api/verify-invite` per-IP limit to at least 600 / 5 min, or report if already done.  
`HANDOVER.md` has no §6.1 (section 6 is open items). Read instead: §3 (then 30 / 5 min / IP) and `docs/MAIL_AND_RUNBOOK_2026-08-19.md` §2 (IP already real; **no** raise).

Hypothesis that a previous session already raised the limit to 600 (or removed it) is **false**. Live n8n still had `throttleCount > 30`. This session raised it to **600 / 5 min / IP**.

---

## Verdict

`verify-invite` was 30 requests / 5 minutes / client IP. It is now **600 / 5 minutes / client IP**. A 40-request burst from one IP (the old limit + 10) all passed the throttle layer. The 60-second per-email resend cooldown on `send-verification-code` was not changed.

H1 remains period id=2, `draft` / `is_active=false`. 25 workflows active at start and end. 2025 fingerprint unchanged.

---

## 1. Verified before-state (live n8n, not the repo)

Read from `public.workflow_entity` on the running instance, then confirmed via n8n API GET `VVqO0KkCr28emLsq`.

Activation at start: **25 active**, 13 inactive unarchived, 22 archived, **28** registered webhooks. The four registration-path workflows were all **active**.

| Route | Workflow | Limit | Window | Key | Client IP |
|---|---|---|---|---|---|
| `GET /api/verify-invite` | `API: Verify Invite` `VVqO0KkCr28emLsq` version `88a8d9d4…`, updated 2026-08-19T11:52:28Z | **30** requests (`throttleCount > 30` → `RATE_LIMITED`) | 5 minutes (`interval '5 minutes'`) | per-IP, `auth_login_attempts.email` = `epe-throttle:verify-invite:<ip>` | `Extract Token`: first hop of `x-forwarded-for` / `x-real-ip` / `X-Forwarded-For`; else `unknown` |
| `POST /api/send-verification-code` | `API: Send Verification Code` `imGl6C6SUPAexvBE` | **1 send / 60 s** (`elapsed < 60 * 1000` → `error_code=resend_cooldown`) | 60 seconds | **per-email** (`email_verification_codes.created_at` max for that email) | not used |
| `POST /api/verify-code` | `API: Verify Code` `OMmlbaAAPmRHcCLS` | **5 wrong guesses** per outstanding code (`attempts >= 5`) | lifetime of that code (10 minutes from send) | **per-email / per-code row** | not used |
| `POST /api/register` | `API: Register` `wkDxU72Kg8fOiZCB` | **no request throttle** | — | — | not used |

Repo export `n8n_workflows/API_ Verify Invite.json` still had `throttleCount > 30` (stale vs live `updatedAt`, same limit). `tests/preAuthLimits.test.js` asserted 30.

`epe_2026` before change: users 89, registered 1, evaluations 0, sessions 0, throttle rows 0, invite id=4 unused and unexpired, H1 draft/inactive.

---

## 2. What changed

Only `API: Verify Invite` node `Format Response`: `throttleCount > 30` → `throttleCount > 600`. Window, key, IP extraction, SQL, connections, and activation were not touched.

| | Before | After |
|---|---|---|
| Live versionId | `88a8d9d4-22e0-4acc-b828-9ccba15adfc3` | `b1c87ec3-3190-4e73-b289-5c874063317b` |
| Live updatedAt | 2026-08-19T11:52:28.249Z | 2026-08-19T13:46:13.004Z |
| Threshold | 30 | 600 |
| Active | true | true (PUT left it active; no deactivate) |
| Active workflow set | 25 names | same 25 names |

Repo: `n8n_workflows/API_ Verify Invite.json` re-exported from live GET. `tests/preAuthLimits.test.js` now asserts `throttleCount > 600`. `node --test tests/preAuthLimits.test.js`: 2/2 pass.

No other route or scoring path was written.

---

## 3. Burst proof

Dummy token `epe-throttle-raise-probe-20260819` (not the live invite). Public origin `https://epe.sedamedical.com/webhook/api/verify-invite`. 40 sequential GETs from this Mac.

```text
n=40
elapsed_s=16.14
http={200: 40}
error_code RATE_LIMITED count=0
every body: success=true, valid=false, "Token is invalid or expired"
auth_login_attempts: epe-throttle:verify-invite:216.147.123.249  failed_count=40
```

40 > the old 30. None were throttled. Counter keyed on the real client IP behind Caddy (`216.147.123.249`), same extraction as `docs/MAIL_AND_RUNBOOK_2026-08-19.md` §2. Artifact: `backups/2026-08-19-throttle-raise/burst_proof.json` (gitignored).

---

## 4. End-state cleanup

```text
DELETE 1  from auth_login_attempts WHERE email LIKE 'epe-throttle:%'
throttle_rows=0
sessions=0
email_verification_codes=0
users=89  registered=1
evaluations=0
invite id=4 unused, not expired
H1 id=2 draft / is_active=false
active workflows=25
webhooks=28
live Format Response still has throttleCount > 600, not > 30
```

Throwaway restore DBs used for dump checks were dropped.

---

## 5. Integrity

Dumps in `backups/2026-08-19-throttle-raise/` (gitignored). Custom-format `pg_dump`; restore into throwaway DBs succeeded (`epe_2026` users=89; n8n `workflow_entity`=60). 2025 fingerprint method matches `docs/IMPORT_2026-08-18.md`.

```text
epe_2026 before SHA-256  cdd8dce86b03b03264017fc92aad336532194498811ea4dde0ef821026f07e56
epe_2026 after  SHA-256  8fe3a8938b3c57c7348db4e933fcfc437ea7c70e809381d5f4e8b7b80a9134d0
n8n public before        a403cccb2e15733db8ea534a66f98f017e53c5bd4feb0c8e629d9a87b28dd646
n8n public after         4543fb0f223c1ac8736aaef3671ef67bd3c7d9b5036cdf830e10755dbee64a25
2025 fingerprint before  21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
2025 fingerprint after   21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
unchanged=true
```

n8n public SHA changed because `API: Verify Invite` was updated. `epe_2026` custom-format SHA also changed (dump header timestamps; both files 73275 bytes). After cleanup there were no remaining probe rows.

---

## Surface for decision — do not resolve silently

**`POST /api/register` will stop the company-wide burst after the first success.** It has no per-IP throttle, but live SQL requires `invite_tokens.is_used = false` and then sets `is_used = true` on the first completed registration (`API: Register` → `Hash Password` / `Load Registration Context`). Invite **id=4** is the unused shared token. Person 1 registers → token burned → persons 2–88 get “Registration link or verification code is invalid”. That contradicts D-0820-4 (“reusable invite token”) and is worse than the old 30 / 5 min cap. **Not changed in this brief.**

The other registration-path limits would **not** choke 89 different people on one NAT:

- `send-verification-code`: 60 s **per email**. 89 first sends in the same minute all pass. Leave as specified.
- `verify-code`: 5 attempts **per code/email**, not per IP.

Unverified outside n8n: Gmail may have its own send cap if 89 verification mails go out in one minute. Not measured here.
