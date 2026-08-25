# Catalogue wording — 20 fields written on live before the H1 start (2026-08-25)

Brief: write exactly 20 text fields in `performance_db.criteria` through
`API: Manage Criteria Admin V7` (not raw SQL); every other field of every row
byte-identical before and after; dated dump first; verbatim before/after
snapshots as the H1-2026 catalogue version; D-0825-1 recorded.

**Outcome in one line: the 20 strings are live, character-for-character; the
other 88 text fields and every non-text column are unchanged; H1 stays
`active` and not started.** Execution record: §4. Proof:
`backups/2026-08-25-catalogue-fix/catalogue_fix_h1_proof.json` (gitignored).

---

## 1. What was checked before the first write

| Check | Found |
|---|---|
| H1 (id 2) | `status=active`, `is_active=true`, `evaluation_started_at` NULL — catalogue still writable (D-0822-1) |
| Four data tables | `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` all **0** |
| `criteria` columns (live `information_schema`) | 22 columns, **no `updated_at`** |
| Live write route | `API: Manage Criteria Admin V7` `55BHbXWIS6igHHBT`, `updatedAt=2026-08-22 06:38:08.633+00`, active. Freeze keys on `evaluation_started_at`, not activation. UPDATE SET-list is title, description, audience, flags, `level_0`…`level_10`. Weight, category, `score_definitions` are not in the SET list. |
| Forms' read route | `API: Get Criteria With Levels` `KKlGLEYMlXlbYUjb`, `GET /api/criteria`, `updatedAt=2026-08-22 06:37:56.521+00`, active |
| Live catalogue vs review §8 (2026-08-24 19:22:58Z) | **equal** — 0 text diffs, 0 meta diffs, all 9 rows |

HANDOVER header still says H1 is `draft` / launch paused (measured 2026-08-24 17:14 UTC). Live at this write: H1 is **active**, not started. That header was not rewritten — the brief limited the HANDOVER edit to one sentence on the §3 catalogue bullet.

---

## 2. Dump

`pg_dump -U admin --no-owner --no-acl -Fc epe_2026` **before** the first write.

| Copy | Path | Bytes | After the run |
|---|---|---|---|
| VPS | `/root/epe_stand_tmp/epe_2026_20260825_062455.dump` (`chmod 600`, dir `700`) | 80 654 | **removed**; `/root/epe_stand_tmp` empty |
| Local | `backups/2026-08-25-catalogue-fix/epe_2026_20260825_062455.dump` | 80 654 | kept (gitignored) |
| `/tmp` | none | — | no `epe_2026*.dump` |

---

## 3. How the 20 fields were written

The admin route cannot PATCH a single column: a save always SETs the whole
writable set. The only safe way through that route is to read the live row
immediately before each save and send that row with only the brief's fields
replaced. Eight POSTs, one per affected criterion, in brief order
13 → 3 → 4 → 8 → 2 → 10 → 12 → 14.

- Auth: one marked `auth_sessions` row for admin id 2,
  jti `caf10000-2026-0825-8000-000000000001`, deleted in `finally`.
  Count **12 → 12**, 0 probe rows remaining.
- No raw SQL write to `criteria`. The session INSERT/DELETE is the one
  permitted live write outside the 20 fields.
- The route did not 409 `EVALUATION_STARTED` and did not 422. It did not
  normalise «», ё, dashes or spaces — stored strings equal the brief file
  `docs/briefs/catalogue_fix_h1_texts.json`.

`performance_db.criteria` has no `updated_at`. The acceptance table's
`updated_at` column is therefore **n/a**; the clock immediately after each
200 is recorded as `written_at_utc`.

---

## 4. Acceptance — compared values

### 4.1 Before / after snapshots (the H1-2026 catalogue version)

| Snapshot | SELECT (server UTC) | File |
|---|---|---|
| Before | `2026-08-25T06:25:07.961842Z` | `docs/catalogue/H1-2026_catalogue_before_20260825T062507Z.md` |
| After | `2026-08-25T06:26:01.657653Z` | `docs/catalogue/H1-2026_catalogue_after_20260825T062601Z.md` |

Before **equals** the HR-review appendix of 2026-08-24 19:22:58Z. The owner
had not edited the catalogue between the review and this write.

### 4.2 The 20 fields

| Criterion | Column | `equals_brief_text` | `updated_at` | `written_at_utc` | Route status |
|---|---|---|---|---|---|
| 13 | description | true | n/a (no column) | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_4_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_5_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_6_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_7_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_8_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_9_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 13 | level_10_desc | true | n/a | 2026-08-25T06:25:20.278081Z | 200 |
| 3 | description | true | n/a | 2026-08-25T06:25:25.602319Z | 200 |
| 3 | level_7_desc | true | n/a | 2026-08-25T06:25:25.602319Z | 200 |
| 3 | level_10_desc | true | n/a | 2026-08-25T06:25:25.602319Z | 200 |
| 4 | description | true | n/a | 2026-08-25T06:25:30.759824Z | 200 |
| 4 | level_6_desc | true | n/a | 2026-08-25T06:25:30.759824Z | 200 |
| 4 | level_10_desc | true | n/a | 2026-08-25T06:25:30.759824Z | 200 |
| 8 | description | true | n/a | 2026-08-25T06:25:35.992735Z | 200 |
| 8 | level_10_desc | true | n/a | 2026-08-25T06:25:35.992735Z | 200 |
| 2 | level_10_desc | true | n/a | 2026-08-25T06:25:41.239004Z | 200 |
| 10 | level_10_desc | true | n/a | 2026-08-25T06:25:47.045538Z | 200 |
| 12 | level_8_desc | true | n/a | 2026-08-25T06:25:52.846021Z | 200 |
| 14 | level_2_desc | true | n/a | 2026-08-25T06:25:58.436754Z | 200 |

All twenty `equals_brief_text = true`.

### 4.3 Everything else identical

9 rows × (title + description + `level_1`…`level_10`) = 108 text fields.
20 changed; **88 identical**. Non-text columns checked per row: `id`,
`category`, `weight` (as `numeric(5,2)` text), `is_active`,
`target_audience`, `selfassesment`, `c_level_only`, `for_manager`,
`score_definitions`, `level_0_desc` — **90 values, all identical**.
Unexpected changes: **none**. Criterion 1 was not written. The 13 deferred
language fields were not written. Weights, audiences, flags, coefficients
and the criteria count are unchanged (coefficients were not touched by any
route).

### 4.4 Forms' read route

`GET https://epe.sedamedical.com/webhook/api/criteria` as the same admin
probe session: **200**. New texts for criteria **3, 13, 14** all
`equals_brief_text = true`. No caching layer served the old strings.

### 4.5 Live after everything

| Thing | After |
|---|---|
| H1 id 2 | `active`, `is_active=true`, `evaluation_started_at` NULL |
| Data tables | 0 / 0 / 0 / 0 |
| `auth_sessions` | 12 (restored; probe jti gone) |
| `/root/epe_stand_tmp` | empty |
| Workflows / frontend / mail / coefficients | untouched |

---

## 5. Rollback

Restore the before snapshot through the **same** route, not raw SQL:

1. For each of criteria 13, 3, 4, 8, 2, 10, 12, 14: read the live row,
   replace the fields listed in §4.2 with the strings from
   `docs/catalogue/H1-2026_catalogue_before_20260825T062507Z.md`,
   `POST /manage-criteria {action:'save'}`.
2. If the route is frozen (H1 started → 409 `EVALUATION_STARTED`), stop —
   recovery is then the dated dump
   `backups/2026-08-25-catalogue-fix/epe_2026_20260825_062455.dump`
   via `/root/backups/epe/verify-restore.sh`, which needs the owner's word.

---

## 6. Riders

- `DECISIONS.md` **D-0825-1** (verbatim as briefed; supersedes D-0820-19 for
  wording only — `c_level_only` level-text stripping is unchanged).
- `docs/HANDOVER.md` §3 catalogue bullet: one sentence. §10 counters not
  edited.
- `PROGRESS.md` entry.

---

## 7. Surfaced, not resolved

1. **`criteria.updated_at` does not exist.** Acceptance asked for that
   column after each write. Live `information_schema` has 22 columns and
   no timestamp. Write times above are `clock_timestamp()` after each 200.
2. **HANDOVER header is stale** (still «H1 is `draft` / launch paused»,
   2026-08-24 17:14 UTC). Live H1 has been `active` / not-started since at
   least the HR review at 19:22:58Z. Out of this brief's HANDOVER scope.
3. Nothing else from the surface list fired: the before snapshot matched
   the review; the route did not 409/422 or rewrite quotes; no field
   outside the 20 changed; `GET /api/criteria` served the new texts.

---

## 8. Closing table — documents to re-upload (md5)

| File | md5 |
|---|---|
| `docs/CATALOGUE_FIX_H1_2026-08-25.md` | `bc145dac0b536c2deec7febd4e17fa14` (body above this table) |
| `docs/catalogue/H1-2026_catalogue_before_20260825T062507Z.md` | `889fbc4cc160db1f05d0f55b3cd9b573` |
| `docs/catalogue/H1-2026_catalogue_after_20260825T062601Z.md` | `515c68aa49e4e83b87acb56a5ef3fe9f` |
| `docs/briefs/catalogue_fix_h1_texts.json` | `a95cea5037ea68ce5914ded247d4f6bd` |
| `scripts/apply_catalogue_fix_h1.py` | `60862951ee833c3971b3f73474fcd221` |
| `DECISIONS.md` | `06a13360635720460be9cf59e5ae71ae` |
| `PROGRESS.md` | `70f43cbcf37280fd53172ac8e8e9d6cf` |
| `docs/HANDOVER.md` | `ea8771395ad858de1b6ae632fd7b06e3` |
