\set ON_ERROR_STOP on

-- PEER_RECOGNITION — evaluations for the close comparison (2026-08-27).
--
-- The close proof needs money to compare. Live has none: the campaign tables
-- are 0/0/0/0, so closing an untouched restore would freeze 89 rows of
-- has_data=false and compare nothing worth comparing.
--
-- This file writes ordinary campaign rows into the STAND ONLY, so that the
-- control and the treatment database — restored from the SAME dump taken after
-- this seed ran — differ by the peer_recognitions rows and by nothing else.
--
-- Two of the four subjects (7 Anton Markin, 8 Arslan Annayev) are exactly the
-- people the proof's nominations name. If a nomination could ever reach a
-- money number, theirs is where it would show.

DO $$
BEGIN
  IF current_database() !~ '^epe_recognition' THEN
    RAISE EXCEPTION 'Refusing to seed a non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

-- Idempotent teardown: only rows this file creates.
DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE period_id = 2 AND subject_id IN (4, 7, 8, 23)
);
DELETE FROM performance_db.evaluations
WHERE period_id = 2 AND subject_id IN (4, 7, 8, 23);

-- 1. Manager channel: Yelena Son (88) evaluates four of her direct reports on
--    the four criteria whose audience is 'all' and which the manager scores.
WITH inserted AS (
  INSERT INTO performance_db.evaluations
    (period_id, subject_id, evaluator_id, status, calculated_score, updated_at,
     evaluation_type, is_self_evaluation, evaluation_source)
  SELECT 2, s.subject_id, 88, 'completed', s.avg_score,
         timestamp '2026-08-27 09:00:00', 'manager', false, 'manager'
  FROM (VALUES (4, 6.50), (7, 7.25), (8, 8.00), (23, 5.75)) AS s(subject_id, avg_score)
  RETURNING id, subject_id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value)
SELECT i.id, c.criteria_id, c.score_value
FROM inserted i
JOIN (VALUES
  (4, 3, 6), (4, 4, 7), (4, 12, 6), (4, 14, 7),
  (7, 3, 7), (7, 4, 8), (7, 12, 7), (7, 14, 7),
  (8, 3, 8), (8, 4, 8), (8, 12, 8), (8, 14, 8),
  (23, 3, 6), (23, 4, 6), (23, 12, 5), (23, 14, 6)
) AS c(subject_id, criteria_id, score_value) ON c.subject_id = i.subject_id;

-- 2. C-level channel: Alexander (2) scores the two c_level_only criteria for
--    the two nominated people.
WITH inserted AS (
  INSERT INTO performance_db.evaluations
    (period_id, subject_id, evaluator_id, status, calculated_score, updated_at,
     evaluation_type, is_self_evaluation, evaluation_source)
  SELECT 2, s.subject_id, 2, 'completed', s.avg_score,
         timestamp '2026-08-27 09:05:00', 'c_level_direct', false, 'c_level_direct'
  FROM (VALUES (7, 7.00), (8, 8.50)) AS s(subject_id, avg_score)
  RETURNING id, subject_id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value)
SELECT i.id, c.criteria_id, c.score_value
FROM inserted i
JOIN (VALUES
  (7, 1, 7), (7, 10, 7),
  (8, 1, 9), (8, 10, 8)
) AS c(subject_id, criteria_id, score_value) ON c.subject_id = i.subject_id;

-- 3. One self-review, so the self channel is populated too and the close
--    dataset is not a single-source artefact.
WITH inserted AS (
  INSERT INTO performance_db.evaluations
    (period_id, subject_id, evaluator_id, status, calculated_score, weighted_score,
     updated_at, evaluation_type, is_self_evaluation, evaluation_source)
  VALUES (2, 8, 8, 'completed', 7.67, 7.10,
          timestamp '2026-08-27 09:10:00', 'self', true, 'self')
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value)
SELECT i.id, c.criteria_id, c.score_value
FROM inserted i
JOIN (VALUES (3, 8), (4, 7), (12, 8)) AS c(criteria_id, score_value) ON true;

COMMIT;
