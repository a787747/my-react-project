# Matrix / calibration surface — Implementation Report

**Date of work:** 2026-08-19 (UTC) / 2026-08-20 (Ashgabat)  
**Status:** Completed, deployed, proof writes rolled back  
**H1 campaign:** back to draft / inactive. Launch 31 Aug.

Alexander decided the admin / c_level matrix and calibration surface is fixed **now**, not in September. Campaign-facing employee routes were not touched. The three scoring formulas in `docs/HANDOVER.md` §4 were not changed.

This report closes the display / operator defects listed in `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md` §Surface item 2, and the score-correction period-binding rule from `docs/ROUTE_GUARD_DEFERRED_2026-08-2x.md` (active period only).

---

## Verdict

The matrix and correction surface is honest for H1.

- Every matrix cell is bound to **one named period**. Default = the single `is_active=true AND status='active'` period. While H1 is draft the screen says so and shows zero rows. It does not mix Annual 2025 with H1.
- `manager_score` is selected by `evaluation_source='manager'`, not by the evaluator’s role.
- C-level stars appear only on subjects who are in scope for the **shown** period, `can_be_evaluated`, and not admin / c_level.
- «Изменить» opens a prefilled modal and saves through the existing **update-evaluation** route. A second save is no longer a 409 behind an edit label.
- Score-correction is **active**. Writes bind only to the active period. A POST while H1 is draft returns **409 `NO_ACTIVE_PERIOD`**.
- The displayed final cell averages the same stored numbers the money paths already average: manager + mid_level (if present) + c_level (if present). No new formula.

H1 can run on this surface. No functional blocker on the admin / c_level matrix.

---

## Jemal pre-check (live `epe_2026`, not edited)

Alexander said Jemal is C-level with evaluation rights. The previous C-level-direct report listed only Alexander and Bayram. That list was incomplete.

Two name matches:

| id | email | name | role | `can_evaluate` | `can_be_evaluated` | manager_id |
|---|---|---|---|---|---|---|
| **47** | jemal@sedamedical.com | **Jemal Gulberdiyeva** | **`c_level`** | **true** | false | 21 (Cem) |
| 57 | mahrijemal@sedamedical.com | Mahrijemal Annamyradova | employee | true | true | 27 |

C-level / admin writers with `can_evaluate=true` today: Alexander (admin 2), Bayram (18), **Jemal (47)**. Read-only C-level: Cem 21, Hemra 40, Mekan Yusupov 61.

Alexander was right about Jemal. The earlier report missed her. Her row was **not** changed. If that row is wrong, change it in the portal — this brief does not edit org data.

---

## Mechanism (smallest honest)

**Chosen:** GET `api/admin/evaluations-matrix` resolves one period, then every score and correction subquery uses that `period_id`.

- Default: `WHERE is_active = true AND status = 'active' LIMIT 1`.
- Optional `?period_id=` for read-only inspect (no UI selector — smallest).
- No matching period → **200** `{ success, data: [], period: null, campaign_active: false }`.
- Writes (C-level star, score-correction) only when the **shown** period is the active campaign period.

Empty-state copy names the draft: «Нет активного периода — матрица не смешивает строки.» / «H1-2026 сейчас черновик. Ячейки появятся после активации.»

AdminFinalScores, BonusCalculation, and AdminScoreCalculator consume the same matrix API. They now show one line of period context. While H1 is draft they are empty too. See Surface.

---

## Per-item evidence

### 1. One period per screen

**SQL:** `scripts/build_route_guard_deferred.py` `MATRIX_INNER_SQL` — every evaluation / score_corrections subquery has `AND e.period_id = ${periodId}` / `AND sc.period_id = ${periodId}`.  
**UI:** banner on `/admin/evaluations-matrix`; no period selector.

| State | API | UI |
|---|---|---|
| H1 draft | 200, `data=[]`, `period=null`, `campaign_active=false` | Banner names H1 as draft; «Показано: 0 из 0» |
| H1 temporarily active | 200, `period.name=H1-2026`, `campaign_active=true`, **88 rows** | Banner «Период: H1-2026 — активен» |
| `?period_id=1` (Annual 2025, closed) while H1 was active | period object is Annual 2025; Alina criterion 3 `manager_score` **null** (no 2026 manager row mixed in) | not walked in the browser (API-only inspect) |

Screenshot: `backups/2026-08-20-matrix-calibration/matrix-h1-active.png` and `matrix-h1-draft-empty.png`.

### 2. `manager_score` by `evaluation_source='manager'`

```sql
AND e.evaluation_source = 'manager'
AND e.period_id = ${periodId}
```

Proof while H1 was active: upward Alina (3) → Akmyrat (1), `evaluation_source='subordinate'`, criterion 13, stored score 9. Akmyrat’s matrix `manager_score` for criterion 13 stayed **null**. The cell is not filled from evaluator role.

`c_level_score` is likewise `evaluation_source='c_level_direct'`.

### 3. Stars only on valid subjects

`canReceiveCLevel` (`src/utils/matrixUtils.js`): shown period must be the active campaign; `is_in_scope`; `can_be_evaluated`; role not `admin` / `c_level`.

Browser DOM on the live H1-active matrix:

| Subject | Star? |
|---|---|
| Alina Naubatova (in scope, evaluable) | yes — «Добавить C-level оценку» |
| Asadbek Usmanov (actor already has a row) | yes — «Изменить C-level оценку» (scores 5 / 7, then 6 / 7) |
| Jemal Gulberdiyeva (`c_level`) | no |
| Bayram Urayev (`c_level`) | no |
| Cem Durukan (`can_be_evaluated=false`) | no |
| Hemra Ashyrov / Mekan Yusupov (read-only C-level) | no |
| Aysoltan Esenova (`is_in_scope=false`) | no |

### 4. «Изменить» is a real update (not 409)

Asadbek already had `c_level_direct` row **id=20** (Alexander → Asadbek, period 2). Modal title **«👑 Изменить C-level оценку»**, sliders prefilled 5 and 7.

Browser XHR (hooked):

```text
POST /webhook/api/update-evaluation  200
{"evaluator_id":2,"subject_id":10,"final_score":6.5,"grades":{"1":6,"10":7},
 "evaluation_source":"c_level_direct","evaluation_id":20}
```

After save: still **one** evaluation id=20; scores 6 and 7; `calculated_score=6.50`; `updated_at` moved. No new row. Not submit-evaluation. Not 409.

Screenshot: `matrix-clevel-edit-modal.png`.

`update-evaluation` itself was **not edited**. Its existing guard (actor owns the row, period not closed) is what allowed the write. Live `updatedAt` still `2026-08-19T11:52:24.730Z`.

### 5. Score-correction activated; period = ACTIVE only

**Before this brief:** route inactive (POST 404). Period subquery was `status <> 'closed' ORDER BY id DESC` — it would write into a **draft** if that draft was the newest non-closed period.

**Now:**

```sql
SELECT p.id FROM performance_db.evaluation_periods p
WHERE p.is_active = true AND p.status = 'active'
LIMIT 1
```

No row → **409 `NO_ACTIVE_PERIOD`**. Client `correction_level` is still ignored: admin / c_level → stored `c_level`; mid_level only if the actor **is** the subject’s manager’s manager.

| Proof | Result |
|---|---|
| POST correction while H1 draft (after rollback) | **409** `NO_ACTIVE_PERIOD`; `score_corrections` stayed 0 |
| POST correction while H1 active, admin → Alina criterion 3 | **200**; stored `c_level`, `period_id=2` |
| Browser: Alina cell → «Изменить» → 10→9 | `POST /webhook/api/admin/score-correction` **200**; row upserted to 9 |
| First-line manager Akmyrat (1) → Alina, H1 temporarily active | **403** `OWNERSHIP_FORBIDDEN`; corrections stayed 0 |

2026 still has **zero** manager-role skip-level users. A live `mid_level` **200** cannot be proven without changing the org. Mid_level presence in the final-cell average was proven by inserting a mid_level row in SQL for the display proof (rolled back), and by the UI tooltip / formula. The write-path rule is the same as the last brief.

Workflow `rSZcm0HDMUHLYk8W` **active**, `updatedAt=2026-08-19T20:34:42.909Z`. Other deferred reporting routes stay inactive (brief #2): all-evaluations, analytics, evaluation-details-by-user, manager-subordinates-matrix, manage-criteria, update-admin-data.

### 6. Final-cell display agrees with the money paths

**Not a new formula.** `getCriterionFinalScore` / `useFinalScoresMatrix` / `useScoreCalculation` already did:

```text
if c_level_only → c_level_score
else if no manager_score → null
else mean(manager_score, mid_level_correction?, c_level_correction?)
```

The table now uses that same function. Display rounds with `toFixed(1)`. Tooltip names every input.

**Worked example from proof rows (Alina Naubatova, criterion 3 «Личная результативность»):**

| Source | Stored |
|---|---|
| manager (Akmyrat → Alina, source=`manager`) | 6 |
| mid_level correction (SQL insert; no skip-level manager in 2026) | 8 |
| c_level correction (admin via the route) | 10, then edited in the browser to 9 |

- First render: `(6 + 8 + 10) / 3 = 8.0`. Tooltip: «Менеджер: 6, Mid-level: 8, C-level: 10, Итого: 8.0». Modal showed the same fraction under «Итоговая оценка».
- After the browser correction save: `(6 + 8 + 9) / 3 = 7.666…` → cell **7.7**. Tooltip: «Менеджер: 6, Mid-level: 8, C-level: 9, Итого: 7.7».

Those rows were rolled back. In September Alexander will read whatever real manager / mid / c_level numbers exist, averaged the same way. Confirm: **yes, mid_level counts in the number on the screen**, the same way the bonus/final-score pages already averaged it.

Screenshots: `matrix-correction-modal.png` (8.0 and `(6 + 8 + 10) / 3`), `matrix-final-cell-77.png` (7.7 after the edit).

### 7. Frontend deploy and browser pass

| Release | Path |
|---|---|
| **Current** | `20260819T203659Z` → `/var/www/epe/current` |
| Previous (kept) | `20260819T181012Z` still on disk |

Login Keychain password still **401**. Browser pass used a minted admin JWT in localStorage (same as the last C-level brief). Alexander’s **real** auth session was not deleted.

Walked as Alexander on `https://epe.sedamedical.com/admin/evaluations-matrix` with H1 temporarily active, then again after rollback:

1. Banner «H1-2026 — активен», 88 rows.
2. Stars only on valid subjects (table above).
3. Asadbek already had a C-level row → modal «Изменить», prefilled.
4. Save went to **update-evaluation 200**, not 409.
5. Alina criterion-3 cell: correction save 200 via score-correction.
6. Final cell 8.0 then 7.7, matching the average.
7. After full rollback: empty-state banner names H1 as draft. `/admin/final-scores` shows «Нет активного периода — числа не смешиваются между циклами.»

---

## What was deployed (backend)

Generator: `scripts/build_route_guard_deferred.py` (regenerates all 10 deferred JSON files).  
Deployer: `scripts/deploy_matrix_calibration.py` — **only** two live PUTs:

| Workflow | id | Change |
|---|---|---|
| `API: evaluations-matrix` | `yQNNr0i4UBFNVgMv` | stayed active; period bind + source filter + actor C-level fields; `updatedAt=2026-08-19T20:34:41.748Z`; 9 nodes |
| `API: Score Correction` | `rSZcm0HDMUHLYk8W` | **activated**; period = active only; `updatedAt=2026-08-19T20:34:42.909Z`; 9 nodes |

`EPE: Auth Guard` GET md5 **`de58de075d66a621e832aac9a2dd3d14`**, `updatedAt=2026-08-18T16:34:30.674Z` — unchanged.  
`API: Submit Evaluation` `updatedAt=2026-08-19T19:43:38.525Z` — not edited.  
Employee-facing campaign routes (login / register / reset, self-review, get-my-manager, check-*, my-profile, evaluation-history, employees) — not edited.

Static tests: `tests/matrixUtils.test.js` + `tests/routeGuardDeferred.test.js` — **24/24**.

---

## Cleanup

Proof writes (all deleted):

```text
DELETE evaluation_scores     → 6
DELETE evaluations           → 3   (ids 19 upward, 20 c_level_direct, 21 manager)
DELETE score_corrections     → 4   (ids 3–6; Alina criteria 13 and 3, c_level + mid_level)
H1 id=2                      → draft, is_active=false
```

**Sessions — both counts, as required:**

| | Count | Who |
|---|---|---|
| Before this brief | **1** | Alexander user_id=2, jti `f443cfa5-f8b8-42fd-9a41-0e527d6f24c6`, issued `2026-08-19 20:19:26+00` |
| Created by proofs | **12** | minted actors (admin / c_level / manager / employee / hr) + extra admin mints + two browser JWTs + two first-line 403 mints |
| Deleted | **12** | proof JTIs only |
| Remaining | **1** | the same Alexander session as at the start |

Alexander’s live tab was not logged out this time.

End state, live and restore-verified from `epe_2026_after.dump`:

```text
users=89
registered=1
evaluations=0
evaluation_scores=0
score_corrections=0
auth_sessions=1   (Alexander, pre-existing)
H1=id 2, draft, inactive
invite id=4 unused (43-char)
workflows=58
active_workflows=27
registered_webhooks=30
EPE: Auth Guard md5=de58de075d66a621e832aac9a2dd3d14
score-correction active=true
evaluations-matrix active=true
```

Active count 26 → 27 is the score-correction activation. Webhooks 29 → 30.

---

## Backup and archive proof

Artifacts in `backups/2026-08-20-matrix-calibration/` (gitignored) and `/root/backups/epe/2026-08-20-matrix-calibration/`. Dumps restore-tested into throwaway databases, then dropped.

| Artifact | SHA-256 / result |
|---|---|
| Pre-change `epe_2026_before.dump` | `92144783b56cbf230928a5a12c6e7b522ac48ede804976c683093cc56560a570` (73391) — restore: users=89, evals=0, corr=0, sess=1, H1 draft, registered=1 |
| Pre-change `n8n_public_before.dump` | `afc94c9dbc70097e9147a1243da94677a43314c69c5a58472846deb5aa730f07` (501738) — restore: workflows=58 active=26, webhooks=29, executions=113, insights_raw=84 |
| Final `epe_2026_after.dump` | `069e8e96fe49d4bd71da118da29956c1745f26e7f24d3df3a9772fbf0b5bb836` (73456) — restore: users=89, evals=0, corr=0, sess=1, registered=1, H1 draft |
| Final `n8n_public_after.dump` | `2463ca1e7c488883cda6b0e096415ac870e6d398f25df1e8916cfa2704d1627e` (505007) — restore: workflows=58 active=27, webhooks=30, executions=113, insights_raw=112 |
| 2025 fingerprint before / after | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e`, **unchanged=true** |

`epe_2026` custom-format SHA moved because proof inserts advanced sequences even after row delete, and dump-header timestamps differ. Row counts after cleanup match the required end state. Alexander’s session is still there on purpose.

n8n public SHA moved because:

1. evaluations-matrix **PUT** (graph + `updatedAt`).
2. score-correction **PUT + activate** (flag + webhook row; active 26→27, webhooks 29→30).
3. `insights_raw` 84→112 during proofs. `execution_entity` stayed **113**.

No schema change. 2025 archive not written.

---

## Boundaries held

- Auth Guard bytes unchanged (same GET md5).
- Employee-facing campaign routes not edited. Submit-evaluation not edited.
- Other deferred reporting routes still inactive.
- Stored formulas and write-path numbers not changed. Display now averages the same stored numbers the money paths already used.
- 2025 archive read-only; fingerprint unchanged.
- Proof writes fully rolled back. Alexander’s real session kept.

---

## Surface for Alexander — do not resolve silently

### 1. After H1 is closed this screen goes empty

The matrix (and Итоговые баллы / Калькуляция бонусов / Калькуляция баллов) bind to the **active** period. While H1 is draft they already show the empty-state. The day H1 is closed and nothing else is active, the same empty-state returns.

The API already accepts `?period_id=` so a selector can be added later without another backend pass. Until then, September calibration on this screen requires either leaving H1 **active** during calibration, or adding the selector.

**Recommendation:** leave H1 active through calibration week, then close it. Add the selector only if you need to inspect a closed period on this screen. Cost of not deciding: the matrix goes blank the morning someone closes H1.

### 2. Exact final-cell average (confirm the September number)

For a non-C-level criterion:

```text
mean(manager_score, mid_level_correction if present, c_level_correction if present)
```

C-level-only criteria still show `c_level_score` as-is. No manager_score → the cell stays empty (corrections alone do not invent a final). Display is one decimal (`8.0`, `7.7`).

Worked example from the (rolled-back) proof: Alina, criterion 3, manager 6 + mid 8 + c_level 10 → **8.0**. After the browser edit, c_level 9 → **7.7**.

This is which stored numbers the screen averages, not a fourth formula. The three intentional formulas in HANDOVER §4 are untouched.

### 3. Jemal’s row

Jemal Gulberdiyeva **is** `c_level` with `can_evaluate=true`. The previous report omitted her. Change the row in the portal if that is wrong.

### 4. `mid_level` 200 still unproven on a live manager user

The write rule is in place (manager’s manager only). First-line → 403, proven this session. 2026 has no skip-level manager to receive 200. Same gap as the deferred-guard brief.
