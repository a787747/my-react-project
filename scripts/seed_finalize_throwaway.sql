\set ON_ERROR_STOP on

-- Fixture actors for the finalization batch (brief 2026-08-24: corrections
-- applicability, BUG-046 middle-manager matrix, new-criterion path).
-- Users 1301-1310; auth_sessions with fixed jtis so the proof script can mint
-- matching JWTs against the stand's JWT_SIGNING_SECRET.
--
-- Shape this acceptance needs (extends the reclass fixture):
--   1310 MID — manager-of-managers ABOVE 1302: the middle manager whose
--              GET api/manager-subordinates-matrix must stop emitting
--              excluded project cells (BUG-046). 1310 is also skip_level
--              for 1303/1304/1308/1309, so mid_level corrections work;
--   1304 P  — project subject: applicable correction target, then switched
--             to general so the excluded cells (and their corrections)
--             disappear from the middle-manager matrix, rows intact;
--   1308 N  — stays general: the corrections-applicability negative
--             (project criterion for a general subject -> 422), and the
--             new-criterion money example carrier (grade S2 = 1.10);
--   different grade coefficients (0.60 / 2.20 / 1.10) so index arithmetic
--   cannot silently pass on a 1.0 fallback.

DO $$
BEGIN
  IF current_database() !~ '^epe_final_' THEN
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
  -- admin (also a correction writer: admin corrections store c_level level)
  (1301, 'FN Admin', 'fn.admin@example.invalid', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M3'),
   NULL, 'Finalize acceptance admin', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- middle manager: manager-of-managers, actor of the BUG-046 matrix
  (1310, 'FN MidManager', 'fn.midmanager@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M2'),
   NULL, 'Finalize acceptance middle manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  -- direct manager of 1303/1304/1308/1309; reports to 1310
  (1302, 'FN Manager', 'fn.manager@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M2'),
   1310, 'Finalize acceptance manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  -- G: general employee, grade S1 = 0.60
  (1303, 'FN Employee G', 'fn.employee.g@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1302, 'Finalize acceptance employee G', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- P: project employee (correction target, then soft-excluded), S4-M1 = 2.20
  (1304, 'FN Employee P', 'fn.employee.p@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S4-M1'),
   1302, 'Finalize acceptance employee P', true, 'project', false, true, true, 0, DATE '2025-01-01'),
  -- c_level writer
  (1305, 'FN C-level Writer', 'fn.clevel.writer@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C1'),
   NULL, 'Finalize acceptance c-level writer', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- c_level READ-ONLY (the live 21/40/61 shape: can_evaluate=false, no grade)
  (1306, 'FN C-level Reader', 'fn.clevel.reader@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   NULL,
   NULL, 'Finalize acceptance c-level reader', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- hr
  (1307, 'FN HR', 'fn.hr@example.invalid', 'hr',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S3'),
   NULL, 'Finalize acceptance hr', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- N: stays general throughout, money-example carrier, grade S2 = 1.10
  (1308, 'FN Employee N', 'fn.employee.n@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1302, 'Finalize acceptance employee N', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- R: spare direct report, grade S2 = 1.10
  (1309, 'FN Employee R', 'fn.employee.r@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1302, 'Finalize acceptance employee R', false, 'general', false, true, true, 0, DATE '2025-01-01');

-- Sessions the guard will accept (jti + token_version + unexpired).
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
VALUES
  ('44444444-4444-4444-8444-444444444401', 1301, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444402', 1302, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444403', 1303, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444404', 1304, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444405', 1305, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444406', 1306, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444407', 1307, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444408', 1308, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444409', 1309, 0, now(), now() + interval '2 days'),
  ('44444444-4444-4444-8444-444444444410', 1310, 0, now(), now() + interval '2 days');

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
    WHERE u.id IN (1303, 1304, 1308)) AS subject_grade_coefficients,
  (SELECT manager_id FROM performance_db.users WHERE id = 1302) AS manager_of_manager;
