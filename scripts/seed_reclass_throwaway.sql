\set ON_ERROR_STOP on

-- Fixture actors for the live-reclassification acceptance (brief 2026-08-24,
-- D-0822-3). Users 1301-1310; auth_sessions with fixed jtis so the proof
-- script can mint matching JWTs against the stand's JWT_SIGNING_SECRET.
--
-- Shape the acceptance needs:
--   1303 G  — general employee whose switch to project must REOPEN the
--             manager task and take the additive path for criteria 8/13;
--   1304 P  — project employee evaluated on the full applicable set whose
--             switch to general must EXCLUDE 8/13 (and their corrections)
--             from matrix and close without deleting a single row;
--   1308    — stays general throughout: the write-validation negative
--             (project criterion for a general subject -> 422);
--   1309    — carrier of the BUG-041 runtime repro evaluation;
--   1305/1306 — c_level writer and the live read-only c_level shape;
--   different grade coefficients (0.60 / 2.20 / 1.10) so index arithmetic
--   cannot silently pass on a 1.0 fallback.

DO $$
BEGIN
  IF current_database() !~ '^epe_reclass_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id BETWEEN 1301 AND 1310 OR evaluator_id BETWEEN 1301 AND 1310
);
DELETE FROM performance_db.score_corrections
WHERE subject_id BETWEEN 1301 AND 1310 OR evaluator_id BETWEEN 1301 AND 1310;
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1301 AND 1310 OR evaluator_id BETWEEN 1301 AND 1310;
DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1301 AND 1310;
DELETE FROM performance_db.evaluation_period_participants WHERE user_id BETWEEN 1301 AND 1310;
DELETE FROM performance_db.users WHERE id BETWEEN 1301 AND 1310;

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date
)
VALUES
  -- admin (also the correction writer: admin corrections store c_level level)
  (1301, 'RC Admin', 'rc.admin@example.invalid', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M3'),
   NULL, 'Reclass acceptance admin', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- manager of 1303/1304/1308/1309; evaluated upward by them
  (1302, 'RC Manager', 'rc.manager@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M2'),
   NULL, 'Reclass acceptance manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  -- G: general -> project mid-campaign (additive path), grade S1 = 0.60
  (1303, 'RC Employee G', 'rc.employee.g@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1302, 'Reclass acceptance employee G', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- P: project -> general -> project (soft exclusion), grade S4-M1 = 2.20
  (1304, 'RC Employee P', 'rc.employee.p@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S4-M1'),
   1302, 'Reclass acceptance employee P', true, 'project', false, true, true, 0, DATE '2025-01-01'),
  -- c_level writer (c_level_direct scores for P: criteria 1 and 10)
  (1305, 'RC C-level Writer', 'rc.clevel.writer@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C1'),
   NULL, 'Reclass acceptance c-level writer', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- c_level READ-ONLY (the live 21/40/61 shape: can_evaluate=false, no grade)
  (1306, 'RC C-level Reader', 'rc.clevel.reader@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   NULL,
   NULL, 'Reclass acceptance c-level reader', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- hr
  (1307, 'RC HR', 'rc.hr@example.invalid', 'hr',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S3'),
   NULL, 'Reclass acceptance hr', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- stays general: write-validation negative subject, grade S2 = 1.10
  (1308, 'RC Employee N', 'rc.employee.n@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1302, 'Reclass acceptance employee N', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- BUG-041 repro carrier, grade S2 = 1.10
  (1309, 'RC Employee R', 'rc.employee.r@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1302, 'Reclass acceptance employee R', false, 'general', false, true, true, 0, DATE '2025-01-01');

-- Sessions the guard will accept (jti + token_version + unexpired).
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
VALUES
  ('33333333-3333-4333-8333-333333333301', 1301, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333302', 1302, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333303', 1303, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333304', 1304, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333305', 1305, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333306', 1306, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333307', 1307, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333308', 1308, 0, now(), now() + interval '2 days'),
  ('33333333-3333-4333-8333-333333333309', 1309, 0, now(), now() + interval '2 days');

-- Every fixture actor is in scope of H1-2026 (period id 2).
INSERT INTO performance_db.evaluation_period_participants (period_id, user_id, is_in_scope, exclusion_reason)
SELECT 2, u.id, true, NULL
FROM performance_db.users u
WHERE u.id BETWEEN 1301 AND 1310
ON CONFLICT (period_id, user_id) DO UPDATE
  SET is_in_scope = true, exclusion_reason = NULL, updated_at = now();

COMMIT;

SELECT
  current_database() AS database,
  (SELECT count(*) FROM performance_db.users WHERE id BETWEEN 1301 AND 1310) AS fixture_users,
  (SELECT count(*) FROM performance_db.auth_sessions WHERE user_id BETWEEN 1301 AND 1310) AS fixture_sessions,
  (SELECT count(*) FROM performance_db.evaluation_period_participants
     WHERE period_id = 2 AND user_id BETWEEN 1301 AND 1310) AS fixture_participants,
  (SELECT status || ',' || is_active || ',' || COALESCE(evaluation_started_at::text, 'not-started')
     FROM performance_db.evaluation_periods WHERE id = 2) AS h1,
  (SELECT string_agg(u.id || '=' || g.coefficient, ' ' ORDER BY u.id)
     FROM performance_db.users u JOIN performance_db.grades g ON g.id = u.grade_id
    WHERE u.id IN (1303, 1304, 1308)) AS subject_grade_coefficients;
