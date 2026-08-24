\set ON_ERROR_STOP on

-- Fixture actors for the browser walkthrough (brief 2026-08-24: browser-driven
-- walkthrough of the campaign UI). Same actor shape as the finalize fixture
-- (1301-1310), plus REAL scrypt password hashes: this brief drives the login
-- form in a browser, so fixture users must authenticate through the actual
-- auth/login workflow instead of pre-minted JWTs. Fixture password for every
-- actor: Walk2026-Portal!
--
-- Actor shape (unchanged from seed_finalize_throwaway.sql):
--   1301 admin, 1310 mid-manager above 1302, 1302 direct manager of
--   1303/1304/1308/1309, 1304 project subject, 1303/1308/1309 general,
--   1305 c_level writer, 1306 c_level read-only, 1307 hr.
--   Grade coefficients differ (0.60 / 2.20 / 1.10) so index arithmetic
--   cannot silently pass on a 1.0 fallback.

DO $$
BEGIN
  IF current_database() !~ '^epe_walk_' THEN
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
  -- admin
  (1301, 'WT Admin', 'wt.admin@sedamedical.com', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M3'),
   NULL, 'Walkthrough admin', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- middle manager: manager-of-managers above 1302
  (1310, 'WT MidManager', 'wt.midmanager@sedamedical.com', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M2'),
   NULL, 'Walkthrough middle manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  -- direct manager of 1303/1304/1308/1309; reports to 1310
  (1302, 'WT Manager', 'wt.manager@sedamedical.com', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'M2'),
   1310, 'Walkthrough manager', false, 'general', true, true, true, 0, DATE '2025-01-01'),
  -- G: general employee, grade S1 = 0.60
  (1303, 'WT Employee G', 'wt.employee.g@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1302, 'Walkthrough employee G', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- P: project employee, S4-M1 = 2.20
  (1304, 'WT Employee P', 'wt.employee.p@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S4-M1'),
   1302, 'Walkthrough employee P', true, 'project', false, true, true, 0, DATE '2025-01-01'),
  -- c_level writer
  (1305, 'WT C-level Writer', 'wt.clevel.writer@sedamedical.com', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C1'),
   NULL, 'Walkthrough c-level writer', false, 'general', false, true, false, 0, DATE '2025-01-01'),
  -- c_level READ-ONLY (the live 21/40/61 shape: can_evaluate=false, no grade)
  (1306, 'WT C-level Reader', 'wt.clevel.reader@sedamedical.com', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   NULL,
   NULL, 'Walkthrough c-level reader', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- hr
  (1307, 'WT HR', 'wt.hr@sedamedical.com', 'hr',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S3'),
   NULL, 'Walkthrough hr', false, 'general', false, false, false, 0, DATE '2025-01-01'),
  -- N: general employee, grade S2 = 1.10; reclassification target general->project
  (1308, 'WT Employee N', 'wt.employee.n@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1302, 'Walkthrough employee N', false, 'general', false, true, true, 0, DATE '2025-01-01'),
  -- R: spare direct report, grade S2 = 1.10
  (1309, 'WT Employee R', 'wt.employee.r@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1302, 'Walkthrough employee R', false, 'general', false, true, true, 0, DATE '2025-01-01');

-- Browser-login credentials: scrypt hashes of the shared fixture password
-- Walk2026-Portal! in the exact format LOGIN_VERIFY parses
-- ($scrypt$N=16384,r=8,p=1$<salt16 b64url>$<dk64 b64url>).
UPDATE performance_db.users AS u
SET password_hash = v.hash
FROM (VALUES
  (1301, '$scrypt$N=16384,r=8,p=1$8AyOEg1d0na0hfE1IuGc1w$FEgHOCXPFEcfpAEXP_hpRZF-SkESG4dciLJV7bk0nkcXEtkmUPIObkrP6uIm3cHqN6GYT2IfKXjxNowPtCjFow'),
  (1302, '$scrypt$N=16384,r=8,p=1$cWjO_Ab7zdAHRhTRgCR4xA$vx_bcv996Un8FtBJtW2iw2EuCUATnnJQaYDux3sqWNk_ED4PQLDVxeBBxW-4d2DzP1NnAMaOhvSSfVYJDon8mQ'),
  (1303, '$scrypt$N=16384,r=8,p=1$cQLACxOwIL5x6jC07Dm3Sg$yBR1Ba9soVcBZkCzHXR3m-aAfDqJbO5gsvIxfBQIXyOfy4_CKNm8ft2D865R5OOLOCv8dh6-pPjPvByxKppUKA'),
  (1304, '$scrypt$N=16384,r=8,p=1$poV105pcNgnqnI7B8qQ0qw$iD6TmG-fctb2KcWk6IMxBzAjdvH1Vui1O-jQ4QE0tbavhRnO3UmUxWMMNGBARgxX92b0gLu777B5bDKXJNi6hw'),
  (1305, '$scrypt$N=16384,r=8,p=1$S2o_GMJsU5KOygRo2dGLeQ$SRMLRBJm5KKBOtiUj1ymN4cLCFq59WpcQtRkK7CF7udpY9Yw_v3g8IdkYD9oizM-xnGrHIY-WF1oWwDxIM37ZQ'),
  (1306, '$scrypt$N=16384,r=8,p=1$UWjKYRpC5Prsx5Zm1QZ6uA$BiHx-mL69UHtBuUZqawY8TWg_IR14ALwzgaSo35rKw_IP9WG-rcr-LsCpoOEMkuwpYIfuHzn2d4tCsmxC5oFRg'),
  (1307, '$scrypt$N=16384,r=8,p=1$y0wFbWzwrFL-MDxxgg-d2A$8Yq9MKAf7Ht-DfttC6vjMtaSWIy3oQuyhTD9y9su7CnQB4Oi-pzI9f70rhBvwXoallutpYop0Wx2Ib_jWE2k9g'),
  (1308, '$scrypt$N=16384,r=8,p=1$4inaEaJCZW-7lyiahsmKVg$_3k4A2-u3_Gg-Uvkf-dcyTgVyY0TvuO7CZ7pCEVZ9DLfIxB25YWTJVb8C6qvueyJNZxcI8qFNN5wG1F0j8AjZw'),
  (1309, '$scrypt$N=16384,r=8,p=1$tROsNLiq-ddJTJ4mGDcU-w$U-1KUO1t7DMEDQmA_mvDQ9NezxAXggx4LU1pCX3Ml0XvF9IvCvrEElgpx8dCcnY_Gfu4YNuPAe6vRGbn4f4Pnw'),
  (1310, '$scrypt$N=16384,r=8,p=1$Hih7E-2IovDISiACTV1Ffw$52EPpGRz1KsGkUqCTA-JiusoLNnNKqxLflxfbDrujzxwyNJrOZRwpwbddT4DX1CuHohEpDXdpKbR1bSz4XjEJg')
) AS v(id, hash)
WHERE u.id = v.id;

-- Sessions the guard will accept (kept for SQL-side verification and any
-- API-level fallback checks; browser logins create their own rows).
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
VALUES
  ('55555555-5555-4555-8555-555555555501', 1301, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555502', 1302, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555503', 1303, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555504', 1304, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555505', 1305, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555506', 1306, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555507', 1307, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555508', 1308, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555509', 1309, 0, now(), now() + interval '2 days'),
  ('55555555-5555-4555-8555-555555555510', 1310, 0, now(), now() + interval '2 days');

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
  (SELECT count(*) FROM performance_db.users
     WHERE id BETWEEN 1301 AND 1310 AND password_hash LIKE '$scrypt$%') AS fixture_logins,
  (SELECT count(*) FROM performance_db.auth_sessions WHERE user_id BETWEEN 1301 AND 1310) AS fixture_sessions,
  (SELECT count(*) FROM performance_db.evaluation_period_participants
     WHERE period_id = 2 AND user_id BETWEEN 1301 AND 1310) AS fixture_participants,
  (SELECT status || ',' || is_active || ',' || COALESCE(evaluation_started_at::text, 'not-started')
     FROM performance_db.evaluation_periods WHERE id = 2) AS h1,
  (SELECT manager_id FROM performance_db.users WHERE id = 1302) AS manager_of_manager;
