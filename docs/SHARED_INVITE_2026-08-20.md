# Shared invite token — 2026-08-20

**Date of work:** 2026-08-19  
Alexander's decision: the 26 Aug company-wide link (invite **id=4**) must stay reusable. Hypothesis from `docs/THROTTLE_RAISE_2026-08-20.md` that `/api/register` sets `invite_tokens.is_used=true` on first success is **true** on live n8n.

`docs/HANDOVER.md` was replaced with the 2026-08-20 text first. §3 claim “all 89 users have `password_hash = NULL`” is **false** on live `epe_2026` (Alexander, id=2, is registered). Not changed here.

---

## Verdict

The shared token is reusable. Two employees registered one after another through invite **id=4**; after both, `is_used` remained **false**. A third attempt with an already-registered email was rejected. Test hashes rolled back; **registered = 1** (Alexander).

A second live defect blocked the same link even before `is_used`: Create Invite stores **base64url** tokens (id=4 is 43 characters); register only accepted `[a-f0-9-]{16,128}` (UUID). First register calls returned 400 without writing a password. Same workflow, validator widened to `[A-Za-z0-9_-]{16,128}` so UUID **and** the live shared token both pass. No schema change.

H1 remains period id=2, `draft` / `is_active=false`. 25 workflows active at start and end. Throttles and scoring untouched. 2025 fingerprint unchanged.

---

## 1. Verified before-state (live)

`API: Register` `wkDxU72Kg8fOiZCB` version `84253e12…`, active, updated 2026-08-19T08:40:21Z.

| Check | Live behaviour |
|---|---|
| `Load Registration Context` | `JOIN invite_tokens` required `COALESCE(is_used,false)=false` and `expires_at > now()` |
| `Hash Password` persist SQL | `UPDATE invite_tokens SET is_used=true, used_by, used_at` with `is_used=false`; success required `invite_used` |
| `Validate Registration` | token regex `[a-f0-9-]{16,128}` |
| Invite id=4 | unused, unexpired, length 43, **does not** match that regex (`urlsafe=true`) |
| Invite id=1 | used, expired, length 36, matches UUID regex (Alexander registered with this one) |
| `send-verification-code` / `verify-invite` | do **not** consult `is_used`; only existence + expiry |
| Activation | 25 active, 28 webhooks |

`verify-code`: 5 attempts per code row. `reset-password`: single-use `used_at` per reset token, 5 min send cooldown per email. Not changed.

---

## 2. What changed

Only `API: Register` (plus generator `scripts/build_auth_workflows.py` and `auth_core/register.json` so a later regen does not restore the burn).

1. Dropped `AND COALESCE(invites.is_used, false) = false` from the load JOIN. Expiry check stays.
2. Replaced the `UPDATE … SET is_used=true` CTE with `SELECT id FROM invite_tokens WHERE id=… AND expires_at > now()`. Persist still requires an unexpired token; it does not write the invite row. `Format Registration Response` still keys on `invite_used`.
3. Token validator: `[A-Za-z0-9_-]{16,128}` (base64url charset; UUID hex+hyphens still match).

Live version after both PUTs: `e20b75b4-a050-4050-9fa0-02cac067ccd3`, updated 2026-08-19T13:56:52.642Z, **active=true**. Active name set unchanged (25).

No other route. No throttle edit. No scoring. No schema.

---

## 3. Proofs

Public origin `https://epe.sedamedical.com`. Shared token id=4 never printed. Verification codes were sent by the live `send-verification-code` path (Gmail) to the two test mailboxes, then read from the DB to complete verify/register. Codes expire in 10 minutes and were consumed or deleted.

### Gates (reusable token in every call)

| Case | Result |
|---|---|
| `GET verify-invite` unknown token | 200 `valid=false` “Token is invalid or expired” |
| `GET verify-invite` expired token id=1 | 200 `valid=false` same message |
| `GET verify-invite` id=4 | 200 `valid=true` `token_id=4` |
| `POST send-verification-code` `not.in.org@sedamedical.com` | 200 `error_code=email_not_found` |
| `POST send-verification-code` `alexander@sedamedical.com` | 200 `error_code=already_registered` |
| `POST verify-code` wrong digits (Alina) | 200 `verified=false` “4 attempts remaining” |
| `POST verify-code` expired row (SQL-inserted past `expires_at`, Anastasiya, no mail) | 500 workflow error “No valid verification code found…” (pre-existing `throw`; still a rejection) |

### Sequential registration on the same link

| Step | Result |
|---|---|
| Alina Naubatova id=3 register | 200 success `user_id=3`. Invite id=4 still `is_used=false`, `used_by` null. Registered count 2. |
| Alp-Arslan Mametnazar id=4 register, **same token** | 200 success `user_id=4`. Invite still unused. Registered count 3. |
| Send code again to Alina | 200 `already_registered` |
| Register again Alina + dummy code | 400 “Registration link or verification code is invalid” |
| Register Anastasiya id=6 + Alina’s consumed code | 400; Anastasiya `password_hash` still NULL |

First register attempt **before** the regex change: both users verified email successfully, then register 400, **zero** password writes. After the charset fix, the same verified codes completed.

---

## 4. Rollback / end state

```text
UPDATE users SET password_hash=NULL WHERE id IN (3,4)  → 2 rows
auth_sessions for 3,4 → 0 rows existed
email_verification_codes → 0 (consumed on success)
epe-throttle:% rows deleted (verify-invite probes) → 1
registered=1  alexander@sedamedical.com
users=89  evaluations=0  sessions=0  codes=0
invite id=4 unused, unexpired
H1 id=2 draft / is_active=false
active workflows=25  webhooks=28
```

Two confirmation emails did go to Alina and Alp-Arslan. The codes are spent/deleted; their passwords are NULL again. They will register for real on 26 Aug like everyone else.

**Superseded (20 Aug):** Alexander forbade further executor mail to anyone except `alexander@sedamedical.com` unless he names the recipient. D-0820-8 / `AGENTS.md` hard constraint 5. Do not repeat this proof pattern.

---

## 5. Integrity

Dumps in `backups/2026-08-19-shared-invite/` (gitignored). Restore into throwaway DBs succeeded.

```text
epe_2026 before  7d1ed206f9591e696096b4b141e29a671414d3b43639e80c3198155407f5fa02
epe_2026 after   bc13a5350b2448846354671ed6750ae28dd5c08b910fe5c714a8ec5514189dcc
n8n public before d125fd555661449762f23edc0f0eb248284b6255d38b50f3095c4e6b8fbe14d2
n8n public after  b0e9719d56a8ec618af5b45736ae0fe05324c9a0975e7dabf42966f28df06b22
2025 fingerprint  21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
                  (before and after; unchanged=true)
```

n8n public SHA changed because `API: Register` was updated. `epe_2026` custom-format SHA differs (dump timestamps; both 73275 bytes). After rollback, registered=1 as before.

`node --test tests/authWorkflows.test.js tests/preAuthLimits.test.js`: 11 pass (9 auth including reusable-invite + 2 pre-auth).

---

## Surface for decision — do not resolve silently

**Reusable token does not let a registered person write another account.** Register joins **request email = user row = verified unused code** and `password_hash IS NULL`. Alina’s consumed code + Anastasiya’s email → 400, Anastasiya still NULL. The shared token does not name a user. The remaining theft path is reading someone else’s mailbox — same as before.

**Other single-use assumptions (not changed):**

- **Password reset** tokens are still one-shot (`used_at IS NULL` then set). Each person gets their own; a same-morning **registration** burst does not share them. Reset **send** cooldown is 5 minutes **per email** — 89 different people can request resets in parallel.
- **Verification codes** are per email, 10 min, deleted on successful register, 60 s resend cooldown per email. 89 first sends in one minute all pass. A second send by the same person inside 60 s is blocked (intended).
- **`API: Create Invite`** still selects `is_used=false` and returns the existing live token (BUG-008). Because register no longer sets `is_used`, that control will keep returning **id=4** until 2026-09-18 expiry. Rotating the public link requires expiring or marking that row — there is no other H1 switch. Not changed.
- **`verify-code`** on missing/expired code still **throws** (HTTP 500 “Error in workflow”) instead of a structured 4xx. Pre-existing; ugly, not a burst killer.

No further register change recommended before 26 Aug.
