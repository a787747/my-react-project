\set ON_ERROR_STOP on

-- PRELAUNCH_BATCH_NIGHT — fixtures the money walkthrough needs on top of
-- scripts/seed_midyear_throwaway.sql (ids 1601–1611), which is applied first
-- and is left exactly as it is.
--
-- Everything here exists because an acceptance line asks for it:
--
--   1612 MY Partial — project participant with SIX applicable manager-path
--        criteria, of which the manager scored only THREE. This is the
--        «at least one partial evaluation» case. Grade S3 (1.40) so the
--        arithmetic cannot pass on a 1.0 fallback.
--   1613 MY NoHireDate — in scope, join_date NULL. The BUG-066 shape: the row
--        that used to be indistinguishable from ten years' service on
--        /admin/users. Under 1601, no evaluations, so no money moves.
--   1614 MY Excluded — EMPLOYED, reports to 1602, out of period-2 scope with
--        reason `excluded_by_admin` and a hire date of 2026-04-09. This is the
--        person the manager must SEE, marked and not evaluable, and the person
--        whose Welcome must carry the owner's late-hire text.
--   1615 MY GoneQuiet — reports to 1602 and is TERMINATED. Must stay HIDDEN on
--        the same screen, from the same query, in the same run. Without this
--        row «the excluded are shown» and «the terminated are hidden» cannot be
--        demonstrated to be two different behaviours of one join.
--
-- Plus, on the existing fixtures:
--   * a c_level_direct evaluation on 1605, so a project participant carries
--     all four channels and the two heaviest criteria (1 and 10) are non-null
--     on somebody whose manager score is also non-null;
--   * a mid_level and a c_level score CORRECTION on 1605's criterion 3, so the
--     «corrections reach this screen» claim is measurable rather than argued.
--
-- The guard below refuses any database that is not a night stand.

DO $$
BEGIN
  IF current_database() !~ '^epe_mid_night_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

-- Idempotent teardown of anything a previous run left behind.
DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id BETWEEN 1612 AND 1615 OR evaluator_id BETWEEN 1612 AND 1615
);
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1612 AND 1615 OR evaluator_id BETWEEN 1612 AND 1615;
DELETE FROM performance_db.score_corrections
WHERE subject_id BETWEEN 1601 AND 1615 OR evaluator_id BETWEEN 1601 AND 1615;
DELETE FROM performance_db.period_scope_events WHERE user_id BETWEEN 1612 AND 1615;
DELETE FROM performance_db.employment_events WHERE user_id BETWEEN 1612 AND 1615;
DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1612 AND 1615;
DELETE FROM performance_db.period_results WHERE user_id BETWEEN 1612 AND 1615;
DELETE FROM performance_db.evaluation_period_participants WHERE user_id BETWEEN 1612 AND 1615;
DELETE FROM performance_db.users WHERE id BETWEEN 1612 AND 1615;
-- The c_level_direct evaluation this file adds on 1605.
DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id = 1605 AND evaluation_source = 'c_level_direct'
);
DELETE FROM performance_db.evaluations
WHERE subject_id = 1605 AND evaluation_source = 'c_level_direct';

-- ── Actors ───────────────────────────────────────────────────────────────────

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date, password_hash
)
VALUES
  (1612, 'MY Partial', 'my.partial@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S3'),
   1602, 'Night stand partial evaluation', true, 'project', false, true, true, 0,
   DATE '2025-03-01', NULL),

  (1613, 'MY NoHireDate', 'my.nohiredate@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1601, 'Night stand missing hire date', false, 'general', false, true, true, 0,
   NULL, NULL),

  -- EMPLOYED and out of scope: the person the manager must see, marked.
  (1614, 'MY Excluded', 'my.excluded@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1602, 'Night stand excluded by admin', false, 'general', false, true, true, 0,
   DATE '2026-04-09',
   '$scrypt$N=16384,r=8,p=1$_Q0Hj0SEDB7Mr_OZQFXN1A$BNu8flwitnEMJJovoZ4cCLriQY0Ya6zFYT6qIQGjh45QZBfY5gy-TVU4-mfnIsoK_t0_fKvsbe_Nvc0nkiw_Tg'),

  -- TERMINATED, same manager as 1614. Must stay hidden on the same screen.
  (1615, 'MY GoneQuiet', 'my.gonequiet@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1602, 'Night stand terminated', false, 'general', false, true, true, 0,
   DATE '2024-05-01', NULL);

UPDATE performance_db.users
SET terminated_at = TIMESTAMPTZ '2026-08-20 09:00:00+00',
    termination_date = DATE '2026-08-20'
WHERE id = 1615;

-- ── Period membership ───────────────────────────────────────────────────────

INSERT INTO performance_db.evaluation_period_participants
  (period_id, user_id, is_in_scope, exclusion_reason)
VALUES
  (2, 1612, true,  NULL),
  (2, 1613, true,  NULL),
  (2, 1614, false, 'excluded_by_admin'),
  (2, 1615, false, 'terminated'),
  (5, 1612, true,  NULL),
  (5, 1613, true,  NULL),
  -- 1614 stays in the annual container: an exclusion from one half-year does
  -- not take a person out of the year (D-0825-10).
  (5, 1614, true,  NULL),
  (5, 1615, false, 'terminated');

-- ── The PARTIAL evaluation ──────────────────────────────────────────────────
-- 1612 is a project participant, so the manager path applies criteria
-- 3, 4, 8, 12, 13, 14 — six. The manager scored 3, 8 and 13 only. The other
-- three must render as «ещё не оценено», NOT as zero, and must contribute
-- nothing to the index.
--
-- calculated_score is the plain mean of the rows below it (formula 1):
--   (6 + 9 + 4) / 3 = 6.3333
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1612, 1602, 2, 6.3333, 'manager', false, 'completed',
          'stand: manager scored three of six criteria', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,6),(8,9),(13,4)) AS v(c,s);

-- ── A fourth channel on 1605, so one person carries all four ────────────────
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1605, 1606, 2, 7.5000, 'c_level_direct', false, 'completed',
          'stand: c_level on stayer B', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,8),(10,7)) AS v(c,s);

-- ── Corrections on 1605, criterion 3 ────────────────────────────────────────
-- The manager gave 9. mid_level says 5, c_level says 4. The screen must show
-- the MEAN of the three — (9 + 5 + 4) / 3 = 6.0 — not the manager's 9, and it
-- must mark the cell as corrected.
INSERT INTO performance_db.score_corrections
  (subject_id, criteria_id, correction_level, correction_score, evaluator_id, period_id)
VALUES
  (1605, 3, 'mid_level', 5, 1601, 2),
  (1605, 3, 'c_level',   4, 1606, 2);

COMMIT;
