-- Migration 012: Reconcile evaluation period constraints
--
-- Purpose:
--   1. Validate data integrity before any DDL.
--   2. Set period_id and evaluation_source NOT NULL (idempotent).
--   3. Create correct period-scoped unique indexes with canonical names.
--      Non-self: (subject_id, evaluator_id, evaluation_source, period_id)
--      Self:     (subject_id, period_id)
--   4. Drop all known obsolete uniqueness indexes after the new ones are live.
--   5. Validate evaluation_periods invariants and create enforcement DDL:
--      - At most one is_active=true row.
--      - Consistency: is_active = (status = 'active').
--      - Partial unique index idx_evaluation_periods_single_active.
--      - Named CHECK constraint chk_evaluation_periods_active_status_consistent.
--
-- Safety:
--   - All wrapped in a single transaction; rolls back completely on any failure.
--   - All validation DO $$ blocks abort the migration if data is bad.
--   - All DDL operations are idempotent; safe to rerun on an already-migrated DB.
--   - Index (re)creation only touches the catalog when the existing definition is wrong.
--
-- Obsolete indexes removed:
--   idx_evaluations_unique_pair          — (subject_id, evaluator_id, is_self_evaluation) — no source/period
--   idx_evaluations_unique_pair_with_source — (subject_id, evaluator_id, evaluation_source) — no period
--   idx_evaluations_unique_pair_source      — (subject_id, evaluator_id, evaluation_source) — no period
--   idx_evaluations_self_unique             — (subject_id, period_id) — superseded by canonical name

BEGIN;

-- ── 1. Validate: no NULL period_id ───────────────────────────────────────────

DO $$
DECLARE
  bad_count bigint;
BEGIN
  SELECT COUNT(*) INTO bad_count
  FROM performance_db.evaluations
  WHERE period_id IS NULL;

  IF bad_count > 0 THEN
    RAISE EXCEPTION
      'Migration 012 aborted: % evaluation row(s) have NULL period_id. '
      'Populate period_id before running this migration.',
      bad_count;
  END IF;
END;
$$;

-- ── 2. Validate: no NULL evaluation_source ───────────────────────────────────

DO $$
DECLARE
  bad_count bigint;
BEGIN
  SELECT COUNT(*) INTO bad_count
  FROM performance_db.evaluations
  WHERE evaluation_source IS NULL;

  IF bad_count > 0 THEN
    RAISE EXCEPTION
      'Migration 012 aborted: % evaluation row(s) have NULL evaluation_source. '
      'Populate evaluation_source before running this migration.',
      bad_count;
  END IF;
END;
$$;

-- ── 3. Validate: no duplicates on the four-column non-self key ────────────────
--    key = (subject_id, evaluator_id, evaluation_source, period_id) WHERE NOT self

DO $$
DECLARE
  dup_count bigint;
  dup_sample text;
BEGIN
  SELECT COUNT(*), string_agg(sample, '; ')
  INTO dup_count, dup_sample
  FROM (
    SELECT
      subject_id || '/' || evaluator_id || '/'
        || evaluation_source || '/' || period_id AS sample
    FROM performance_db.evaluations
    WHERE is_self_evaluation = false
    GROUP BY subject_id, evaluator_id, evaluation_source, period_id
    HAVING COUNT(*) > 1
    LIMIT 5
  ) t;

  IF dup_count > 0 THEN
    RAISE EXCEPTION
      'Migration 012 aborted: % duplicate '
      '(subject_id, evaluator_id, evaluation_source, period_id) tuple(s) exist '
      'among non-self evaluations. Sample: [%]. '
      'Deduplicate before running this migration.',
      dup_count, dup_sample;
  END IF;
END;
$$;

-- ── 4. Validate: no duplicates on the self-eval key ──────────────────────────
--    key = (subject_id, period_id) WHERE is_self_evaluation

DO $$
DECLARE
  dup_count bigint;
  dup_sample text;
BEGIN
  SELECT COUNT(*), string_agg(sample, '; ')
  INTO dup_count, dup_sample
  FROM (
    SELECT subject_id || '/' || period_id AS sample
    FROM performance_db.evaluations
    WHERE is_self_evaluation = true
    GROUP BY subject_id, period_id
    HAVING COUNT(*) > 1
    LIMIT 5
  ) t;

  IF dup_count > 0 THEN
    RAISE EXCEPTION
      'Migration 012 aborted: % duplicate (subject_id, period_id) tuple(s) '
      'exist among self-evaluations. Sample: [%]. '
      'Deduplicate before running this migration.',
      dup_count, dup_sample;
  END IF;
END;
$$;

-- ── 5. Set period_id NOT NULL (idempotent) ────────────────────────────────────

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'performance_db'
      AND table_name   = 'evaluations'
      AND column_name  = 'period_id'
      AND is_nullable  = 'YES'
  ) THEN
    ALTER TABLE performance_db.evaluations
      ALTER COLUMN period_id SET NOT NULL;
  END IF;
END;
$$;

-- ── 6. Set evaluation_source NOT NULL (idempotent) ────────────────────────────

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'performance_db'
      AND table_name   = 'evaluations'
      AND column_name  = 'evaluation_source'
      AND is_nullable  = 'YES'
  ) THEN
    ALTER TABLE performance_db.evaluations
      ALTER COLUMN evaluation_source SET NOT NULL;
  END IF;
END;
$$;

-- ── 7. Create idx_evaluations_unique_non_self_period ──────────────────────────
--    Correct definition: (subject_id, evaluator_id, evaluation_source, period_id)
--    WHERE is_self_evaluation = false
--    If an index with this name already exists but has a wrong definition, drop and recreate.

DO $$
DECLARE
  idx_exists     boolean;
  idx_def_ok     boolean;
BEGIN
  SELECT
    EXISTS(
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'performance_db'
        AND indexname   = 'idx_evaluations_unique_non_self_period'
    ),
    EXISTS(
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'performance_db'
        AND indexname   = 'idx_evaluations_unique_non_self_period'
        AND indexdef LIKE '%subject_id%evaluator_id%evaluation_source%period_id%'
        AND indexdef LIKE '%is_self_evaluation = false%'
    )
  INTO idx_exists, idx_def_ok;

  IF idx_exists AND NOT idx_def_ok THEN
    -- Wrong definition — drop and recreate below
    DROP INDEX performance_db.idx_evaluations_unique_non_self_period;
    idx_exists := false;
  END IF;

  IF NOT idx_exists THEN
    CREATE UNIQUE INDEX idx_evaluations_unique_non_self_period
      ON performance_db.evaluations
        (subject_id, evaluator_id, evaluation_source, period_id)
      WHERE is_self_evaluation = false;
  END IF;
END;
$$;

-- ── 8. Create idx_evaluations_unique_self_period ──────────────────────────────
--    Correct definition: (subject_id, period_id) WHERE is_self_evaluation = true

DO $$
DECLARE
  idx_exists     boolean;
  idx_def_ok     boolean;
BEGIN
  SELECT
    EXISTS(
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'performance_db'
        AND indexname   = 'idx_evaluations_unique_self_period'
    ),
    EXISTS(
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'performance_db'
        AND indexname   = 'idx_evaluations_unique_self_period'
        AND indexdef LIKE '%subject_id%period_id%'
        AND indexdef LIKE '%is_self_evaluation = true%'
    )
  INTO idx_exists, idx_def_ok;

  IF idx_exists AND NOT idx_def_ok THEN
    DROP INDEX performance_db.idx_evaluations_unique_self_period;
    idx_exists := false;
  END IF;

  IF NOT idx_exists THEN
    CREATE UNIQUE INDEX idx_evaluations_unique_self_period
      ON performance_db.evaluations (subject_id, period_id)
      WHERE is_self_evaluation = true;
  END IF;
END;
$$;

-- ── 9. Validate evaluation_periods: at most one is_active=true ───────────────

DO $$
DECLARE
  active_count bigint;
BEGIN
  SELECT COUNT(*) INTO active_count
  FROM performance_db.evaluation_periods
  WHERE is_active = true;

  IF active_count > 1 THEN
    RAISE EXCEPTION
      'Migration 012 aborted: % evaluation_periods rows have is_active=true. '
      'At most one period may be active. Fix data before running this migration.',
      active_count;
  END IF;
END;
$$;

-- ── 10. Validate evaluation_periods: is_active ⟺ (status = ''active'') ───────

DO $$
DECLARE
  incons_count bigint;
  incons_sample text;
BEGIN
  SELECT COUNT(*), string_agg(id::text || ':is_active=' || is_active || '/status=' || status, '; ')
  INTO incons_count, incons_sample
  FROM (
    SELECT id, is_active, status
    FROM performance_db.evaluation_periods
    WHERE (is_active = true AND status != 'active')
       OR (is_active = false AND status = 'active')
    LIMIT 5
  ) t;

  IF incons_count > 0 THEN
    RAISE EXCEPTION
      'Migration 012 aborted: % evaluation_periods rows have inconsistent is_active/status. '
      'Sample: [%]. Fix before running this migration.',
      incons_count, incons_sample;
  END IF;
END;
$$;

-- ── 11. Create idx_evaluation_periods_single_active (idempotent) ──────────────
--    Partial unique index on a constant expression ensures at most one is_active=true.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'performance_db'
      AND indexname   = 'idx_evaluation_periods_single_active'
  ) THEN
    CREATE UNIQUE INDEX idx_evaluation_periods_single_active
      ON performance_db.evaluation_periods ((true))
      WHERE is_active = true;
  END IF;
END;
$$;

-- ── 12. Add CHECK constraint for is_active/status consistency (idempotent) ────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema     = 'performance_db'
      AND table_name       = 'evaluation_periods'
      AND constraint_name  = 'chk_evaluation_periods_active_status_consistent'
      AND constraint_type  = 'CHECK'
  ) THEN
    ALTER TABLE performance_db.evaluation_periods
      ADD CONSTRAINT chk_evaluation_periods_active_status_consistent
      CHECK ((is_active = true) = (status = 'active'));
  END IF;
END;
$$;

-- ── 13. Drop all known obsolete indexes (after new ones are live) ─────────────

-- (subject_id, evaluator_id, is_self_evaluation) — no source, no period
DROP INDEX IF EXISTS performance_db.idx_evaluations_unique_pair;

-- (subject_id, evaluator_id, evaluation_source) — no period (from migration 002)
DROP INDEX IF EXISTS performance_db.idx_evaluations_unique_pair_with_source;

-- (subject_id, evaluator_id, evaluation_source) — no period (from migration 007)
DROP INDEX IF EXISTS performance_db.idx_evaluations_unique_pair_source;

-- (subject_id, period_id) WHERE self — superseded by canonical name
DROP INDEX IF EXISTS performance_db.idx_evaluations_self_unique;

COMMIT;
