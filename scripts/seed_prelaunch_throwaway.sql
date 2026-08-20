\set ON_ERROR_STOP on

DO $$
BEGIN
  IF current_database() !~ '^epe_prelaunch_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1001 AND 1010;
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1001 AND 1010
   OR evaluator_id BETWEEN 1001 AND 1010;
DELETE FROM performance_db.evaluation_period_participants
WHERE user_id BETWEEN 1001 AND 1010;
DELETE FROM performance_db.users WHERE id BETWEEN 1001 AND 1010;

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version
)
VALUES
  (1007, 'Prelaunch Admin', 'admin.prelaunch@example.invalid', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1008, 'Acceptance admin', false, 'general', false, true, false, 0),
  (1008, 'Prelaunch C-level Writer', 'clevel.writer.prelaunch@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Acceptance C-level writer', false, 'general', false, true, false, 0),
  (1009, 'Prelaunch C-level Read-only', 'clevel.readonly.prelaunch@example.invalid', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Acceptance C-level read-only', false, 'general', false, false, false, 0),
  (1001, 'Prelaunch Manager', 'manager.prelaunch@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Acceptance manager', false, 'general', true, true, true, 0),
  (1010, 'Prelaunch Foreign Manager', 'foreign.manager.prelaunch@example.invalid', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   NULL, 'Acceptance foreign manager', false, 'general', true, true, true, 0),
  (1002, 'Prelaunch Report Complete', 'report.complete.prelaunch@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1001, 'Acceptance report complete', false, 'general', false, true, true, 0),
  (1003, 'Prelaunch Report Pending Self', 'report.pending.prelaunch@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1001, 'Acceptance report pending self', false, 'general', false, true, true, 0),
  (1004, 'Prelaunch Report Pending Manager', 'report.pending.manager.prelaunch@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1001, 'Acceptance report pending manager', false, 'general', false, true, true, 0),
  (1005, 'Prelaunch Out Of Scope', 'out.of.scope.prelaunch@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1001, 'Acceptance out of scope', false, 'general', false, true, true, 0),
  (1006, 'Prelaunch Foreign Subject', 'foreign.subject.prelaunch@example.invalid', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT min(id) FROM performance_db.grades),
   1008, 'Acceptance foreign subject', true, 'project', false, true, true, 0);

INSERT INTO performance_db.evaluation_period_participants (
  period_id, user_id, is_in_scope, exclusion_reason
)
SELECT
  2,
  id,
  id <> 1005,
  CASE WHEN id = 1005 THEN 'Acceptance fixture: out of scope' ELSE NULL END
FROM performance_db.users
WHERE id BETWEEN 1001 AND 1010;

UPDATE performance_db.evaluation_periods
SET is_active = false
WHERE id <> 2;

UPDATE performance_db.evaluation_periods
SET status = 'active', is_active = true
WHERE id = 2;

INSERT INTO performance_db.evaluations (
  id, period_id, subject_id, evaluator_id, status, general_comment,
  private_comment, calculated_score, weighted_score, updated_at,
  evaluation_type, is_self_evaluation, evaluation_source
)
VALUES
  (2001, 2, 1001, 1001, 'completed', 'Manager own self-review', NULL,
   3.00, 3.00, now() - interval '9 minutes', 'self', true, 'self'),
  (2002, 2, 1002, 1002, 'completed', 'Report complete self-review', NULL,
   8.00, 8.00, now() - interval '8 minutes', 'self', true, 'self'),
  (2003, 2, 1001, 1002, 'completed', 'Upward fact', 'Hidden upward private comment',
   8.00, NULL, now() - interval '7 minutes', 'manager', false, 'subordinate'),
  (2004, 2, 1002, 1001, 'completed', 'Hidden manager general comment', 'Hidden manager private comment',
   7.00, NULL, now() - interval '6 minutes', 'manager', false, 'manager'),
  (2005, 2, 1003, 1001, 'completed', 'Pending-self report manager evaluation', NULL,
   5.00, NULL, now() - interval '5 minutes', 'manager', false, 'manager'),
  (2006, 2, 1004, 1004, 'completed', 'Pending-manager report self-review', NULL,
   7.00, 7.00, now() - interval '4 minutes', 'self', true, 'self'),
  (2007, 2, 1001, 1004, 'completed', 'Second upward fact', NULL,
   6.00, NULL, now() - interval '3 minutes', 'manager', false, 'subordinate'),
  (2008, 2, 1006, 1006, 'completed', 'Foreign self-review', NULL,
   4.00, 4.00, now() - interval '2 minutes', 'self', true, 'self'),
  (2009, 2, 1006, 1010, 'completed', 'Foreign manager general comment', 'Foreign manager private comment',
   4.00, NULL, now() - interval '1 minute', 'manager', false, 'manager'),
  (2010, 2, 1002, 1008, 'completed', 'C-level direct evaluation', 'C-level private comment',
   9.00, NULL, now(), 'manager', false, 'c_level_direct');

INSERT INTO performance_db.evaluation_scores (
  id, evaluation_id, criteria_id, score_value, comment
)
VALUES
  (3001, 2001, 3, 2, 'МОЯ САМООЦЕНКА — критерий 3'),
  (3002, 2001, 4, 3, 'МОЯ САМООЦЕНКА — критерий 4'),
  (3003, 2001, 12, 4, 'МОЯ САМООЦЕНКА — критерий 12'),
  (3004, 2002, 3, 9, 'САМООЦЕНКА ПОДЧИНЁННОГО — критерий 3'),
  (3005, 2002, 4, 8, 'САМООЦЕНКА ПОДЧИНЁННОГО — критерий 4'),
  (3006, 2002, 12, 7, 'САМООЦЕНКА ПОДЧИНЁННОГО — критерий 12'),
  (3007, 2003, 2, 8, 'Скрытый upward-комментарий'),
  (3008, 2004, 3, 6, 'СКРЫТЫЙ КОММЕНТАРИЙ РУКОВОДИТЕЛЯ — критерий 3'),
  (3009, 2004, 4, 7, 'СКРЫТЫЙ КОММЕНТАРИЙ РУКОВОДИТЕЛЯ — критерий 4'),
  (3010, 2004, 12, 8, 'СКРЫТЫЙ КОММЕНТАРИЙ РУКОВОДИТЕЛЯ — критерий 12'),
  (3011, 2005, 3, 5, 'Manager evaluation without self-review'),
  (3012, 2005, 4, 5, NULL),
  (3013, 2005, 12, 5, NULL),
  (3014, 2006, 3, 8, 'Self-review awaiting manager'),
  (3015, 2006, 4, 7, NULL),
  (3016, 2006, 12, 6, NULL),
  (3017, 2007, 2, 6, 'Second hidden upward comment'),
  (3018, 2008, 3, 4, 'Foreign self-review'),
  (3019, 2008, 4, 4, NULL),
  (3020, 2008, 12, 4, NULL),
  (3021, 2009, 3, 4, 'Foreign manager score comment'),
  (3022, 2009, 4, 4, NULL),
  (3023, 2009, 12, 4, NULL),
  (3024, 2010, 1, 9, 'C-level strategic comment'),
  (3025, 2010, 10, 9, 'C-level culture comment');

COMMIT;

SELECT
  current_database() AS database,
  (SELECT count(*) FROM performance_db.users WHERE id BETWEEN 1001 AND 1010) AS fixture_users,
  (SELECT count(*) FROM performance_db.evaluations WHERE id BETWEEN 2001 AND 2010) AS fixture_evaluations,
  (SELECT status || ',' || is_active FROM performance_db.evaluation_periods WHERE id = 2) AS h1;
