# TALK — «Поговорить с руководством» (2026-09-07)

**Verdict:** wave 1 is live and open. It is a separate, structured management
listening channel with four guarded routes, employee/admin pages and three
campaign entry points. It has no period binding and no path into evaluation
scores or period close.

The owner explicitly authorised opening on 2026-09-06, one day before the
concept timetable. Live frontend after the copy revision:
**`20260906T135041Z`**. Workflow:
**`API: Management Talk`**, id **`pALSY08dYjNmHB64`**, active, updated
**`2026-09-06T13:40:13.535Z`**.

## 1. What was built

- Approved contract: `CONVERSATION_CHANNEL_CONCEPT.md`.
- Migration 019: `management_talk_waves`, `management_talk_topics`,
  `management_talk_responses`, `management_talk_counterparts`.
- One response per `(wave_id, responder_id)`, enforced by the primary key;
  save uses `ON CONFLICT ... DO UPDATE`.
- Every responder and every named counterpart is an integer FK to
  `performance_db.users(id)`. There is no `period_id`, score-like column or FK
  to any campaign table.
- Four routes: `GET api/talk/form`, `POST api/talk/save`,
  `POST api/talk/withdraw`, `GET api/talk/list`.
- Employee page `/talk`; owner page `/admin/talk`; sidebar, Welcome/team banner
  and post-evaluation prompts.
- The employee success state is exactly **«Ответ получен»**. No employee
  scheduling state machine was invented.
- Deadline copy is rendered from `waves.closes_at`; the stand response returned
  `deadline_text=10 сентября` for
  `2026-09-10T23:59:59.999999+05:00`.

## 2. Frozen Auth Guard

The live `EPE: Auth Guard` graph was read before building. It consumes only
`authorization`, `required_roles`, `required_capability` and the passed request.
It does not inspect or register webhook paths. A new TALK path therefore needs
no guard change.

Canonical `updatedAt` remained
**`2026-08-18T16:34:30.674Z`** before and after deployment. The guard was not
written.

## 3. Approved counterpart selector

Before activation the owner signed off this exact live list:

1. Alexander Petrosov (admin, id 2)
2. Bayram Urayev (c_level, id 18)
3. Cem Durukan (c_level, id 21)
4. Hemra Ashyrov (c_level, id 40)
5. Jemal Gulberdiyeva (c_level, id 47)
6. Mekan Yusupov (c_level, id 61)

The server uses this ID allowlist and also rechecks current employment and role.
Role membership alone cannot add a future person. For topic 10 the author's
current manager is removed/refused. Topics 9, 11 and 12 deliberately do not
inherit that rule (D-TALK-11).

## 4. Acceptance — expected versus found

1. **Reader role matrix.** Expected admin 200; c_level/hr/manager/employee 403;
   unauthenticated 401 `TOKEN_MISSING`. Found exactly those six results on the
   stand and again on live.
2. **Answer lifecycle.** Expected employed 200; second save still one row;
   withdraw zero; terminated refused. Stand found `200 → row 1`,
   `200 → same count 1`, `withdraw 200 → row 0`; terminated returned
   `403 ACTOR_TERMINATED`.
3. **Topic 10.** A crafted request by Aysha Suvhanova (15) naming her current
   manager Jemal Gulberdiyeva (47) returned
   `422 TALK_OWN_MANAGER_FORBIDDEN`; response rows for actor 15 remained zero.
   The same counterpart was accepted for topics 9, 11 and 12.
4. **Wave close by clock.** The proof inserted a second stand-only wave with
   `opens_at=clock_timestamp()-2 days` and
   `closes_at=clock_timestamp()-1 day`. The server clock was later than
   `closes_at`; save returned `409 TALK_WAVE_CLOSED`. Wave 1 timestamps before
   and after were identical:
   `2026-09-06 11:52:17.384442Z` /
   `2026-09-10 18:59:59.999999Z` on the final stand. No open/closed flag was
   set and no Wave 1 timestamp was altered.
5. **Isolation.**
   - Schema: zero `period_id`, zero score/weight/coefficient/rating/rank/count
     columns, zero FK in either direction between TALK and
     `evaluations`, `evaluation_scores`, `score_corrections`,
     `period_results`.
   - The live `API: Manage Periods` graph contains zero references matching
     `management_talk|api/talk|talk-2026`.
   - Sixteen existing payload families were walked on the stand: employees,
     profile, history, check-evaluated, get-my-manager, criteria,
     evaluations-matrix, all-evaluations, analytics, admin roster,
     coefficients, HR status, periods, annual roll-up, details-by-user and
     employee events. All returned 200 and none carried
     `talk-2026-wave-1`. The marker was present on both new TALK reads, so the
     proof was non-vacuous.
6. **Campaign before/after.** The first session read was
   **177 / 572 / 0 / 0** (`evaluations` / `evaluation_scores` /
   `score_corrections` / `period_results`). Immediately before live writes it
   was **177 / 572 / 0 / 0**; final read was **177 / 572 / 0 / 0**.
   The brief expected movement, but none occurred during the measured window;
   it would be false to report employee activity that was not observed.
   `evaluation_started_at` stayed exactly
   **`2026-08-26 10:08:54.340312Z`**.

## 5. Admin live smoke

The owner authorised one live smoke on the admin's own account. The script
refused to start unless admin had no existing response.

- Before save: **0**
- After `POST /api/talk/save`: **1**
- `GET /api/talk/form` read-back: **`all_good`**
- After `POST /api/talk/withdraw`: **0**

The final live TALK count was **0 responses / 0 counterpart rows**. Short-lived
auth sessions were deleted in `finally`. No test user was created.

## 6. Admin denominator

The stand reader recorded all three answer categories as 1/1/1 and returned:

- employed: 86
- registered but unanswered: 78
- never registered: 5

Those two missing populations are separate fields and cards. The twelve topic
rows always render in contract order, including zeroes.

## 7. Validation and deployment evidence

- Static suite after the copy revision: **474/474 passed** (8 TALK tests).
- Production build passed; live deploy build passed again.
- New-file lint: zero errors. Existing changed files retain six pre-existing
  lint findings in `Sidebar.jsx` and `ManagerEvaluation.jsx`; this brief did not
  widen into that refactor.
- Independent code review found no critical issue. Fixed before deployment:
  teardown quoting, approved-ID allowlist, credential temp cleanup, misleading
  graph-builder code, role field leakage and save-response counterpart count.
- Final fresh stand: **23/23 passed**.
- Migration applied twice on live: first result `1 wave / 12 topics / 0
  responses / 0 counterparts`; second application inserted zero rows.
- Existing generated workflows unchanged: **20**.
- Workflow totals after activation: **62 total / 37 active**.
- Frontend CAS:
  `releases/20260827T124349Z → releases/20260906T134020Z`;
  copy-only follow-up:
  `releases/20260906T134020Z → releases/20260906T135041Z`.
- Public `/talk` and `/admin/talk` both returned HTTP 200 (SPA entry).
  Deployed assets contain the TALK title; the literal
  `Ответить можно до 10 сентября` is absent, while `deadline_text` is present.
- A real interactive browser walkthrough was not run; route behaviour was
  exercised over HTTP on the stand and live, and the production bundle was
  built and inspected.

Anchor dumps immediately before the first live write, copied locally with
matching md5:

- `epe_2026`: `b19ea9cec626d9b0ccfa3fc26e9123b7`
- n8n public schema: `aa95ee3e67499ac1ed676e04cdba2b1c`

They are evidence, not a rollback mechanism. Restoring either would erase live
employee work.

## 8. Rollback and teardown

Lossless rollback after employees begin answering:

1. deactivate `pALSY08dYjNmHB64`;
2. flip the frontend symlink back to `releases/20260827T124349Z`;
3. leave TALK tables and their real responses intact.

Do not restore a dump and do not drop TALK tables after a real response exists.

The final stand database/container and tunnel were removed. VPS staging was
emptied. Remaining project databases were `epe_2026,postgres`; no live
container was restarted.

## 9. Surfaced, not resolved

- **BUG-081:** no admin scheduling-state names, transitions or audit contract
  were decided. Wave 1 therefore provides structured reads only; the owner
  tracks contact routing manually.
- D-TALK-9 closing letter is a management action after the wave, before H1
  close.
- Structured TALK retention is decided with peer recognition at Annual 2026
  close.

## 10. Commits

- Implementation: `f1472b9` — TALK surface, migration, workflow source,
  frontend, tests and proof tooling.
- Live export/deploy guard: `dddc32e`.
- Employee copy revision: `a6291ef`.

They are followed by documentation record commits containing this report.

## 11. Copy revision (D-TALK-14, 2026-09-06)

The employee explanation was replaced verbatim with the owner's new six
paragraphs. The old acute-project introduction and four dash-prefixed assurance
paragraphs are absent from source and the deployed bundle. The gate question,
answer choices, topics, API and stored data did not change.

The deadline still renders from `wave.deadline_text`; the deployed bundle
contains the new first paragraph and does not contain either the old first
paragraph or the hard-coded string `Ответить можно до 10 сентября`.

Validation: focused TALK **8/8**, full suite **474/474**, lint zero, production
build passed. Campaign tables stayed **177/572/0/0**, TALK responses stayed
**0**, and `evaluation_started_at` was unchanged. Copy commit: `a6291ef`.
