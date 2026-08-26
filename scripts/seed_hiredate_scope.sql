\set ON_ERROR_STOP on

-- HIRE_DATE_AND_SCOPE_TOGGLE stand-only fixture.
-- Applied after seed_midyear_throwaway.sql and seed_night_extra.sql.
--
-- MY Newcomer (1607) starts date-derived OUT of H1. We deliberately give them
-- one manager-path score directly in the throwaway database. The treatment
-- stand corrects their hire date and brings them IN; the control does not.
-- After both real closes, exactly this person's frozen result may differ.
--
-- Hand arithmetic, formula #3 (no denominator):
-- criterion 3 score 6 × level coefficient 1.10 × weight 3.00 × grade A 0.30
-- = bonus index 5.9400. final_rating = 6.0000.

DO $$
BEGIN
  IF current_database() !~ '^epe_mid_night_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id
  FROM performance_db.evaluations
  WHERE subject_id = 1607 AND period_id = 2
);
DELETE FROM performance_db.evaluations
WHERE subject_id = 1607 AND period_id = 2;

WITH evaluation AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES
    (1607, 1601, 2, 6.0000, 'manager', false, 'completed',
     'stand: stored while date-derived out; included after date correction', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores
  (evaluation_id, criteria_id, score_value, comment)
SELECT id, 3, 6, 'stand: hand index 5.9400'
FROM evaluation;

COMMIT;
