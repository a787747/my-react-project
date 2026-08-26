# ROLE_ACCESS_HR_CLEVEL — C-level reads the admin surfaces, HR reads the roster (2026-08-26)

**Brief:** ROLE_ACCESS_HR_CLEVEL (fresh session). **Campaign OPEN since 2026-08-26 10:08:54Z.**

**Outcome in one line: the owner's report is diagnosed to the line — the empty employees page is
a 403 the screen swallows, the /team pattern exactly — and the full change is built, generated,
pinned by 439/439 tests and pushed; but this session ran in a remote cloud container with NO
access to the Mac, the VPS, or live, so nothing here has touched the running system: the stand
proof, the live dump, the deploy and every live verification remain for a Mac session, with the
scripts for all of it written and ready.**

---

## 0. Environment — read this first

The brief says "ON THE MAC". This session was not on the Mac. It ran in an isolated cloud
container holding a fresh clone of the repository and nothing else:

- no SSH binary and no keys — `92.51.45.147` unreachable;
- the container's egress proxy refuses CONNECT to `epe.sedamedical.com` (403) — live unreachable
  even read-only;
- no Docker daemon — no stand, no restored dump, no browser walkthrough against a running system.

Everything below is therefore split honestly into **what is proven here** (static: the code, the
generated workflow definitions, the test suite, the production build) and **what is NOT proven**
(everything the acceptance section demands against the running system). No claim in this report
is a live measurement. The server-side facts come from the generators, which the PRELAUNCH_GATE
and EMPLOYEE_SURFACES_POLISH sessions measured byte-identical to live `workflow_entity`
(32 identical / 0 changed, last at 2026-08-26 ~11:04Z); any PUT to live after that would move
this baseline, so the Mac session re-runs the drift check before trusting it.

## 1. Diagnosis (brief outcome 1) — what each page requires today and what each role receives

Server-side truth = the guard's `required_roles` passed to the frozen `EPE: Auth Guard`
(`updatedAt 2026-08-18T16:34:30.674Z`, untouched by this brief). Frontend truth = `src/App.jsx`
route wrappers. State before this brief:

| Page | Frontend gate (before) | Feeding route(s) | Server roles (before) | What c_level got | What HR got |
|---|---|---|---|---|---|
| `/admin/users` («Сотрудники» — the same page is HR's «Сотрудники» via the HR sidebar) | `AdminRoute` (admin, c_level, hr) | `GET api/admin-users-data` | **admin only** | **empty table** | **empty table** |
| `/admin` (Критерии) | `AdminRoute` | `POST manage-criteria {action:'get'}` | **admin only** | empty catalogue | empty catalogue (typed URL — BUG-013) |
| `/admin/all-evaluations` | `ReportingRoute` (admin, c_level) | `GET api/admin/all-evaluations` | admin, c_level | works | redirect to /hr/dashboard |
| `/analytics` | `ReportingRoute` | `GET api/analytics` | admin, c_level | works | redirect |
| `/admin/evaluations-matrix` | `ReportingRoute` | `GET api/admin/evaluations-matrix` | admin, c_level | works | redirect |
| `/admin/final-scores` | `CoefficientRoute` (**admin only**) | matrix + `GET api/score-coefficients` (**admin only**) + `api/admin-users-data` (**admin only**, grades feed) | **redirect to /welcome** | redirect to /hr/dashboard |
| `/admin/score-calculator` | `CoefficientRoute` (**admin only**) | same three | **redirect** | redirect |

**The owner's empty-page report, established from code:** `/admin/users` admits all three roles at
the route level, `useUsers` fetches admin-only `api/admin-users-data`, gets 403 `ROLE_FORBIDDEN`
from the guard, catches it, sets an `error` state — and `AdminUsers.jsx` destructured only
`loading`, never `error`. The page then rendered its full chrome over `users: []`: «Найдено: 0»,
no message. **It is a 403 the screen swallows — the /team pattern (BUG-012) exactly.** Same
pattern, same silence, on `/admin` (criteria): `useCriteria` logged the 403 and left the
catalogue empty.

Also established: the `admin-users-data` SQL selects **no salary column** for any role — `salary`
appears in no workflow payload and nowhere in `src/`; the protected salary columns live only in
the database and the import scripts. The one money input in that payload is
`options.grades[].coefficient` (grade coefficients, D-0822-2 admin-eyes-only).

## 2. What was built (brief outcomes 2–4)

### Server side — four workflow generators (repo `scripts/`, generated JSON in
`n8n_workflows/route_guard_h1|route_guard_deferred/`); NOT yet on live

| Workflow | Change |
|---|---|
| `API: Admin Get Users Data` | guard `["admin"]` → `["admin","hr","c_level"]`; the merge strips `options.grades[].coefficient` for **hr** (`{id, code}` only). Admin and c_level keep it — the money screens c_level may now read feed from this route. |
| `API: Get Score Coefficients` (GET) | guard `["admin"]` → `["admin","c_level"]`. The POST save workflow stays `["admin"]`. |
| `API: Manage Criteria Admin V7` | guard `["admin"]` → `["admin","c_level"]`; `action !== 'get'` now refuses every non-admin **403 ROLE_FORBIDDEN before the freeze check and before any SQL**. |
| `API: Score Correction` | guard `["admin","c_level","manager"]` → `["admin","manager"]` (capability `can_evaluate` unchanged); the `c_level` branch of `Decide Level` removed — **see §4, this narrows D-0820-7**. |

Every other write route was verified already admin-only in its generator: save-user, terminate,
reinstate, exclude/include-participant, all six period mutations + start-evaluation, save
score-coefficients, update-admin-data, create-invite, employee-events/employment-events/
period-scope-events (admin-only reads). No write route accepts `hr` today; after this change none
accepts `c_level` either. Submit/update-evaluation (c_level_direct, D-0820-7) and
self-review-submit are deliberately untouched — they are the campaign's designed writes, and the
brief does not list them.

### Frontend

- `/admin/final-scores`, `/admin/score-calculator` → `ReportingRoute` (admin + c_level);
  `/admin/scoring` and `/admin/bonus-calculation` stay `CoefficientRoute` (admin-only).
- `/admin` (Критерии) → `ReportingRoute`: c_level reads it, HR is redirected to /hr/dashboard
  instead of the silent empty shell — the HR half of BUG-013.
- Sidebar: «Итоговые баллы» and «Калькуляция баллов» offered to the analytics audience
  (admin + c_level); «Критерии» offered to c_level; «Калькуляция бонусов», «Периоды»,
  «Коэффициенты» stay admin-only.
- `/admin/users` is read-only below admin: `canEdit` is now the admin check, so Добавить/Excel/
  edit/terminate/scope/import affordances are not rendered for hr or c_level (the server refuses
  them anyway — hiding the button is UX, the 403 is the access control).
- `/admin` (criteria) read-only below admin: no add button, no Действия column, no test-data
  cleanup block; subtitle says «только чтение».
- Correction affordance (`ScoreDetailModal.canCorrect`): admin or skip-level **manager** only —
  role c_level no longer sees a correction control it would be refused on.
- **Refusal surfaces (outcome 4):** `AdminUsers`, `AdminSettings`, `AdminAllEvaluations`,
  `AdminEvaluationsMatrix` now render the server's refusal (or failure) with a retry instead of a
  blank list; `useUsers`/`useCriteria`/`useAllEvaluations`/`useEvaluationsMatrix` carry
  `err.userMessage` to the screen; `Analytics` now includes the server reason in its existing
  error card; `useScoreCalculation` no longer substitutes an empty coefficient set on failure —
  the BUG-030 `allSettled` pattern, which closes the code half of **BUG-042**.

## 3. What is proven here — and what is not

**Proven in this environment:**
- `npm test`: **439/439** (423 baseline + 16 new/updated pins in
  `tests/roleAccessHrClevel.test.js`, `routeGuardWorkflows.test.js`, `routeGuardDeferred.test.js`,
  `evaluationStartGate.test.js`). The new pins hold: the four role lists exactly; the hr
  grades-coefficient strip; the criteria write-refusal by role placed before the freeze; no
  salary column in the roster route; the frontend route gates; the read-only affordances; every
  refusal surface.
- Production build: passes. Changed-file ESLint: **no new errors** (Sidebar.jsx and
  ScoreDetailModal.jsx carry pre-existing errors, byte-identical count at HEAD — verified by
  linting the HEAD versions).
- The four generated workflow JSONs regenerate deterministically with the changed guards.

**NOT proven — every acceptance item that needs the running system:**
- the role × route matrix against real HTTP (script ready: `scripts/prove_role_access.py`);
- the write-refusal list as real calls; the compensation walk over actual response keys;
- the browser walkthrough as c_level and HR;
- the stand from a fresh live dump, the deploy, and every live-after check.

## 4. Surfaced — decisions the brief made or left, in the executor's words

1. **Corrections: the brief supersedes the writer half of D-0820-7, and I implemented the brief.**
   D-0820-7/§3 made admin **and c_level** the writers of `c_level`-level score corrections; the
   brief says every write route, corrections listed by name, "must refuse both roles by role,
   server-side", and the acceptance demands that refusal as a real call. Implemented: role
   `c_level` gets 403 `ROLE_FORBIDDEN` on `api/admin/score-correction`; `c_level`-level
   corrections are stored by **admin alone**; the mid_level (skip-level manager) path is
   untouched. Consequence for September calibration: Bayram (18) and Jemal (47) can no longer
   store corrections — they calibrate their own channel by evaluating (averaged, D-0826-1), and
   any manager-channel correction goes through Alexander. **If this is not what the owner meant,
   it is a one-line revert in each of two generator files** (`guard_input_js` roles and the
   `Decide Level` branch) — say so before the Mac session deploys.
2. **"Password reset must refuse both roles" cannot be implemented as written.** Both routes
   (`api/request-password-reset`, `api/reset-password`) are unauthenticated self-service account
   recovery — there is no actor and no role to refuse, and refusing hr/c_level would mean those
   five people cannot recover their own accounts. No admin-triggered reset-someone's-password
   route exists. Nothing was changed; the prover deliberately does not call these routes (the
   request route sends mail — D-0820-8).
3. **The employee-card history (`GET api/admin/employee-events`) stays admin-only.** It is an
   audit read (actor ids, old→new values) that the brief does not name; the read-only roster for
   hr/c_level simply does not render the history affordance. Widening it is a separate decision.
4. **Stale tracked generator outputs found (not this brief's).** Regenerating
   `n8n_workflows/route_guard_h1|route_guard_deferred/` showed three files stale against their own
   HEAD generators (`evaluations-matrix.json`, `manage-periods.json`, `save-user.json` — the
   2026-08-26 08:52 rewrites never refreshed these snapshots, only the top-level exports) and two
   never committed at all (`manage-employment.json`, `manage-period-scope.json`). I reverted the
   three and removed the two — this commit carries only this brief's four files. Filed as
   **BUG-077** (the BUG-045 family, subdirectory instance).
5. **`/admin/bonus-calculation` is not in the brief's list** and stays admin-only everywhere. If
   the owner expected C-level to see the budget screen too, that is a new decision.
6. **The C-level evaluation affordance on the matrix remains** for c_level (the campaign's
   designed write, D-0820-7 submit path, not in the brief's refusal list). A read-only C-level
   account (Cem/Mekan/Hemra) that tries it is refused server-side with 403
   `CAPABILITY_FORBIDDEN`, which the modal shows — a natural candidate for the walkthrough's
   "one refusal message shown".

## 5. Runbook for the Mac session (in order; nothing here was executed)

1. Read this report; `git pull` the branch `claude/hr-clevel-access-control-dudin7`.
2. Re-read live state (89/3/79, tables, `evaluation_started_at`) — it has moved since 11:04Z.
3. **Fresh dump pair before any live write**, copied to the Mac outside the repo, md5 both sides
   (the EMPLOYEE_SURFACES_POLISH §7 procedure).
4. Throwaway stand restored from that dump, gate pressed on the stand through the real route;
   import the four changed workflows; run
   `scripts/prove_role_access.py --base <stand> --pg-container <…> --n8n-container <…> --db <…>`
   — expect PASS (positive + negative matrix, write refusals one by one, compensation walk).
   Browser walkthrough on the stand as c_level and as HR: seven pages with real data, no edit
   affordance, one refusal shown.
5. `python3 scripts/check_live_drift.py --expect-changed "API: Admin Get Users Data,API: Get
   Score Coefficients,API: Manage Criteria Admin V7,API: Score Correction"` — anything else
   changed → stop, someone touched live.
6. `python3 scripts/deploy_role_access_hr_clevel.py` (read-only), then `--apply`. It refuses on a
   moved Auth Guard, verifies graph/active/webhooks after each PUT, refreshes the four top-level
   exports, and hard-fails if `evaluation_started_at`, population, or any coefficient fingerprint
   moved during the window; table-count movement is reported as employee activity, not swallowed.
7. Frontend: `npm ci && npm test && npm run build`, then `./scripts/deploy_epe_frontend.sh`
   (its own lock and CAS gates; it has no started-campaign refusal — EMPLOYEE_SURFACES_POLISH
   deployed after the press).
8. Live verification: `prove_role_access.py --base https://epe.sedamedical.com/webhook`;
   open the seven pages as a real c_level account (non-empty); confirm campaign still open,
   `evaluation_started_at` unchanged, table counts as before modulo real submits, 89/3/79 (or the
   then-current measured population), catalogue/coefficients/grades md5 vs
   `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`, Auth Guard `updatedAt`
   unchanged. Record everything in a follow-up section of this report.

## 6. §4 of HANDOVER, for the record

Nothing in this brief touches a formula, the catalogue, a coefficient value, or any money
computation. The only money-adjacent change is **who may read** coefficients and the matrix
(c_level, granted by the owner in this brief) — every value, every weight, every writer path is
byte-identical, and the save routes remain admin-only.

## 7. Session hygiene

- No live system was reachable, so no live write, no dump, no stand, no container, no mail.
- The working tree was clean at start (fresh clone); every modified file is this session's; the
  three stale generator snapshots found mid-work were reverted, not adopted (§4.4).
- `EPE: Auth Guard` untouched: no generator or JSON of it modified; the deploy script refuses to
  run if its live `updatedAt` differs from the frozen value.

**Implementation commit:** `5c46052`.

---

# §8. DEPLOYED AND PROVEN ON LIVE — follow-up by the Mac session (ROLE_ACCESS_DEPLOY, 2026-08-26)

**Outcome in one line: the change is live and proven — the branch was reviewed, the owner's
correction applied (D-0826-7: c_level KEEPS its score corrections, D-0820-7 stands), three
workflows PUT at 13:46:55–57Z, the frontend flipped to `20260826T134725Z`, and the full
acceptance ran against the running system: 151-cell role×route matrix PASS on the stand and PASS
on live, a real accepted c_level correction stored on the stand, seven non-empty pages as the real
c_level account and the roster as the real HR account in a real browser on live, zero compensation
keys in any payload, and every campaign invariant byte-identical before and after.**

## 8.1 The owner's correction (D-0826-7)

The brief's instruction to refuse role `c_level` on corrections (§4.1 above) was wrong and was
reverted BEFORE anything reached live: D-0820-7 stands, `c_level` (with `can_evaluate`) is the
intended author of `c_level`-level corrections. Revert commit `fd637c1` on the branch; the
regenerated `route_guard_deferred/score-correction.json` came out byte-identical to live (the
drift check listed it among 29 identical), so the deploy script's UPDATES entry for it reported
`"changed": false` and no PUT was made — live `API: Score Correction` still reads
`updatedAt 2026-08-26 07:57:50.177Z`. Recorded in `DECISIONS.md` as **D-0826-7** with a
strike-through banner in D-0826-6. Corrections are now the ONE write route that admits `c_level`;
every other refusal of D-0826-6 landed as built.

## 8.2 What was done, in order

1. Branch reviewed as foreign work — no substantive disagreement beyond §4.1 (already corrected
   by the owner). Landed on main as merge `3b97581`; **PR #2 MERGED 2026-08-26T13:36:01Z**. The
   previous session's scheduled PR check-in (`trig_01Awcwu6g7iXbL6XREaAamGj`, one-shot 14:25Z)
   was disabled at 13:31:20Z before it could fire (the API cannot delete routines — the owner can
   remove the dead row at claude.ai/code/routines).
2. Live re-read 13:36–13:38Z: tables **0/0/0/0**, population **89/3/78** — the brief said 79, but
   the owner excluded **Aysoltan Kulmamedova (16)** at 12:31:49Z (`excluded_by_admin`, his page);
   roles now 1 admin / 5 c_level / **13 manager** / 2 hr / **68 employee** (one employee→manager
   move since the 24 Aug reading, `employee_card_events` is empty so it predates migration 017's
   logging path); HR **Liya Dmitriyeva (52) is registered** (third registered account). All owner
   activity, not drift.
3. **Fresh dump pair before any live write**: `epe_2026_20260826T133855Z.dump`
   (md5 `4afb0ae10c4585db6c4d46b4ebad2bbd`) + `n8n_app_20260826T133855Z.dump`
   (md5 `23b8516cc936b36b48af0deb384c8124`), VPS `/root/epe_stand_tmp` → Mac
   `~/EPE_ROLLBACK/2026-08-26-role-access/`, md5 identical both sides.
4. Zero-drift check: exactly the three intended workflows differed from the generators; 29
   identical, score-correction among them.
5. **Stand** `epe_roleaccess_20260826_1341` ← that dump (period 2 started, inherited), container
   `epe-roleaccess-n8n` on VPS loopback :25679 with the working-tree surface
   (`scripts/setup_roleaccess_throwaway.sh`). Proofs on the stand:
   `prove_role_access.py` **PASS, 151 cells** (`backups/2026-08-26-role-access/prove_role_access_20260826T134509Z.json`);
   `prove_roleaccess_stand_accept.py` **PASS** — Bayram (18) stored a real accepted `c_level`
   correction on criterion 3 (200, row stored), Jemal (47) then upserted over it — the stored row
   read `evaluator 47, score 6, level c_level`, one row total, which is the known
   last-writer-wins residue in BUG-073's row, reproduced, not new.
6. **Deploy**: `deploy_role_access_hr_clevel.py` read-only then `--apply` —
   `API: Admin Get Users Data` → 13:46:55.454Z, `API: Get Score Coefficients` → 13:46:56.606Z,
   `API: Manage Criteria Admin V7` → 13:46:57.784Z; score-correction `changed: false`, no PUT;
   Auth Guard checked before and after; graph/active/webhooks verified after each PUT; the three
   top-level exports refreshed. Frontend `npm test` 439/439 → build →
   `./scripts/deploy_epe_frontend.sh` — **FLIPPED `releases/20260826T134725Z`**
   (was `20260826T110433Z`, which is the rollback target).
7. **Live proof**: `prove_role_access.py --base https://epe.sedamedical.com/webhook` —
   **PASS, 151 cells, 0 failures** (`prove_role_access_20260826T134914Z.json`).

## 8.3 The acceptance, item by item

- **Role × route matrix, positive and negative, on live:** 151 cells, every cell a real HTTPS
  call with its status recorded in the artifact. Ordinary manager and ordinary employee: **55
  cells of 403** covering every admin surface (roster, coefficients, criteria, matrix,
  all-evaluations, analytics, details-by-user, periods, annual-rollup, HR status,
  employee-events).
- **Every write route as c_level and as hr, refusal by refusal:** save-user, terminate,
  reinstate, exclude/include-participant, all six period mutations + start-evaluation,
  manage-criteria save и delete, save-score-coefficients, update-admin-data, create-invite — 403
  `ROLE_FORBIDDEN` for both roles, every row in the artifact. **Corrections deliberately still
  accepted for c_level:** the read-only c_level (Cem 21) reads 403 `CAPABILITY_FORBIDDEN` — the
  role passed the guard, the capability refused (D-0820-7); the can_evaluate writer (Bayram 18)
  reads **422 `CRITERIA_NOT_APPLICABLE`** — past role AND capability, refused only at criteria
  applicability (the probe uses c_level_only criterion 1 so nothing can be stored on live,
  D-0826-3); hr reads 403 `ROLE_FORBIDDEN`. The expected CODES are asserted, not just statuses.
  The accepted-write half is the stand proof of §8.2 item 5.
- **A real c_level account on live in a real browser (Jemal Gulberdiyeva, 47, minted session,
  probe rows deleted after):** `/admin/users` «Найдено: 86» full roster; `/admin` 9 criteria,
  «только чтение», no Действия column; `/admin/all-evaluations` 83 rows;
  `/analytics` the true zero-state of the open campaign (0 оценок); `/admin/evaluations-matrix`
  88 rows; `/admin/final-scores` 88 rows with the weight columns; `/admin/score-calculator`
  picker «Найдено: 88 из 88». **No edit affordance on any of them** (no Добавить/Excel/
  Редактировать/Уволить on the roster, no add/cleanup/actions on criteria). Sidebar offers no
  Периоды, no Коэффициенты, no Калькуляция бонусов.
- **A real HR account (Liya Dmitriyeva, 52):** `/admin/users` «Найдено: 86», rows rendered, zero
  edit affordances; typed `/admin` → **redirected to /hr/dashboard** (BUG-013's HR half, now
  verified on live); typed `/admin/final-scores` → redirected; sidebar offers no money screens.
- **No salary field in any payload:** the artifact's compensation walk scanned the response keys
  of **all 23 non-admin 200s** recursively — **0 compensation keys**. `users[0]` keys recorded;
  `options.grades[0]` = `{code, coefficient, id}` for c_level, **`{code, id}` for hr**.
- **Campaign untouched:** `evaluation_started_at` = `2026-08-26 10:08:54.340312Z` before and
  after; tables **0/0/0/0** before and after every step (deploy AND both prover runs);
  89/3/**78** (the measured population of the day, item 2) unchanged through the window;
  catalogue/coefficients/grades md5 = `fc618757…` / `317e09e8…` / `946b30a5…` — equal to
  `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md` to the digit, by the snapshot's
  own SQL.
- **Auth Guard:** `updatedAt 2026-08-18 16:34:30.674Z`, `active=false` — unchanged, checked
  directly and enforced by the deploy script on both sides of the PUTs.

## 8.4 Hygiene

Stand torn down (container removed, `epe_roleaccess_20260826_1341` dropped, live holds
`epe_2026` + `postgres` only), `/root/epe_stand_tmp` emptied (the kept copies are the local
md5-verified pair), tunnels killed, minted probe sessions deleted (live `auth_sessions` probe
rows: 0 left). The prover writes/deletes its own `auth_sessions` rows — that table is session
state, not campaign data, and the artifact records table counts identical around every run. No
user, scope, termination, evaluation, catalogue, coefficient, grade, criteria or period row was
written on live. The pre-existing 25678 tunnel found open at session start was this session's own
first command and was closed.

**Deploy session commits:** revert `fd637c1`, merge `3b97581`, and the follow-up commit carrying
this section (hash recorded in PROGRESS.md by the closing commit).
