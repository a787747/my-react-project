# Periods: rename, hierarchy (containers), close-time result persistence, annual roll-up

**Date of work:** 2026-08-21
**Origin of proof:** isolated n8n `epe-hier-n8n` on VPS loopback `:25679` (same pinned image digest) against throwaway DB `epe_hier_20260821_0549` (restored from the live pre-migration dump + `scripts/seed_hierarchy_throwaway.sql`). Live `epe_2026` received **only** migration 013 (new table; parent column already existed). No period or data rows were written to live.
**Frontend release:** `20260821T060049Z` (`/var/www/epe/current`). Previous stamps `20260820T154749Z`, `20260820T165040Z` remain on disk.
**H1:** live period id=2 stays `draft` / `is_active=false`, 87/89 in scope. Nothing was activated or closed on live.

---

## Verdict

All four outcomes are live and proven on the throwaway stand: rename, containers (non-activatable, 422), close-time result persistence (atomic, immutable, idempotent), and the annual roll-up view for admin + c_level. The acceptance matrix passed in full, including the explicit anti-zero-fill assertion (half-year employee shows 8.0, not 4.0). Tests 213/213. Alexander can now create Annual 2026 and attach H1 in `/admin/periods` — that walk-through is the designated UX acceptance.

---

## What was built

### 1. Rename (`POST api/periods/rename`, admin)

Pencil control on every row of `/admin/periods` → modal → new name. Unique-name conflict → 409 «Период с таким названием уже существует». Renaming any period — draft, active, closed, container — is safe.

**Nothing keys on a period name anywhere.** Verified by sweep: every query, guard, and matrix/report SQL binds to `period_id` / `is_active` / `status`; the frontend branches on `id`/`status`/`is_active` and uses `name`/`period_name` for display only; the analytics trend groups by `ep.id`. The only name-keyed artifacts are one-time seed migrations 010/012 (`WHERE name = 'Annual 2025' / 'H1-2026'`) — already applied, not runtime, but re-running 010 after a rename would re-insert a period under the old name; noted for the archive, no action needed (migrations are not re-run in operations). Proof also runtime-shaped: after renaming closed P1, the matrix (`?period_id=`), stored results, and the roll-up were byte-identical except the label.

### 2. Containers (`parent_period_id`, `POST api/periods/reparent`)

A container is a period with children — a **reporting construct, nothing more** (D-0821-1):

- **Never activatable**: no «Активировать» control on container rows, and the API refuses with **422 `CONTAINER_NOT_ACTIVATABLE`** — checked before the switch and re-asserted inside the UPDATE, so the at-most-one-active invariant holds even under a race. Deactivation of the current period is now gated on the target actually being activatable (previously a failed activation could still deactivate the current period — fixed in passing).
- **A period that has evaluations can never become a container** → 422 `PARENT_HAS_EVALUATIONS`.
- Child dates must lie within the parent's → 422 `CHILD_DATES_OUTSIDE_PARENT`; no nesting (parent must be top-level, a container cannot become a child) → 422 `PARENT_IS_CHILD` / `CHILD_IS_CONTAINER`; the active period cannot become a parent → 422 `PARENT_ACTIVE`.
- **Reparenting is safe and free**: attach/detach any leaf (any status, including closed) via the folder-tree control; proof showed detach → re-attach leaves every stored number identical.
- Containers cannot be closed (422 `CONTAINER_NOT_CLOSABLE`) — their children close.

UX (my call): creation and attachment both live in `/admin/periods`. The create modal gained a period-type select (Полугодовой/Годовой) and an optional parent select; each leaf row has a «привязать к контейнеру / отвязать» modal listing eligible parents (top-level, no evaluations, not active). Children render indented under their container; the container row shows a «Контейнер» badge, child count, and `—` for scope. Alexander's flow: «Создать период» → Annual 2026 (annual, 2026-01-01…2026-12-31) → on the H1 row, folder-tree icon → choose Annual 2026 → save.

### 3. Close-time result persistence (`POST api/periods/close`, D-0821-2)

Closing a **leaf, active** period computes and stores per participant into the new `performance_db.period_results` (migration 013):

| Column | Meaning |
|---|---|
| `rating_manager / rating_upward / rating_c_level_direct` | AVG of `calculated_score` per source, the 1–10 ratings |
| `rating_self` | the self-review's plain rating (`calculated_score`, not the weighted value) |
| `final_rating` | **per-person final = mean over criterion final cells**, each cell exactly as the matrix computes it: `mean(manager, mid?, c_level?)`, `c_level_only` → `c_level_score` (D-0820-12). The per-person aggregate — mean over that person's non-empty cells, `c_level_only` cells included when scored — **reproduces an existing surface**: it is the «ИТОГОВЫЙ БАЛЛ» column of the evaluations-matrix Excel export (`src/utils/excelExport.js:228-229,248`: same `getCriterionFinalScore` per cell, same non-null filter, same population). Corrected 2026-08-21: this document previously called the definition this brief's own call and claimed the matrix had no per-person total to copy — it does |
| `bonus_index` | formula #3 exactly as Итоговые баллы / Калькуляция бонусов compute it: Σ(cell × score-coefficient(round(clamp(cell))) × weight) × grade coefficient — **no division by sum of weights** (HANDOVER §4), including the client's `parseFloat(weight) \|\| 1.0` quirk |
| `is_in_scope` | participant flag frozen at close |
| `has_data` | **explicit no-data marker**: `false` = in scope but never evaluated. DB CHECKs make it impossible for a no-data or out-of-scope row to carry any number — a missing rating can never be read back as a zero |

Mechanics: the close flow loads a dataset that mirrors the matrix SQL subquery-for-subquery (same predicates, same latest-by-`updated_at`, same correction lookups), computes the numbers in a Code node that replicates the client pipeline verbatim, then writes **one atomic SQL statement**: a `target` CTE re-asserts (active + leaf + no existing results + evaluation count unchanged since compute, `FOR UPDATE`), the INSERT and the `status='closed', is_active=false` UPDATE both gate on it. Any race → zero rows changed → 409. **Second close: 200 `already_closed`, zero rows** (proven by md5 fingerprint + row count). No route anywhere UPDATEs or DELETEs `period_results` (asserted by test over all 17 generated workflows).

**Invariant held:** reproducing a closed period's numbers requires no live join — the roll-up reads `period_results` only (test-asserted: the roll-up SQL references none of evaluations/scores/corrections/coefficients/criteria), and editing `criteria.weight` and `grades.coefficient` in the throwaway after close changed neither the stored rows nor the annual view.

H1's real close remains a September action; nothing was closed on live.

### 4. Annual roll-up (`GET api/periods/annual-rollup?container_id=`, D-0821-3)

Placement (my call): **its own screen** — `/admin/annual-rollup`, «Годовые итоги» in the Аналитика sidebar group. Итоговые баллы stays a live-period screen; mixing frozen and live numbers on one screen invited exactly the confusion this brief kills.

- Audience: `ReportingRoute` (admin + c_level); API guard `admin`+`c_level` — HR 403, employees 403 (proven). Subjects see nothing new; this week's sealing untouched (no subject-facing route was modified).
- Per person × child: persisted final (with its index beneath), or «вне охвата» / «нет данных» / «период не закрыт» / «нет сохранённых результатов» (the last for a hypothetical closed-without-results child, e.g. Annual 2025 if ever attached).
- **Annual rating = server-computed AVG of persisted finals over in-scope periods with data only** — out-of-scope excluded, no zero-fill; «нет данных» excluded from the mean but visible. **Annual index = SUM of persisted indices.** The client renders, never recomputes.
- Unclosed children contribute nothing; a container with zero closed children renders an honest empty state naming the children and their statuses — never live mixed numbers.
- Person set: anyone in scope of at least one closed child; `role='admin'` excluded like every other reporting surface.

---

## Proof (throwaway stand, 38 recorded checks → `backups/2026-08-21-periods-hierarchy/api_proof.json`)

Container `Hier Annual-T` → children `Hier P1` (attached at creation) + `Hier P2` (attached via the reparent flow — the same path Alexander will use). P1 activated → evaluations seeded → closed via the API; then P2 the same. 96 result rows per close (93 in scope, 91 no-data — the restored live users, honestly marked).

| Acceptance | Result |
|---|---|
| A in scope both, finals 6.0 / 8.0 | stored `6.0000`/`8.0000`; annual rating **7.0**; annual index **104.70 = 36.30 + 68.40** (i1+i2) ✅ |
| B in scope P2 only, final 8.0 | annual **8.0 — NOT 4.0** (explicit assertion); P1 cell «вне охвата» (`in_scope=false`, no numbers); index **68.40** = its single term ✅ |
| C in scope P1, never evaluated | stored `in_scope=true, has_data=false`, all numbers NULL; «нет данных» in the view; excluded from mean (annual = «—»); visible ✅ |
| Ratings per source | A: manager 6.00 + self 5.00 persisted; manager 1102: upward 7.00 persisted ✅ |
| Server/client cross-check | stored final and index equal the client pipeline (matrix API + score-coefficients + grades, replicated formula-exact incl. JS rounding) to < 0.005, for both periods ✅ |
| Weight/grade edit after close | `criteria.weight` +3 and grade coefficient +0.7 → roll-up JSON and stored fingerprint byte-identical ✅ |
| Second close | 200 `already_closed`, `results_stored: 0`, fingerprint and row count unchanged ✅ |
| Container activate / close | 422 `CONTAINER_NOT_ACTIVATABLE` / 422 `CONTAINER_NOT_CLOSABLE`; no Activate button rendered ✅ |
| Container rules | dates-outside-parent 422; nesting 422; parent-with-evaluations 422; closed-period activation 422 ✅ |
| Rename | 200 + label everywhere; duplicate → 409; zero effect on numbers ✅ |
| Reparent | detach → container shows 1 child; re-attach → identical numbers ✅ |
| Audience | admin 200, c_level 200, hr 403, employee 403 ✅ |
| Rendered check (vite `:5299` → stand) | `/admin/periods`: container badge, no Activate, indented closed children «результаты сохранены», H1 row unchanged with Активировать; `/admin/annual-rollup`: A `6.00/8.00 → 7.00 / 104,70`, B `вне охвата/8.00 → 8.00 / 68,40`, C `нет данных → — / —` (DOM-extracted) ✅ |

Static tests: `npm test` → **213 pass / 0 fail** (192 prior incl. this week's sealing/regression suite + 21 new: container-not-activatable, `period_results` insert-only across all workflows, no-zero-fill/in-scope-only roll-up SQL, formula-parity markers, and the close-compute Code node executed with fixtures — no-data → NULLs never zeros, corrections averaging, coefficient-by-rounded-level).

## Live deploy

1. **Migration 013** — dated dump first: `backups/2026-08-21-periods-hierarchy/epe_2026_pre013_20260821_0549.dump` (73 814 bytes, also on host). Applied: `parent_period_id` already existed (skipped — it shipped with the original schema import), `period_results` created empty. **Every existing table's row count proven unchanged** (`live_counts_before/after_013.txt`, diff clean); second run of the migration: all no-ops.
2. **`API: Manage Periods` PUT** (`M9ljMDdO1mIl8m1h`) via `scripts/deploy_periods_hierarchy.py`: guard frozen before/after, activation preserved (`active=true`), live graph verified node-for-node. `updatedAt` `2026-08-20T15:46:55.640Z` → **`2026-08-21T06:00:08.687Z`**. 23 → 61 nodes, 3 → 7 webhooks. Top-level export refreshed from live.
3. **Frontend** `./scripts/deploy_epe_frontend.sh` → **`20260821T060049Z`**; bundle carries `AdminAnnualRollup` and `/webhook` base.
4. **Live after deploy:** H1 `draft,false`, scope 87/89; evaluations/scores/corrections/period_results **0/0/0/0**; Auth Guard `updatedAt=2026-08-18T16:34:30.674Z`, `active=false`; workflows 58 total / 33 active; registered webhooks 37 → **41**; new routes answer 401 (guard) at the public origin; 2025 archive 73/234/644/3 by SELECT only.

## Constraints held

- 2025 archive: SELECT only. Live `epe_2026`: schema migration only — zero period/data rows written (0/0/0/0 above).
- `EPE: Auth Guard` untouched (`updatedAt` re-read after the final probe).
- No mail (D-0820-8). H1 not activated, not closed, scope untouched.
- Throwaway: container `epe-hier-n8n` removed after the proof; DB `epe_hier_20260821_0549` kept for audit (drop when convenient — it is not production).

## Leftovers / observations

- **Stale top-level export:** `n8n_workflows/API_ evaluations-matrix.json` is the pre-guard, pre-period-binding version (live runs the generated one from `build_route_guard_deferred.py`). It misled this brief's stand for one cycle. BUG-028 (Low, open); the generated `route_guard_deferred/evaluations-matrix.json` is the truth, and the stand script now generates instead of copying.
- `/admin/periods` renders rename/reparent controls for c_level/HR viewers too; the API is admin-only (403 via the known interceptor message). Same pattern as the pre-existing Activate button — cosmetic.
- Errors on the periods page surface via `alert(handleApiError(...))` — functional, not pretty; consistent with the page's existing style.
- `period_results` immutability is product-level (no mutating route exists, test-enforced); raw SQL can still write — same trust model as every other table.
- The roll-up excludes `role='admin'` subjects (matrix precedent). Alexander is therefore not a row in Годовые итоги; his results are not evaluated anyway.
- `.claude/launch.json` (local vite launcher for the stand) is committed as tooling; harmless.
