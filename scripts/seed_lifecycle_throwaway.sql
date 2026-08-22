\set ON_ERROR_STOP on

-- Fixture actors for the two-gate lifecycle + coefficient-privacy acceptance
-- (brief 2026-08-22). Users 1201-1208; auth_sessions with fixed jtis so the
-- proof script can mint matching JWTs against the stand's JWT_SIGNING_SECRET.
--
-- Two evaluation subjects deliberately carry DIFFERENT grade coefficients so the
-- server-side weighted_score can be recomputed independently and compared per
-- subject (a single coefficient would not distinguish "real" from "1.0").

DO $$
BEGIN
  IF current_database() !~ '^epe_lifecycle_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id BETWEEN 1201 AND 1210 OR evaluator_id BETWEEN 1201 AND 1210
);
DELETE FROM performance_db.score_corrections
WHERE subject_id BETWEEN 1201 AND 1210 OR evaluator_id BETWEEN 1201 AND 1210;
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1201 AND 1210 OR evaluator_id BETWEEN 1201 AND 1210;
DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1201 AND 1210;
DELETE FROM performance_db.evaluation_period_participants WHERE user_id BETWEEN 1201 AND 1210;
DELETE FROM performance_db.users WHERE id BETWEEN 1201 AND 1210;

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date
)
VALUES
  -- admin
  (1201, 'LC Admin', 'lc.admin@example.invalid', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M3'),
   NULL, 'Lifecycle acceptance admin', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- manager (evaluates 1203 and 1204; is evaluated upward by them)
  (1202, 'LC Manager', 'lc.manager@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M2'),
   NULL, 'Lifecycle acceptance manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  -- subject A: grade S1, coefficient 0.60
  (1203, 'LC Employee A', 'lc.employee.a@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1202, 'Lifecycle acceptance employee A', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- subject B: grade S4-M1, coefficient 2.20 — deliberately different from A
  (1204, 'LC Employee B', 'lc.employee.b@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S4-M1'),
   1202, 'Lifecycle acceptance employee B', true, 'project', false, true, true, 0, DATE '2025-01-01'),
  -- c_level writer
  (1205, 'LC C-level Writer', 'lc.clevel.writer@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C1'),
   NULL, 'Lifecycle acceptance c-level writer', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- c_level READ-ONLY (the live 21/40/61 shape: can_evaluate=false, no grade)
  (1206, 'LC C-level Reader', 'lc.clevel.reader@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   NULL,
   NULL, 'Lifecycle acceptance c-level reader', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- hr
  (1207, 'LC HR', 'lc.hr@example.invalid', 'hr',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S3'),
   NULL, 'Lifecycle acceptance hr', false, 'general', false, false, false, 0, DATE '2025-01-01');

-- Sessions the guard will accept (jti + token_version + unexpired).
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
VALUES
  ('22222222-2222-4222-8222-222222222201', 1201, 0, now(), now() + interval '2 days'),
  ('22222222-2222-4222-8222-222222222202', 1202, 0, now(), now() + interval '2 days'),
  ('22222222-2222-4222-8222-222222222203', 1203, 0, now(), now() + interval '2 days'),
  ('22222222-2222-4222-8222-222222222204', 1204, 0, now(), now() + interval '2 days'),
  ('22222222-2222-4222-8222-222222222205', 1205, 0, now(), now() + interval '2 days'),
  ('22222222-2222-4222-8222-222222222206', 1206, 0, now(), now() + interval '2 days'),
  ('22222222-2222-4222-8222-222222222207', 1207, 0, now(), now() + interval '2 days');

-- Every fixture actor is in scope of H1-2026 (period id 2).
INSERT INTO performance_db.evaluation_period_participants (period_id, user_id, is_in_scope, exclusion_reason)
SELECT 2, u.id, true, NULL
FROM performance_db.users u
WHERE u.id BETWEEN 1201 AND 1210
ON CONFLICT (period_id, user_id) DO UPDATE
  SET is_in_scope = true, exclusion_reason = NULL, updated_at = now();

COMMIT;

SELECT
  current_database() AS database,
  (SELECT count(*) FROM performance_db.users WHERE id BETWEEN 1201 AND 1210) AS fixture_users,
  (SELECT count(*) FROM performance_db.auth_sessions WHERE user_id BETWEEN 1201 AND 1210) AS fixture_sessions,
  (SELECT count(*) FROM performance_db.evaluation_period_participants
     WHERE period_id = 2 AND user_id BETWEEN 1201 AND 1210) AS fixture_participants,
  (SELECT status || ',' || is_active || ',' || COALESCE(evaluation_started_at::text, 'not-started')
     FROM performance_db.evaluation_periods WHERE id = 2) AS h1,
  (SELECT string_agg(u.id || '=' || g.coefficient, ' ' ORDER BY u.id)
     FROM performance_db.users u JOIN performance_db.grades g ON g.id = u.grade_id
    WHERE u.id IN (1203, 1204)) AS subject_grade_coefficients;
