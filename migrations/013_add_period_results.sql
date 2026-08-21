-- Migration 013: close-time period result persistence + period hierarchy column
--
-- Purpose:
--   1. Ensure evaluation_periods.parent_period_id exists (live epe_2026 already
--      has it with an FK; this is a no-op there and a repair for any DB built
--      from the pre-hierarchy schema.sql).
--   2. Create performance_db.period_results — the immutable per-person snapshot
--      written exactly once when a leaf period is closed. Reproducing a closed
--      period's numbers must never require a live join against editable inputs
--      (weights, grades, coefficients, classification, hierarchy). D-0821-2.
--
-- Data semantics:
--   - One row per (period, participant) as recorded at close time.
--   - is_in_scope: the participant flag frozen at close. Out-of-scope people
--     carry no numbers.
--   - has_data=false is the explicit "in scope but never evaluated" marker —
--     the CHECK below makes it impossible for a no-data row to carry a number,
--     so a missing rating can never be read back as a zero.
--   - final_rating: the per-person final exactly as the matrix computes cells —
--     mean over criterion finals, each mean(manager, mid?, c_level?) or
--     c_level_score for c_level_only criteria (D-0820-12).
--   - bonus_index: formula #3 exactly as the money screens compute it —
--     sum over criteria of final × score_coefficient × weight, × grade
--     coefficient. Not a rating (HANDOVER §4).
--
-- Safety: idempotent; no data rows are written; single transaction.

BEGIN;

ALTER TABLE performance_db.evaluation_periods
    ADD COLUMN IF NOT EXISTS parent_period_id integer
        REFERENCES performance_db.evaluation_periods(id);

CREATE TABLE IF NOT EXISTS performance_db.period_results (
    period_id integer NOT NULL
        REFERENCES performance_db.evaluation_periods(id),
    user_id integer NOT NULL
        REFERENCES performance_db.users(id),
    is_in_scope boolean NOT NULL,
    has_data boolean NOT NULL DEFAULT false,
    rating_manager numeric(10,2),
    rating_upward numeric(10,2),
    rating_c_level_direct numeric(10,2),
    rating_self numeric(10,2),
    final_rating numeric(10,4),
    bonus_index numeric(14,4),
    closed_at timestamptz NOT NULL DEFAULT now(),
    closed_by integer REFERENCES performance_db.users(id),
    PRIMARY KEY (period_id, user_id),
    -- a no-data marker can never carry a number
    CONSTRAINT period_results_no_data_is_empty CHECK (
        has_data OR (
            rating_manager IS NULL
            AND rating_upward IS NULL
            AND rating_c_level_direct IS NULL
            AND rating_self IS NULL
            AND final_rating IS NULL
            AND bonus_index IS NULL
        )
    ),
    -- out-of-scope rows are always no-data rows
    CONSTRAINT period_results_out_of_scope_no_data CHECK (
        is_in_scope OR NOT has_data
    )
);

CREATE INDEX IF NOT EXISTS idx_period_results_user
    ON performance_db.period_results (user_id, period_id);

COMMIT;
