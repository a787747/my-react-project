\set ON_ERROR_STOP on

-- Campaign rows on the ADMIN_USERS_SUMMARY stand only. Seeds the four
-- channels across the walkthrough fixture so the /admin/users counters
-- can be checked against a non-empty database. Live epe_2026 is refused.

DO $$
BEGIN
  IF current_database() !~ '^epe_adminusers_' THEN
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
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1301 AND 1310 OR evaluator_id BETWEEN 1301 AND 1310;

-- 1303 self (general employee: 3, 4, 12)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1303, 1303, 2, 7.0000, 'self', true, 'completed',
          'stand: 1303 self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,7),(4,7),(12,7)) AS v(c,s);

-- 1302 → 1303 manager, complete for a general non-manager (3,4,12,14)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1303, 1302, 2, 6.5000, 'manager', false, 'completed',
          'stand: 1302 manager→1303', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,6),(4,7),(12,6),(14,7)) AS v(c,s);

-- 1305 → 1303 c_level_direct (existing evaluation for the modal edit path)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1303, 1305, 2, 7.0000, 'c_level_direct', false, 'completed',
          'stand: 1305 c_level→1303', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,8),(10,6)) AS v(c,s);

-- 1308 self + upward; manager has NOT evaluated 1308
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1308, 1308, 2, 6.0000, 'self', true, 'completed',
          'stand: 1308 self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,6),(4,6),(12,6)) AS v(c,s);

WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1302, 1308, 2, 7.0000, 'subordinate', false, 'completed',
          'stand: 1308 upward→1302', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,7)) AS v(c,s);

-- 1304 self + upward + complete manager eval (project: 3,4,8,12,13,14)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1304, 1304, 2, 8.0000, 'self', true, 'completed',
          'stand: 1304 self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,8),(4,8),(12,8)) AS v(c,s);

WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1302, 1304, 2, 8.0000, 'subordinate', false, 'completed',
          'stand: 1304 upward→1302', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,8)) AS v(c,s);

WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1304, 1302, 2, 7.0000, 'manager', false, 'completed',
          'stand: 1302 manager→1304', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,7),(4,7),(8,7),(12,7),(13,7),(14,7)) AS v(c,s);

COMMIT;

SELECT
  current_database() AS database,
  (SELECT count(*) FROM performance_db.evaluations
     WHERE subject_id BETWEEN 1301 AND 1310 OR evaluator_id BETWEEN 1301 AND 1310) AS fixture_evals,
  (SELECT count(*) FROM performance_db.evaluation_scores es
     JOIN performance_db.evaluations e ON e.id = es.evaluation_id
    WHERE e.subject_id BETWEEN 1301 AND 1310 OR e.evaluator_id BETWEEN 1301 AND 1310) AS fixture_scores;
