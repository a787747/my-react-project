# Launch prep — 2026-08-19

Brief: `docs/briefs/LAUNCH_PREP_2026-08-20.md`  
H1 remains period id=2, draft/inactive. Campaign start: 31 Aug. Invitations: 26 Aug.

Architect statements about the code were treated as hypotheses. Where live code disagreed, the code won; disagreements are listed below.

---

## Verdict

The system is ready for invitation waves and for H1 activation on 31 August, with two operational actions still on Alexander: publish DKIM for `noreply@sedamedical.com`, and name one company plus one external mailbox for an inbox/spam test. Nothing in this pass changed a scoring formula, `EPE: Auth Guard`, or a deferred route.

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
| Launchprep / throwaway users | 0 |
| Email verification codes | 0 |
| Throttle rows | 0 |
| Live workflows | 60 total, **25 active** |
| `EPE: Auth Guard` | inactive (sub-workflow, unchanged) |
| Frontend | `20260819T120100Z` at `/var/www/epe/current` |
| Unused invite | `invite_tokens.id=4`, unused, expires 2026-09-18 (kept on purpose) |

2025 fingerprint before and after: `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e`.

---

## Dumps

| File | SHA-256 |
|---|---|
| `epe_2026_before_launch_prep.dump` | `a088c7b3833ceee20a682edd9821ee43bce60e74a9a7ce6e8e1129a40a8b5f49` |
| `n8n_public_before_launch_prep.dump` | `dd89f72db87020e31f987d75fa98ba9eda8560b731c53ce8f4bda60ef9e8fe6a` |
| `epe_2026_after_launch_prep.dump` | `46cefc67951c16bdca596462cff3509536bc0baba3da0957c8ab2bd4ae00789a` |
| `n8n_public_after_launch_prep.dump` | `b496aaa935f3997e9506c8dde8ce882b822142ce3b802c9b756fd037503e9796` |

After-dump restore into throwaway databases: `users=89`, `evals=0`, `h1=draft,false`, `workflows=60`, `active=25`. Throwaways dropped. Host copies: `/root/backups/epe/2026-08-19-launchprep/`.

---

## 1. BUG-007 closed

**What changed.** `GET /api/employees` joins the single period that is both `is_active` and `status='active'` and `evaluation_period_participants.is_in_scope`. HR status denominators use the same set. `TaskStatusContext` treats an empty/inactive campaign as “no pending subordinate task”. Admin user management and the organisation tree outside campaign views are untouched.

**No active period (current live state, and rehearsal before activate):** employees `campaign_active=false`, count `0`; HR `total=0`, `in_scope_count=0`. Frontend copy: «Кампания ещё не открыта».

**With H1 temporarily active (rehearsal):**

| Proof | Result |
|---|---|
| Akmyrat Jumahanov (id=1) campaign list | 5 names: Alina, Asadbek, Halykberdi, Muhammet Gylyjov, Shasenem. **Esenova absent** |
| Alyona Dzhafarova (id=5) campaign list | 1 name: Muhammet-Ali Chariyev. **Balova absent** |
| Periods GET | `in_scope_count=87`, `participant_count=89` (visible in Admin → Periods, column «В охвате») |
| HR status | `in_scope_count=87`, `total=84` (87 minus admin + 2 HR), Esenova and Balova absent; Akmyrat `total_subordinates=5` |

Recommendation (implemented, not a silent product change beyond the brief): **empty campaign lists when no period is active**, not a fallback to the org tree. Falling back would re-open BUG-007 the moment H1 is draft again.

---

## 2. Pre-auth limits

| Route | Limit | Proof |
|---|---|---|
| `POST /api/send-verification-code` | 60 s per email | First call 200; second call inside the window `success=false`, `error_code=resend_cooldown`, `retry_after_seconds=60`. First live pair failed because `Date.parse` on the n8n timestamp was `NaN`; cooldown now uses `FLOOR(EXTRACT(EPOCH FROM MAX(created_at))*1000)`. |
| `GET /api/verify-invite` | 30 requests / 5 minutes / IP | 30th call valid; 31st `error_code=RATE_LIMITED`. Counter is `auth_login_attempts` key `epe-throttle:verify-invite:<ip>`. Rows deleted after rehearsal. |

No other pre-auth behaviour changed. Register now shows the cooldown message.

These values will not block a legitimate employee: they wait one minute for a second code. A large office NAT that opens the same invite more than 30 times in five minutes can see `RATE_LIMITED`; those people retry after the window.

Codes during the proof went only to the throwaway `epe.launchprep@sedamedical.com` (not an employee). That user and those codes are gone.

---

## 3. Write-path integrity

No schema change. CALCULATION_MAP §B.3 was correct: submit/update previously stored the client `final_score`. They now ignore it and set `calculated_score = AVG(score_val)` of the same evaluation's score rows. Grades outside 1–10 still return `422 GRADE_OUT_OF_RANGE` and write nothing. Self-review `weighted_score` was not touched.

| Case | Result |
|---|---|
| Manager submit Alina, grades 6, 8, 7, client `final_score=1` | stored `7.00` = mean of rows |
| Upward Alina → Akmyrat, client `final_score=99` | stored mean of the grade rows |
| Grade `11` for Asadbek | `422 GRADE_OUT_OF_RANGE`; evaluation count unchanged; Asadbek rows `0` |
| Update Alina, grades 9, 9, 6, client `final_score=2` | stored `8.00` |

---

## 4. Rehearsal

Production API, real user rows, temporary JWTs + `auth_sessions` only. **No `password_hash` written on any real account.** H1 activated for the pass, then returned to draft. Rows deleted. Dumps before and after.

| Step | Result |
|---|---|
| No-period employees / HR | empty, `campaign_active=false` |
| Activate H1 | 200, id=2 active |
| Scope lists | Esenova/Balova absent; 87/89 |
| Classification Alina general→project→general, before any eval | 200 / 200 |
| Self-review Alina | 200 |
| Upward Alina → Akmyrat | 200 (tampered `final_score` ignored) |
| Manager submit Alina | 200, stored 7.00 |
| Out-of-range Asadbek | 422, no row |
| Manager update Alina | 200, stored 8.00 |
| Classification after first eval | **409 CLASSIFICATION_FROZEN** |
| HR status | 87 in scope, excluded pair absent |
| `periods/create` with client `status=active` | stored **draft / inactive / half_year** (temp id=4 deleted) |
| Delete rehearsal evaluations while H1 still active | classification edit **200** (freeze lifted) |
| H1 back to draft; coefficient GET + POST same values | **200** (period freeze lifted) |
| End-state string | `0\|0\|0\|0\|1\|0\|draft,false\|general` |

Browser UI pass while H1 was active was not repeated; the excluded-pair proof is the API pass above. After return to draft, the production bundle correctly shows an empty campaign list.

Alexander can still edit classification and coefficients between now and 31 Aug.

---

## 5. Invitations

`docs/INVITATION_WAVES.md` has all five parts: wave list (managers first, then by department), registration one-pager, Russian email draft with a marked second-language slot, registered-users query plus Admin → Сотрудники badge, deliverability result.

The system sends only verification-code and reset mail. Alexander sends the invitation with the shared registration link from Admin → Periods.

Deliverability (system mail only):

- Sender: `noreply@sedamedical.com`
- SPF present: `v=spf1 include:_spf.google.com ~all` (softfail)
- DMARC: `p=none`, reports to `eziz@sedamedical.com`
- MX: Google Workspace
- DKIM: **no public selector found**
- Inbox/spam test to a company mailbox and an external mailbox: **not sent** — no mailboxes were named in this brief

---

## 6. Housekeeping (one line each)

- **Decision register:** `DECISIONS.md` is the single register; `PROJECT_DECISIONS.md` is a pointer.
- **Registered users:** 1 (`alexander@sedamedical.com`).
- **Real `password_hash`:** none set during this brief or the rehearsal.
- **`acceptance_tokens.json` / `browser_accounts.json`:** never in `git ls-files` or `git log`; nothing to rotate.
- **`periods/create`:** already forces `status='draft'`, `is_active=false`, `period_type ∈ {half_year, annual}`; client `status` is ignored. Rehearsal proved it. HANDOVER §7.3 is done.

---

## Disagreements vs architect hypotheses

- Campaign `GET /api/employees` listed all org-tree subordinates by `manager_id` — confirmed BUG-007, now closed.
- HR status counted all users with a manager, not in-scope participants — same bug, now closed.
- Submit/update already validated grades 1–10 but stored client `final_score` — CALCULATION_MAP §B.3 was right; now they store the row mean.
- Self-review still stores client `final_score` / `weighted_score` — left untouched, as required.
- `periods/create` already handled `period_type` and `status`; this brief did not need a code change there.
- Classification freeze is “any evaluation in the active period”; coefficient freeze is “any period `is_active` or `status='active'`”, not evaluation count. After rehearsal rows were deleted, both writes returned 200.
- There is no `clear-test-evaluations` route (deleted in the previous brief). Cleanup was SQL delete + dump, on purpose.
- `PROJECT_RULES.md` does not exist.
- `performance_db.auth_verification_codes` does not exist; codes live in `email_verification_codes`.

---

## Surface for decision

1. **Frontend rebuild.** Already deployed (`20260819T120100Z`): empty-campaign copy, task status, periods «В охвате», register cooldown, registration badge. This should not wait until 26 Aug.
2. **No active period.** Recommendation: keep empty campaign lists (what shipped). Do not show the org tree in campaign views.
3. **DNS / mailbox (Alexander).**
   - Publish Google Workspace DKIM TXT (typically `google._domainkey.sedamedical.com`). Without it, `noreply@` will often land in Spam.
   - Confirm `noreply@sedamedical.com` exists as a user or alias.
   - Name one company mailbox and one external mailbox for a real inbox/spam test. I will not send to employees or to unnamed boxes.
   - Do not change SPF `~all` → `-all` until DKIM is live and you know n8n SMTP is Google.
4. **Shared invite vs per-wave tokens.** Recommendation: **keep the single shared link** for H1. Alexander is the only admin; BUG-008 is an audit-trail issue, not an authorization hole. Per-wave tokens are not worth it now.
5. **Cooldown / throttle.** 60 s resend will not block a legitimate employee. 30 / 5 min / IP can bite a large office NAT; those people retry. I would not raise the limit before the first wave.

---

## Files

- `docs/briefs/LAUNCH_PREP_2026-08-20.md`
- `docs/INVITATION_WAVES.md`
- `docs/HANDOVER.md` §3 / §7
- `bugs.md` — BUG-007 closed; BUG-008 open
- `DECISIONS.md` / `PROJECT_DECISIONS.md`
- `src/context/TaskStatusContext.jsx`, `src/hooks/useDashboardData.js`, `src/pages/Dashboard.jsx`, `src/pages/AdminPeriods.jsx`, `src/pages/Register.jsx`, `src/components/admin/UserTable.jsx`
- `scripts/build_auth_workflows.py`, `scripts/build_route_guard_workflows.py`
- `n8n_workflows/API_ Send Verification Code.json`, `n8n_workflows/API_ Verify Invite.json`
