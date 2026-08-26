\set ON_ERROR_STOP on

-- CLEVEL_AVERAGING — the second C-level evaluator (D-0826-1).
--
-- Applied on top of seed_midyear_throwaway.sql (ids 1601–1611) and
-- seed_night_extra.sql (1612–1615), both left exactly as they are. This file
-- adds ONE person and NOTHING else, so that the difference between round 1 and
-- round 2 of the proof is a single evaluation and can be attributed.
--
--   1616 MY CLevel Two — a SECOND person holding c_level_direct rights, the
--        shape live has three of (Alexander id 2, Bayram id 18, Jemal id 47).
--        role c_level, can_evaluate = true, can_be_evaluated = false, so they
--        can never become a money row themselves. In scope of period 2 like
--        the other C-level fixture (1606), and therefore frozen at close as
--        «in scope, no data» — identical on both sides of the comparison.
--
-- The second EVALUATION is deliberately not here: it is applied between the
-- two rounds by prove_clevel_close.py, so round 1 and round 2 differ by that
-- one row and by nothing else.
--
--   round 2 adds: 1616 → 1605 c_level_direct, criterion 1 = 4, criterion 10 = 9
--   already present: 1606 → 1605 c_level_direct, criterion 1 = 8, criterion 10 = 7
--
--   criterion 1  «Стратегическая значимость роли», weight 5.00: 8 and 4 → 6
--   criterion 10 «Оценка C-Level и соответствие культуре», weight 1.60: 7 and 9 → 8
--
-- 1616's row carries a strictly LATER updated_at than 1606's, so the old
-- reader (ORDER BY e.updated_at DESC LIMIT 1) is deterministic and the report
-- can state which of the two scores it picked instead of saying «4 or 8».

DO $$
BEGIN
  IF current_database() !~ '^epe_mid_night_clv_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

-- Idempotent teardown.
DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id = 1616 OR evaluator_id = 1616
);
DELETE FROM performance_db.evaluations WHERE subject_id = 1616 OR evaluator_id = 1616;
DELETE FROM performance_db.auth_sessions WHERE user_id = 1616;
DELETE FROM performance_db.period_results WHERE user_id = 1616;
DELETE FROM performance_db.evaluation_period_participants WHERE user_id = 1616;
DELETE FROM performance_db.users WHERE id = 1616;

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date, password_hash
)
VALUES
  (1616, 'MY CLevel Two', 'my.clevel.two@sedamedical.com', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C2'),
   NULL, 'Second c_level_direct writer', false, 'general', false, true, false, 0,
   DATE '2025-01-01', NULL);

INSERT INTO performance_db.evaluation_period_participants
  (period_id, user_id, is_in_scope, exclusion_reason)
VALUES
  (2, 1616, true, NULL),
  (5, 1616, true, NULL);

COMMIT;
