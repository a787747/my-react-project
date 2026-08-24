# Employees period meta — 2026-08-24

One workflow changed, additively, through its builder: `GET /api/employees`
(`API: Get Employees (Smart Role Based)`) now carries `period_name`,
`period_start_date`, `period_end_date` for the current period at the top level
of the payload — the feed the Welcome period notice (release 20260824T182054Z)
was already written to consume. Frontend untouched: `extractPeriodMeta` accepts
exactly these key names (verified before the change, pinned in tests). Launch
stays paused; live is campaign-inert after everything (§4).

**Checked this session:** the builder (`EMPLOYEES_SQL` / `EMPLOYEES_FORMAT` in
`scripts/build_auth_workflows.py`); `src/utils/periodNotice.js` +
`src/context/TaskStatusContext.jsx` (consumer key names); throwaway stand
`epe-empmeta-n8n` / `epe_empmeta_20260824_1840` (old-vs-new payload diff, 3
states × 3 actors); local frontend against the stand in a real browser (three
states); live PUT + `check_live_drift.py` before and after; live admin GET via
the marked-session probe; `npm test` before/after.

---

## 1. The change

Three additive edits, all inside the two code nodes of one workflow. Generated
via the builder — no hand-edited export (BUG-028/045 hygiene).

| Node | Edit |
|---|---|
| `Build Identity-Bound Query` | `current_period` CTE gains `name`, `to_char(start_date, 'YYYY-MM-DD') AS start_date_text`, `to_char(end_date, 'YYYY-MM-DD') AS end_date_text` |
| same | top-level SELECT gains `(SELECT name FROM current_period) AS period_name`, `(SELECT start_date_text …) AS period_start_date`, `(SELECT end_date_text …) AS period_end_date` |
| `Format Response` | body gains `period_name: row.period_name \|\| null`, `period_start_date: …`, `period_end_date: …` after `current_period_status` |

Dates are serialised **inside SQL** (`to_char`), never as a `date` column
through the n8n Postgres node — that node returns `date` as a UTC JS `Date`
and `String(v).slice(0, 10)` yields the previous calendar day in
Europe/Moscow (BUG-031). Pinned in `tests/upwardChannelSeal.test.js`.

"Current period" is unchanged: the single active leaf (BUG-043), which covers
both the preparation window and the started campaign; a draft or a container is
never current, so the three keys are `null` exactly when `current_period_id`
is. Guard unchanged: `required_roles: []` — any authenticated session.
`GET /api/periods` stays `admin`/`hr`/`c_level`; nothing was opened.

Consumer check that kept the frontend untouched: `extractPeriodMeta` reads
`period_name` and accepts `period_start_date` / `period_end_date` in its date
key lists (`src/utils/periodNotice.js`), and `TaskStatusContext` feeds it the
payload root. No field-name alignment was needed; no `src/` file changed.

## 2. Stand proof — old vs new payload, 3 states × 3 actors

Walkthrough pattern: stand `epe-empmeta-n8n` (same pinned image digest as
live) on VPS loopback :25679, DB `epe_empmeta_20260824_1840` restored from a
dated dump of live (80 600 bytes, local copy
`backups/2026-08-24-empmeta/epe_2026_empmeta_20260824_1840.dump`; restore
verified: 89 users, 9 active criteria). Fixture actors 1301–1310 (walkthrough
shape) plus **1311 WT Employee O** — an out-of-scope direct report of manager
1302 (`is_in_scope=false`). Live was never written.

`scripts/prove_empmeta.py` (`backups/2026-08-24-empmeta/empmeta_proof.json`):
both workflow versions imported on the stand (new `A9QJvuLOxEFXnLnc` as set up,
old `Eo3TG2n5KIgMaxlB` generated from the pre-brief builder), each **verified
node-for-node via n8n export before its phase** (`import:workflow` assigns new
ids; a stand accumulates same-named duplicates — the definition, not the name,
was trusted). Per phase: draft → real `POST api/periods/activate` (200) → real
`POST api/periods/start-evaluation` (200) as fixture admin 1301, with a SQL
rewind to draft between phases and at the end.

All **9 cells** (3 states × employee 1303 / manager 1302 / out-of-scope 1311):

| Check | Result |
|---|---|
| `added_keys` | exactly `period_end_date, period_name, period_start_date` — all 9 cells |
| `removed_keys` | `[]` — all 9 cells |
| new payload minus the three keys == old payload (deep equality, `data` rows included) | **true — all 9 cells** |

Values, from the recorded payloads (employee actor shown; all three actors
identical on the meta keys):

**draft** — three keys `null`; `campaign_active=false`,
`period_in_preparation=false`, `current_period_id=null`,
`actor_is_in_scope=null`, `data=[]`:

```json
{"success": true, "actor_user_id": 1303, "campaign_active": false,
 "period_in_preparation": false, "current_period_id": null,
 "current_period_status": null, "period_name": null,
 "period_start_date": null, "period_end_date": null,
 "actor_is_in_scope": null, "data": []}
```

**activated-not-started** — H1 name and the exact dates (not the previous
day), `campaign_active=false`, `period_in_preparation=true`:

```json
{"success": true, "actor_user_id": 1303, "campaign_active": false,
 "period_in_preparation": true, "current_period_id": 2,
 "current_period_status": "active", "period_name": "H1-2026",
 "period_start_date": "2026-01-01", "period_end_date": "2026-06-30",
 "actor_is_in_scope": true, "data": []}
```

**started** — same three values with `campaign_active=true` (manager actor
shown; `data` reduced to ids):

```json
{"success": true, "actor_user_id": 1302, "campaign_active": true,
 "period_in_preparation": false, "current_period_id": 2,
 "current_period_status": "active", "period_name": "H1-2026",
 "period_start_date": "2026-01-01", "period_end_date": "2026-06-30",
 "actor_is_in_scope": true, "data": [1303, 1308, 1304, 1309]}
```

Also compared: out-of-scope 1311 gets `actor_is_in_scope=false` with the same
meta values; the manager's `data` is exactly the four in-scope directs — 1311
never appears; stand H1 fixture row `H1-2026|2026-01-01|2026-06-30`; final
stand state back to `draft|false|null`. Zero failures in the artifact.

## 3. Browser check — local frontend against the stand

`vite` :5299 (`epe-hier-vite` launcher, `VITE_DEV_API_PROXY` →
127.0.0.1:25679 through the tunnel), real login as
`wt.employee.g@sedamedical.com` through the actual auth workflow. States set
on the stand DB, page reloaded between them.

| Stand H1 state | Rendered (read from the page, not mocked) |
|---|---|
| activated-not-started | title **«Промежуточная оценка: H1-2026 (1 января 2026 — 30 июня 2026)»**; scope **«Сейчас оценивается работа за период с 1 января 2026 по 30 июня 2026. …то, что произошло после 30 июня 2026…»**; state line «Период открыт для подготовки. Задачи самооценки и оценки появятся в день старта, названный в письме о запуске.» |
| started | same title and scope; state line «Оценка идёт — ваши задачи ниже.»; task cards present («МОИ ЗАДАЧИ», «Активный период оценки») |
| draft | title and scope **absent** (no «Промежуточная оценка», no dates on the page); body + «Период оценки сейчас не открыт.» |

Russian date form comes from `formatPeriodDateRu` on the served
`YYYY-MM-DD` strings — `src/` still contains neither `H1-2026` nor
`2026-06-30` (pinned test unchanged).

## 4. Live deploy

`scripts/deploy_employees_period_meta.py` (contract of `deploy_reclass.py`:
guard-freeze check before and after, PUT preserves activation, live graph
re-read node-for-node, tracked export refreshed behind
`assert_not_a_generator_input`).

| | |
|---|---|
| Dry-run | `changed=true`, `active_before=true`, `updatedAt_before=2026-08-24T06:10:17.952Z` (matches the documented live value) |
| PUT | workflow `bKB4Sb46yWoq1tSV`, activation `true → true`, **`updatedAt_after=2026-08-24T18:49:55.486Z`**, webhook `GET api/employees` only |
| Auth Guard | `2026-08-18T16:34:30.674Z` before, during and after — frozen value intact |
| Drift before PUT | `changed = ["API: Get Employees (Smart Role Based)"]` — exactly the intended delta |
| Drift after PUT | **30 identical / 0 changed** / 2 absent (the two long-standing absentees, warned by name) |
| Export refreshed | `n8n_workflows/API_ Get Employees (Smart Role Based).json` rewritten from live |

Live probe after the PUT (`scripts/probe_live_empmeta.py`,
`backups/2026-08-24-empmeta/live_probe.json`; one marked 30-min session row
for admin id 2, deleted before exit — the established probe technique; state
fingerprint identical before/after, `auth_sessions` 11 → 11):

```json
{"success": true, "actor_user_id": 2, "campaign_active": false,
 "period_in_preparation": false, "current_period_id": null,
 "current_period_status": null, "period_name": null,
 "period_start_date": null, "period_end_date": null,
 "actor_is_in_scope": null, "data": []}
```

Key set is exactly the previous eight plus the three new keys; the three are
`null` — H1 (id 2) is `draft|false|null` and the four data tables are
`0/0/0/0` (SELECT after everything). No activation, no start, no mail.

## 5. Tests

| | Count |
|---|---|
| `npm test` before | **312 / 312** |
| `npm test` after | **313 / 313** |

+1: `extractPeriodMeta` reads the exact served keys
(`tests/welcomePeriodNotice.test.js`). Rewritten to the new truth:
`tests/upwardChannelSeal.test.js` employees test now asserts the three keys,
the SQL `to_char` serialisation, no `.slice(0, 10)`, and that the payload
still carries no scores/comments/upward content; the no-period mock in
`welcomePeriodNotice.test.js` gained the three null keys.

## 6. Teardown

Stand container removed; `epe_empmeta_20260824_1840` dropped (`epe_2026` is
the only `epe_%` database left); `/root/epe_stand_tmp` emptied; both tunnels
killed. Dump kept only as the local dated copy under
`backups/2026-08-24-empmeta/`.

## 7. Riders

- **BUG-054 filed (low):** live workflow named `API: My Evaluation History
  (Received)` while its SQL is given-only — correct behaviour, misleading
  name; a future "fix" toward the name would open the sealed upward channel.
- **BUG-055 filed (low):** `Profile.jsx:221/316` renders «Оценен
  подчиненным:» against `evaluator_name` the server nulls on upward rows.
- bugs.md statistics **18 open / 37 closed** (recounted from status rows).
- The proof and probe scripts initially expected psql's `t/f` for a
  `||`-concatenated boolean; Postgres casts it as `true/false`. Two
  expectation strings fixed; the compared live/stand values were correct
  throughout.

## 8. Surfaced, not resolved

1. Nothing in this brief's scope: no existing key changed value in any of the
   9 diff cells, no consumer broke on the new keys (the only consumer reads
   them by name and ignored their absence before), no date shifted a day, one
   workflow sufficed.
2. Still open from the Welcome brief and untouched here: criterion 14 live
   level curve ≠ approved curve; TeamView BUG-012.

## 9. Closing table — files to re-upload (md5)

| File | md5 |
|---|---|
| `docs/EMPLOYEES_PERIOD_META_2026-08-2x.md` | `ec105d4b43fae3baf244dc60e1fd4d69` (body above this table) |
| `bugs.md` | `1a7af2c6692a4292b6af6332724d9dd9` |
| `PROGRESS.md` | `e85c783e76ed8475fedb9e3a2ed4bd7c` |
| `docs/HANDOVER.md` | `2022ddc62021ca1310c9834454e43dbb` |
| `n8n_workflows/auth_core/protected-employees.json` | `5502fd2916ebb5adf05e5c18f0dc8853` |
| `n8n_workflows/API_ Get Employees (Smart Role Based).json` | `1eed9e8ac206df19a38e359b3a5e0859` |
