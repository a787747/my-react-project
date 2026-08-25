# Catalogue wording — five level-6 norm labels removed on live (2026-08-25)

Brief: write exactly five text fields in `performance_db.criteria` through
`API: Manage Criteria Admin V7` (not raw SQL); every other field of every row
byte-identical before and after; dated dump first; verbatim before/after
snapshots as the next H1-2026 catalogue version; D-0825-2 recorded.

**Outcome in one line: the five strings are live, character-for-character; the
other 103 text fields and every non-text column are unchanged; H1 stays
`active` and not started.** Execution record: §4. Proof:
`backups/2026-08-25-catalogue-fix2/catalogue_fix2_h1_proof.json` (gitignored).

---

## 1. What was checked before the first write

| Check | Found |
|---|---|
| Working tree | clean on `origin/main` `6ca603ea23b284f10d2380e82e6325a08e6dec66` |
| H1 (id 2) | `status=active`, `is_active=true`, `evaluation_started_at` NULL — catalogue still writable (D-0822-1) |
| Four data tables | `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` all **0** |
| `criteria` columns (live `information_schema`) | 22 columns, **no `updated_at`** |
| Live write route | same as fix 1: `POST /manage-criteria {action:'save'}`. Freeze keys on `evaluation_started_at`, not activation. |
| Live catalogue vs last after (`H1-2026_catalogue_after_20260825T062601Z.md`) | **equal** — body 24 052 bytes, 0 field diffs |

Criterion 3 used the brief's primary tail («но инициативу сверх этого проявляет редко»), not the alternative. Criterion 10 keeps straight `"` around «всё в порядке». Criterion 12's brief text also replaces «пинка» with «напоминаний».

---

## 2. Dump

`pg_dump -U admin --no-owner --no-acl -Fc epe_2026` **before** the first write.

| Copy | Path | Bytes | After the run |
|---|---|---|---|
| VPS | `/root/epe_stand_tmp/epe_2026_20260825_072229.dump` (`chmod 600`, dir `700`) | 80 676 | **removed**; `/root/epe_stand_tmp` empty |
| Local | `backups/2026-08-25-catalogue-fix2/epe_2026_20260825_072229.dump` | 80 676 | kept (gitignored) |
| `/tmp` | none | — | no `epe_2026*.dump` |

---

## 3. How the five fields were written

Same mechanism as `scripts/apply_catalogue_fix_h1.py`: the admin route cannot
PATCH a single column, so each save SETs the whole writable set. Five POSTs,
one per affected criterion, in brief order 3 → 4 → 8 → 10 → 12. Each row was
read from live immediately before its POST; only `level_6_desc` was replaced.

- Auth: one marked `auth_sessions` row for admin id 2,
  jti `caf10000-2026-0825-8000-000000000002`, deleted in `finally`.
  Count **12 → 12**, 0 probe rows remaining.
- No raw SQL write to `criteria`. The session INSERT/DELETE is the one
  permitted live write outside the five fields.
- The route did not 409 `EVALUATION_STARTED` and did not 422. It did not
  normalise «», ё, dashes or spaces — stored strings equal
  `docs/briefs/catalogue_fix2_h1_texts.json`.

`performance_db.criteria` has no `updated_at`. Write times below are
`clock_timestamp()` after each 200.

---

## 4. Acceptance — compared values

### 4.1 Before / after snapshots (the H1-2026 catalogue version)

| Snapshot | SELECT (server UTC) | File |
|---|---|---|
| Before | `2026-08-25T07:22:39.878985Z` | `docs/catalogue/H1-2026_catalogue_before_20260825T072239Z.md` |
| After | `2026-08-25T07:23:16.687383Z` | `docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md` |

Before **equals** `H1-2026_catalogue_after_20260825T062601Z.md` (0 diffs). The
owner had not edited the catalogue between fix 1 and this write.

### 4.2 The five fields

| Criterion | Column | `equals_brief_text` | `updated_at` | `written_at_utc` | Route status |
|---|---|---|---|---|---|
| 3 | level_6_desc | true | n/a (no column) | 2026-08-25T07:22:51.238481Z | 200 |
| 4 | level_6_desc | true | n/a | 2026-08-25T07:22:56.439355Z | 200 |
| 8 | level_6_desc | true | n/a | 2026-08-25T07:23:02.089734Z | 200 |
| 10 | level_6_desc | true | n/a | 2026-08-25T07:23:07.848718Z | 200 |
| 12 | level_6_desc | true | n/a | 2026-08-25T07:23:13.511540Z | 200 |

All five `equals_brief_text = true`.

### 4.3 Everything else identical

9 rows × (title + description + `level_1`…`level_10`) = 108 text fields.
5 changed; **103 identical**. Non-text columns checked per row: `id`,
`category`, `weight` (as `numeric(5,2)` text), `is_active`,
`target_audience`, `selfassesment`, `c_level_only`, `for_manager`,
`score_definitions`, `level_0_desc` — **90 values, all identical**.
Unexpected changes: **none**. Criteria 13 and 14 were not written. Titles,
audiences, flags, weights, coefficients and the criteria count are unchanged.

### 4.4 Forms' read route

`GET https://epe.sedamedical.com/webhook/api/criteria` as the same admin
probe session: **200**. New `level_6_desc` for criteria **3, 4, 8, 10, 12**
all `equals_brief_text = true`. Independent SELECT after teardown returned
the same five strings. No caching layer served the old labels.

### 4.5 Live after everything

| Thing | After |
|---|---|
| H1 id 2 | `active`, `is_active=true`, `evaluation_started_at` NULL |
| Data tables | 0 / 0 / 0 / 0 |
| `auth_sessions` | 12 (restored; probe jti gone) |
| `/root/epe_stand_tmp` | empty |
| Workflows / frontend / mail / coefficients / stand | untouched |

---

## 5. Rollback

Restore the before snapshot through the **same** route, not raw SQL:

1. For each of criteria 3, 4, 8, 10, 12: read the live row, replace
   `level_6_desc` with the string from
   `docs/catalogue/H1-2026_catalogue_before_20260825T072239Z.md`,
   `POST /manage-criteria {action:'save'}`.
2. If the route is frozen (H1 started → 409 `EVALUATION_STARTED`), stop —
   recovery is then the dated dump
   `backups/2026-08-25-catalogue-fix2/epe_2026_20260825_072229.dump`
   via `/root/backups/epe/verify-restore.sh`, which needs the owner's word.

---

## 6. Riders

- `DECISIONS.md` **D-0825-2** (verbatim as briefed; supersedes the H2 item
  «унификация ярлыка (Норма)» from CRITERIA_HR_REVIEW).
- `docs/HANDOVER.md` §3 catalogue bullet: one sentence (latest snapshot
  file name). §10 counters not edited.
- `PROGRESS.md` entry.

---

## 7. Surfaced, not resolved

1. **`src/pages/GuidePreview.jsx` line 22** still quotes
   «Качественный профи (Нижняя граница нормы). Надежный сотрудник.»
   Local DEV-only fixture (`import.meta.env.DEV`); not in the production
   route table or the live bundle `20260825T065554Z`. Brief forbade a
   frontend change.
2. Historical documents (`docs/CRITERIA_HR_REVIEW_2026-08-2x.md`,
   `docs/USER_FACING_COPY_2026-08-2x.md`, the fix-1 texts JSON, previous
   catalogue snapshots) still contain the removed labels. They are not UI.
3. Nothing else from the surface list fired: the before snapshot matched
   the last after; the tree was clean at start; no field outside the five
   changed; the route did not 409/422 or rewrite quotes.

---

## 8. Closing table — documents to re-upload (md5)

| File | md5 |
|---|---|
| `docs/CATALOGUE_FIX2_H1_2026-08-25.md` | `e6cc5f096cbe57b6e48091a88097303f` (body above this table) |
| `docs/catalogue/H1-2026_catalogue_before_20260825T072239Z.md` | `14e2e23d7ca8aa2045e80a2ecb16087f` |
| `docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md` | `e5306c2483ebf19a6e0944f78327b43f` |
| `docs/briefs/catalogue_fix2_h1_texts.json` | `16c02d7fc6adfb88d7b8f28117898fa9` |
| `scripts/apply_catalogue_fix2_h1.py` | `1da4e321629aee0a8942ac7daff947ac` |
| `DECISIONS.md` | `4e1c75bafaaf237b3b783fdeb1a82e68` |
| `PROGRESS.md` | `685c5c554394b762668e66e151706b7d` |
| `docs/HANDOVER.md` | `2e8382c677206ac2c0c62fe2807b1f89` |
