# HIRE_DATE_AND_SCOPE_TOGGLE — editable hire date and per-period scope (2026-08-26)

**Brief:** HIRE_DATE_AND_SCOPE_TOGGLE. **Decisions:** D-0826-4 / D-0826-5.

**Outcome:** the admin employee card now edits `join_date` (date → empty → date),
shows and changes participation per evaluation period, recomputes open
date-derived scope with a visible named outcome for every period, refuses any
move out after evaluation data exists, and records actor/time. The automatic
rule is now the final three calendar months: for H1 ending 2026-06-30, a hire on
2026-03-31 is in and 2026-04-01 is out. Proven on two restored copies of one
live dump, in a real browser with the stand gate pressed, then deployed with
zero live person/scope drift. The live second gate was never pressed.

## 1. Baseline re-read, not assumed

Before editing, live read **89 users / 3 terminated / 80 in H1**, H1
`active/true`, `evaluation_started_at NULL` on all three periods, and
`evaluations / evaluation_scores / score_corrections / period_results =
0 / 0 / 0 / 0`. Four H1 rows carried `excluded_by_admin`.

The proposed rule was evaluated against the live people and H1 dates before any
write: **zero disagreements**. The only people hired after the 31-March boundary
who were not terminated were already out. Applying the rule to H1 therefore
changed nothing, as required.

The generators were also compared to live before editing: **32 identical,
0 changed**; the two known generator-only workflows remained absent.

## 2. What the repository contradicted

The brief says one existing table records both termination and scope. There was
no such table:

- `employment_events` records termination/reinstatement;
- `period_scope_events` records period exclusion/inclusion.

Migration 017 does not rewrite or copy either history. It additively creates
`employee_card_events` for old→new card fields and exposes one admin-only reader,
`GET /api/admin/employee-events?user_id=`, which unions all three event families
with actor and time. Calling it without `user_id` is refused to prevent an
unbounded company-wide audit response.

## 3. Card save: no silent role/category defaults

`admin/save-user` remains an admin-only full-row operation, but an existing row
now has two protections:

1. the client reloads `/api/admin-users-data` immediately before POST, takes all
   writable fields from that fresh row, then overlays the form;
2. the server refuses `INCOMPLETE_USER_ROW` if any full-row field is absent.

`role || employee` and `work_category || general` can therefore no longer demote
a manager or move a project employee because a field disappeared from the
request. A stand partial-body probe returned 422 and the full row remained
byte-identical.

Card writes and scope recompute are one SQL statement. If a date change would
exclude a person after evaluation data exists, the whole card save is refused;
the message explicitly says that all other fields also remained unchanged.
Every actual card change is stored in `employee_card_events.changes` as
`{"field":{"old":...,"new":...}}`, with actor from the guard and database time.

## 4. Scope precedence and rule

Migration 017 adds nullable `evaluation_period_participants.scope_override`:

- `included_by_admin` — manually in;
- `excluded_by_admin` — manually out;
- NULL — default/date-derived and eligible for recompute.

Recompute touches only non-closed rows with no override and reason NULL or a
date-derived reason (`join_date_missing`, legacy `hired_after_period_end`,
`insufficient_tenure`). It never touches `terminated`, `excluded_by_admin`,
either manual override, or a closed period.

Manual off writes `is_in_scope=false`, reason and override
`excluded_by_admin`. Manual on reverses admin/date exclusions, including
`join_date_missing`, and writes `included_by_admin`; a later date correction
cannot silently reverse that manual inclusion. Termination remains refused.

The old confirmation escape on exclusion is removed. If any received, self,
given evaluation or correction exists in the period, off returns 409
`HAS_EVALUATIONS`, lists all four counts and changes nothing.

The shared cutoff expression in period creation and card recompute is the day
before the final three calendar months:

```sql
(date_trunc('month', end_date)::date
 - interval '2 months' - interval '1 day')::date
```

For 2026-06-30 it is 2026-03-31; strictly later is out. NULL is out with
`join_date_missing`.

## 5. Stand proof

`scripts/setup_hiredate_scope_throwaway.sh` restored one fresh live dump into
control and treatment, applied migration 017 to both, loaded HEAD workflows in
control and the working tree in treatment, and pressed the stand gate through
the established fixture. Evaluation fingerprints were identical before the
test.

`backups/2026-08-26-hiredate-scope/proof.json`: **32/32**.

Measured sequence:

- NULL date → `2026-04-09`: H1 `excluded_by_date`, Annual 2026
  `unchanged_in_scope`, Annual 2025 `closed_untouched`;
- date → empty: H1 stayed out with `join_date_missing`, Annual 2026 moved out;
- empty → `2025-03-01`: H1 and Annual 2026 moved in;
- manual off/on on a no-data employee both returned 200; on persisted
  `scope_override=included_by_admin`;
- off on MY LateStart returned 409 even with the legacy
  `confirm_existing_evaluations=true` flag, counts **2 received / 1 self /
  1 given / 0 corrections**, row unchanged;
- editing MY Excluded to an early date returned `manual_preserved`; H1 stayed
  `excluded_by_admin`;
- every card/scope action was readable afterwards with actor 1601 and time;
- evaluation rows remained byte-identical.

### Money proof

MY Newcomer (1607) began date-derived out of H1 but carried one stand-only
manager score on criterion 3. Treatment corrected the date and brought them in;
control did not. Both copies closed through their own real
`POST /api/periods/close`.

- Same frozen user set on both sides.
- Every frozen cell of every other person was byte-identical.
- The only moved row was 1607.
- Control: `is_in_scope=false`, `has_data=false`, all numbers NULL.
- Treatment: manager/final rating 6; bonus index
  `6 × 1.10 × 3.00 × 0.30 = 5.9400`.
- Pool difference: exactly `5.9400`.

The bonus index remained the §4 weighted sum **without** a denominator. No
formula, criterion, coefficient, grade or catalogue value was changed.

### Browser

Real browser against the treatment stand:

- card showed admin-only «Дата приёма», named H1/Annual periods and the event
  journal;
- after `2026-04-09`, the visible «Что произошло с охватом» block named:
  Annual 2025 closed/unchanged, H1 excluded by the three-month rule, Annual 2026
  still in;
- the H1 switch for an evaluated person stayed on and the red refusal printed
  the 2/1/1/0 counts and «Ничего не изменено»;
- journal rows showed source/event, timestamp and actor.

The stand databases and both stand containers were removed; afterwards only
`epe_2026,postgres` remained. No non-stand container was restarted.

## 6. Live deployment

Rollback anchor before the first live write:

- timestamp: `20260826T085029Z`;
- VPS staging: `/root/epe_stand_tmp/`, mode 600, removed after final verification;
- Mac: `~/EPE_ROLLBACK/2026-08-26-hiredate-scope/`, outside the repository;
- `epe_2026` md5: `886c761c81f82f32aa327d7a49af19cf`;
- n8n public schema md5: `57b873cb0a8ce2f209c5d6e2ea65fd23`;
- both hashes equal on VPS and Mac.

Migration 017 was applied twice; the second run emitted only expected
already-exists notices.

Five workflows were PUT through the n8n API and remained active:

- `API: Admin Save User (GUI Mode)` — 08:52:42Z, final actor-id guard correction
  at 09:04:31Z;
- `API: Manage Periods` — 08:52:44Z;
- `API: Admin Get Users Data` — 08:52:46Z;
- `API: Manage Period Scope` — 08:52:48Z;
- `API: Get Employees (Smart Role Based)` — 08:52:50Z.

Auth Guard stayed frozen at `2026-08-18T16:34:30.674Z`, inactive.

Frontend release: **`20260826T085259Z`**, previous
`20260826T051630Z`. The deploy lock, compare-and-swap and both bundle safety
gates passed.

## 7. Live after

`backups/2026-08-26-hiredate-scope/live_verify.json`: **19/19**.

- 89 users, 3 terminated, 80 in H1.
- H1 `active/true`; `evaluation_started_at NULL` on all three periods.
- campaign tables 0/0/0/0.
- `employee_card_events=0`; existing `period_scope_events=4`.
- every user cell compared to the anchor: **zero changed**;
- every pre-existing participant cell compared to the anchor: **zero changed**;
  new `scope_override` NULL on all rows;
- criteria / level coefficients / grades md5 exactly
  `fc618757… / 317e09e8… / 946b30a5…`, equal to
  `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`;
- 60 workflows / 35 active / 22 archived / 49 webhooks;
- extensions: `plpgsql` only;
- partial save probe 422, wrote no card event;
- unified event reader 200 with user id, 422 without it, 401 without auth;
- probe session deleted; verification restore dropped; databases again
  `epe_2026,postgres`.

The verifier initially found two test defects, not product defects: Python
Framework had no CA file configured for urllib, and the grade fingerprint
omitted `description` from the documented projection. Both were corrected; the
full pass was rerun from a fresh restore and ended 19/19.

## 8. Review findings

Post-build review found seven items. Fixed before deployment:

- duplicate toast + inline card feedback;
- refusal text now states the entire card transaction was rolled back;
- a new arbitrary manual exclusion no longer lies «hired after 31 March»;
  legacy four H1 marks keep the owner's existing text;
- employee-event reader now requires `user_id`;
- invalid guard actor id fails explicitly;
- period-create conflict path clears a stale override.

Not fixed: **BUG-076**, the roster's correlated period-list query scales as
users × periods. It is a low performance finding at 89 × 3, not a correctness
or H1 blocker.

`npm test`: **412/412** (three final pins added for guard actor identity,
whole-card rollback copy and required event `user_id`). Production build passed. Changed-file lint passed;
the repository-wide existing React lint baseline remains (including
`ManagerEvaluation.jsx:79` and the context fast-refresh warning) and was not
expanded into this functional brief.

## 9. Frozen-column correction

`join_date` leaves the global frozen-column set under D-0826-4. Future drift
checks must still compare it, but a change made through the audited admin card
is intended owner activity, not an incident. Unrelated operations — hierarchy,
termination, classification — still must not move it. HANDOVER and the two
recent reports that printed the old global list carry this correction.

## 10. Files and records

- migration 017: card events + durable two-direction manual override;
- route generators and five refreshed workflow exports;
- employee card, hooks, context, period-state copy and API constants;
- setup/seed/proof/deploy/live-verify scripts;
- `tests/hireDateScopeToggle.test.js` plus updated contract pins;
- D-0826-4 / D-0826-5 verbatim; BUG-076; HANDOVER; PROGRESS.

No mail was sent. No catalogue, coefficient, grade, criteria or period row was
written. No live employee, participant, evaluation or result value moved. The
second gate was never called.

**Commit:** pending; recorded after the implementation commit.
