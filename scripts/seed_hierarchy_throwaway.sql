\set ON_ERROR_STOP on

-- Fixture actors for the periods-hierarchy acceptance (brief 2026-08-21).
-- Users 1101-1107; auth_sessions with fixed jtis so the proof script can mint
-- matching JWTs against the stand's JWT_SIGNING_SECRET.

DO $$
BEGIN
  IF current_database() !~ '^epe_hier_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1101 AND 1110;
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1101 AND 1110
   OR evaluator_id BETWEEN 1101 AND 1110;
DELETE FROM performance_db.evaluation_period_participants
WHERE user_id BETWEEN 1101 AND 1110;
DELETE FROM performance_db.users WHERE id BETWEEN 1101 AND 1110;

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date
)
VALUES
  (1101, 'Hier Admin', 'hier.admin@example.invalid', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Hier acceptance admin', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  (1102, 'Hier Manager', 'hier.manager@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Hier acceptance manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  (1103, 'Hier Employee A', 'hier.employee.a@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1102, 'Hier acceptance employee A', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  (1104, 'Hier Employee B', 'hier.employee.b@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1102, 'Hier acceptance employee B', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  (1105, 'Hier Employee C', 'hier.employee.c@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1102, 'Hier acceptance employee C', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  (1106, 'Hier C-level Reader', 'hier.clevel@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Hier acceptance c-level', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  (1107, 'Hier HR', 'hier.hr@example.invalid', 'hr',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Hier acceptance hr', false, 'general', false, false, false, 0, DATE '2025-01-01');

-- Sessions the guard will accept (jti + token_version + unexpired).
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
VALUES
  ('11111111-1111-4111-8111-111111111101', 1101, 0, now(), now() + interval '2 days'),
  ('11111111-1111-4111-8111-111111111102', 1102, 0, now(), now() + interval '2 days'),
  ('11111111-1111-4111-8111-111111111103', 1103, 0, now(), now() + interval '2 days'),
  ('11111111-1111-4111-8111-111111111106', 1106, 0, now(), now() + interval '2 days'),
  ('11111111-1111-4111-8111-111111111107', 1107, 0, now(), now() + interval '2 days');

COMMIT;

SELECT
  current_database() AS database,
  (SELECT count(*) FROM performance_db.users WHERE id BETWEEN 1101 AND 1110) AS fixture_users,
  (SELECT count(*) FROM performance_db.auth_sessions WHERE user_id BETWEEN 1101 AND 1110) AS fixture_sessions,
  (SELECT status || ',' || is_active FROM performance_db.evaluation_periods WHERE id = 2) AS h1,
  (SELECT count(*) FROM performance_db.period_results) AS period_results_rows;
