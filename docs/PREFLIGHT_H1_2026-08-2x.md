# H1 launch pre-flight — re-verification of the 2026-08-20 fixes

**Date of work:** 2026-08-20 (evening, after the 15:46 UTC PUT and the `20260820T154749Z` deploy)
**Method:** read-only against the live system — `workflow_entity` / n8n REST API over the SSH tunnel, `epe_2026` and the 2025 archive by SELECT only, deployed bundle grepped on the host, one safe HTTP probe. No PUT, no deploy, no DB write, no mail. The repo's `n8n_workflows/` exports were treated as untrusted until diffed node-for-node against live.

---

## Verdict

**H1 can be activated: yes.** Every Part 1 baseline value matches live; all six server rules from `docs/PRELAUNCH_FIXES_2026-08-2x.md` re-verified pass against the live workflow definitions; the previously unproven read-only C-level behavior (Part 3) is proven correct from live SQL plus the deployed bundle — no fix was needed anywhere, so no PUT and no deploy happened. Standing reminder: **Alexander must finish the project/general classification in Admin → Сотрудники BEFORE pressing Activate — those writes return 409 once a period is active.**

---

## Part 1 — Baseline (expected vs live)

| Check | Expected | Live (this session) | Verdict |
|---|---|---|---|
| H1 period id=2 | `draft`, `is_active=false` | `draft`, `f` | ✅ |
| Participants period 2 | 87 in scope / 89 | 87 / 89 | ✅ |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` | `2026-08-18 16:34:30.674+00`, `f` | ✅ |
| Workflows | 58 total / 33 active | 58 / 33 (22 archived) | ✅ |
| Registered webhooks | 37 | 37 | ✅ |
| Frontend `current` | `releases/20260820T154749Z` | symlink matches; `20260820T065435Z` still on disk | ✅ |
| Certificate | notAfter 2026-11-17 | `Nov 17 04:31:09 2026 GMT`, Let's Encrypt YE1 | ✅ |
| Origin | portal at `https://epe.sedamedical.com` | Russian SPA HTML served | ✅ |
| 2025 archive (`postgres.performance_db`) | 73 / 234 / 644 / 3 | users 73, evaluations 234, scores 644, corrections 3 | ✅ |
| `epe_2026` | evaluations 0, scores 0, corrections 0 | 0 / 0 / 0 | ✅ |
| Invite id=4 | `is_used=false` | `f`, expires 2026-09-18 | ✅ |

No mismatches.

---

## Part 2 — Six server rules, live-definition re-verification

All workflows were fetched live this session; every `updatedAt` equals the fix report's PUT table. Repo exports for all seven routes diff **node-for-node identical** to live (`Prepare Guard Input` / query / format code compared as strings).

### a. My Profile V5 (`jCKNLytVw0qEF17W`, 15:46:56) — ✅ pass

The SQL selects **no comment columns at all**, and score fields are attached only to self rows:

```js
if (isSelfEvaluation) {
  evaluation.score = row.calculated_score;
  evaluation.calculated_score = row.calculated_score;
  evaluation.weighted_score = row.weighted_score;
}
```

Stats come from self only: `const selfEvaluations = evaluations.filter(e => e.is_self_evaluation);` → `average_score`, `latest_*` derived from `selfEvaluations`; `total_evaluations` keeps the fact-of-evaluation count. Upward evaluator identity is nulled: `evaluator_name: row.evaluation_source === 'subordinate' ? null : row.evaluator_name`.

### b. Get Evaluation Details FIXED (`s2mrMporGOx0h14B`, 15:46:53) — ✅ pass

```sql
WHERE e.id = ${rawEvalId}
  AND (
    ${privileged}                    -- ['admin','c_level'].includes(actorRole); HR is NOT in the list
    OR e.evaluator_id = ${actorId}
    OR (e.subject_id = ${actorId} AND e.is_self_evaluation = true)
  )
```

Zero rows → `404 «Оценка не найдена или недоступна вам»`. `private_comment` additionally nulled unless privileged or evaluator; upward evaluator identity hidden from the subject.

### c. Check Self Review (`QRkUvs24DkcC3WBW`, 15:46:51) — ✅ pass

```sql
WITH selected_subject AS (
  SELECT CASE
    WHEN ${requestedId} = ${actorId} THEN ${actorId}
    WHEN ${privileged} THEN ${requestedId}
    WHEN EXISTS (SELECT 1 FROM performance_db.users target
                 WHERE target.id = ${requestedId}
                   AND target.manager_id = ${actorId}) THEN ${requestedId}
    ELSE ${actorId}
  END AS subject_id
)
```

Exactly self / admin+c_level / direct report; anything else silently falls back to the actor's own row (no 403, no leak). Rows additionally bound to `p.is_active = true AND p.status = 'active'`.

### d. Get Criteria With Levels (`KKlGLEYMlXlbYUjb`, 15:46:52) — ✅ pass

```js
const canSeeCLevelTexts = ['admin', 'c_level'].includes(String(guard.identity.role || ''));
const levelTextFields = Array.from({ length: 10 }, (_, i) => `level_${i + 1}_desc`);
...
if (isCLevelOnly && !canSeeCLevelTexts) { levelTextFields.forEach(f => delete criterion[f]); }
```

Titles and descriptions kept for everyone. `level_0_desc` is outside the stripped list but is **empty on both live `c_level_only` rows (ids 1, 10)** — checked; nothing leaks through it today.

### e. Score Correction (`rSZcm0HDMUHLYk8W`, 15:46:49) — ✅ pass

```js
required_roles: ["admin", "c_level", "manager"],
required_capability: "can_evaluate",
```

The Auth Guard's live `Authorize` node enforces it: `identity[parsed.required_capability] !== true` → `403 CAPABILITY_FORBIDDEN` — identity (incl. `can_evaluate`) is read from the DB per request. Score range 1–10 → 422; no active period → 409 `NO_ACTIVE_PERIOD`; `mid_level` = skip-level manager, admin/c_level store `c_level`.

### f. Get Employees + Get My Manager (`bKB4Sb46yWoq1tSV` 15:46:09, `3C1u68KOTSMwcqgy` 15:46:54) — ✅ pass

Employees `scoped` CTE:

```sql
WHERE users.manager_id = ${actorId}
  AND ${actorCanEvaluate}
  AND COALESCE((SELECT is_in_scope FROM actor_scope), false)
```

joined to `active_period` and `epp.is_in_scope = true`; the three flags are `EXISTS(...)` booleans `has_self_review` / `has_evaluated_manager` / `evaluated_by_actor`; `actor_is_in_scope` is always in the payload. Coefficient stripping in both workflows: `const canSeeGradeCoefficient = ['admin', 'c_level'].includes(...)` — employees `delete safeEmployee.grade_coefficient`, my-manager `...(canSeeGradeCoefficient ? { grade_coefficient: m.grade_coefficient } : {})`.

### g. Live probe — ✅ pass

`GET https://epe.sedamedical.com/webhook/api/verify-invite?token=preflight-bogus-…` →

```json
{"success":true,"valid":false,"message":"Ссылка-приглашение недействительна или срок её действия истёк"}
```

Russian, no English, no `/api/` path.

---

## Part 3 — Read-only C-level (Cem 21, Hemra 40, Mekan 61)

**Verdict: was already correct — nothing to fix, nothing was PUT or deployed.** The `can_evaluate` predicate shipped inside the 15:46 PUT of `API: Get Employees` (generator `scripts/build_auth_workflows.py:1440` — `AND ${actorCanEvaluate}`); the fix report simply never proved it. Proven now:

Live DB facts: all three are `c_level`, `can_evaluate=false`, `can_be_evaluated=false`, **in scope** (`is_in_scope=true`, part of the 87). Cem has `has_subordinates=true` and **3 direct reports** (`manager_id=21`); Hemra/Mekan have none.

**Server.** `/api/employees` for Cem: `actorCanEvaluate` comes from the guard identity (live DB read) → `AND false` → `scoped` is empty → `data: []` even though his line exists, while the envelope keeps `success`, `actor_user_id`, `campaign_active`, `current_period_id/status`, `actor_is_in_scope: true` — the exact shape `TaskStatusContext` consumes. This holds both today (draft; `active_period` empty for everyone) and after activation (the predicate is the actor's flag, not the period). Submit is double-closed: `API: Submit Evaluation` guard input has `required_capability: "can_evaluate"` (403 `CAPABILITY_FORBIDDEN` before any SQL) plus an in-workflow `if (!validation.can_evaluate)` re-check. Corrections need the same capability (Part 2e).

**Client (deployed `20260820T154749Z`, verified in the minified bundle on the host, which matches src).** `TaskStatusContext` sets `hasSubordinates = campaignActive && subordinates.length > 0` → **false** for the trio. Consequences, each traced in the bundle:

- Sidebar «Команда» gate is `!isOutOfScope && !isHR && (hasSubordinates || user.has_manager_subordinates || role === 'manager')` (bundle: `!h&&!Xo(v.role)&&(d||v.has_manager_subordinates||v.role===\`manager\`)`) → hidden: context flag false, `has_manager_subordinates` is never set by login (login's `safeUser` spreads the users row, which has no such column), role is `c_level`.
- Dashboard (only via typed URL): `processedSubordinates.length === 0` → empty-state card «Кампания ещё не открыта» / «Нет сотрудников в этой кампании», zero `EmployeeCard` → **zero «Оценить» CTAs**; no dead buttons.
- Welcome: the subordinate-evaluation chip and the manager process block key off the same context `hasSubordinates` → absent.
- Самооценка: `needsSelfReview = !isCLevel && !isOutOfScope` → no task chip; the page renders the exempt card «Самооценка не требуется» for c_level — no form, no submit.
- «Оценить руководителя»: the trio has `manager_id NULL` → `has_manager=false` → page shows «Руководитель не назначен» (pre-existing, documented §4.8 row 8).
- OutOfScopeNotice does **not** fire (`actor_is_in_scope=true`) — correct: they are in scope as September readers, not as H1 writers.
- Reporting untouched: Аналитика group (`/analytics`, all-evaluations, matrix, final scores, bonus) renders for `c_level` via `canViewAnalytics`; routes are `ReportingRoute` (admin + c_level); none of those five APIs gate on `can_evaluate`.

**Observations, report-only (outside the stated rules, not fixed):**

1. The sidebar task panel «Мои задачи» renders as an **empty box** for the trio (all three chip conditions false). Cosmetic.
2. `AdminEvaluationsMatrix` (reachable by the trio as c_level) renders correction inputs; a save would hit the server's capability gate → 403, surfaced by `errorHandler.js` as the generic «Доступ запрещен. Недостаточно прав» (known interceptor leftover). Affects exactly 3 users, September screens, server-safe.
3. Login's `safeUser` includes `can_evaluate` / `has_subordinates` raw columns client-side; nothing binds UI affordances to them today — the UI keys off the campaign list, which is the safer server-derived signal.

---

## Part 5 — Registrations & sessions (read-only, nothing deleted, no mail)

Users with `password_hash IS NOT NULL` — **2**:

| id | email | role | first login (UTC) | last login (UTC) |
|---|---|---|---|---|
| 2 | alexander@sedamedical.com | admin | 2026-08-19 20:19:26 | 2026-08-20 12:32:20 |
| 47 | jemal@sedamedical.com | c_level | 2026-08-20 12:22:21 | 2026-08-20 12:22:21 |

`auth_sessions`: 4 rows, 2 distinct users, issued 2026-08-19 20:19 → 2026-08-20 12:32 UTC, 2 unexpired. (Same 2/4 the fix report saw before its PUT — no drift.)

---

## Part 6 — Git

Working tree reviewed file-by-file before committing: no secrets (compose files use `${ENV}` refs; the only `eyJ…` strings are deliberately forged negative-test tokens with `not-a-real-signature`; no salary values anywhere — column names only; `public/шаблон_импорта_сотрудников.xlsx` is a template with fictional example rows, already served by the live origin by design). Build artifacts excluded via `.gitignore` (`dist.zip`, `__pycache__/`); `backups/` and container-inspect dumps were already ignored. Nothing unexpected found → committed. `npm test` re-run before committing: **182 pass / 0 fail**.

| Hash | Commit |
|---|---|
| `92ba7cc` | Track backend baseline: workflow exports, generators, proof and deploy scripts |
| `911e3bd` | Track frontend: pre-launch visibility fixes, drafts, out-of-scope UX, tests |
| `090871b` | Track project docs: brief reports through 2026-08-20, plan, env template |
| (this commit) | Pre-flight report, PROGRESS entry, bugs.md rows BUG-024…027 (closed) |

`bugs.md`: added closed rows **BUG-024** (check-self-review regression), **BUG-025** (subject-side score leak), **BUG-026** (c_level_only level texts), **BUG-027** (correction capability gate) — the four defects this week's pre-launch brief actually closed; stats 9 open / 18 closed. No open row changed state.

---

## Constraints held

- Live H1 stayed `draft` / `is_active=false`; nothing activated or deactivated anywhere (no throwaway stand was needed — no fixes).
- `EPE: Auth Guard` untouched: `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` at start and finish (re-read after the last query).
- Zero writes to live `epe_2026` and zero writes to the 2025 archive (SELECT only; no dump needed — no data-touching operation ran).
- `auth_sessions` untouched — 4 rows before and after.
- No mail to anyone (D-0820-8). No PUT, no deploy (Part 4 never triggered).

---

## Final verdict

**H1 can be activated: yes.** No blockers. Before pressing Activate on 31 Aug, Alexander finishes the project/general classification of the 89 in Admin → Сотрудники (freezes with 409 after the first submission in the active period) — and sends the invitation on 26 Aug per `LAUNCH_RUNBOOK_H1.md`.
