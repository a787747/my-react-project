-- Migration 014: the second gate — "evaluation started" on a period
--
-- Purpose:
--   Split the single campaign switch (activate) into two. Activation opens the
--   preparation window: the period is the current one, admin can still finish
--   the criteria catalogue and the money inputs, and employees see nothing.
--   Starting the evaluation opens the campaign itself: tasks appear, the submit
--   routes accept, and the criteria catalogue freezes. D-0822-1.
--
-- Data semantics:
--   - evaluation_started_at is the single source of truth for "the campaign is
--     running". NULL = not started. It is written exactly once by
--     POST /api/periods/start-evaluation and never cleared by any route:
--     the mark is irreversible at product level, like activation and close.
--     Recovery is SQL on the host, same as the documented activation rollback.
--   - evaluation_started_by is the admin who started it, for the audit trail.
--     Nullable because a hand-written SQL repair may not know an actor; the
--     CHECK below only forbids a starter without a start time.
--   - The column is deliberately NOT tied to status by a CHECK. Close leaves it
--     set (a closed period was started — that is history), and the documented
--     emergency stop sets an active period back to draft by SQL; a status-linked
--     CHECK would break both.
--   - Type/leaf preconditions (no containers, no annual periods) are enforced by
--     the route, exactly as activation and close enforce them. See
--     docs/LIFECYCLE_COEFF_2026-08-2x.md.
--
-- Safety: idempotent; no data rows are written or changed; single transaction.
--   Every existing period keeps evaluation_started_at = NULL, so no period is
--   retroactively "started".

BEGIN;

ALTER TABLE performance_db.evaluation_periods
    ADD COLUMN IF NOT EXISTS evaluation_started_at timestamptz;

ALTER TABLE performance_db.evaluation_periods
    ADD COLUMN IF NOT EXISTS evaluation_started_by integer
        REFERENCES performance_db.users(id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_evaluation_periods_started_by_needs_started_at'
    ) THEN
        ALTER TABLE performance_db.evaluation_periods
            ADD CONSTRAINT chk_evaluation_periods_started_by_needs_started_at
            CHECK (evaluation_started_by IS NULL OR evaluation_started_at IS NOT NULL);
    END IF;
END
$$;

COMMENT ON COLUMN performance_db.evaluation_periods.evaluation_started_at IS
    'When the admin opened the evaluation itself (second gate). NULL = the period is active but still in preparation: employees see no tasks and the submit routes refuse. Set once, never cleared by any route.';
COMMENT ON COLUMN performance_db.evaluation_periods.evaluation_started_by IS
    'users.id of the admin who started the evaluation. Audit trail only.';

COMMIT;
