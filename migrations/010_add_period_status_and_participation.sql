BEGIN;

ALTER TABLE performance_db.evaluation_periods
    ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'draft';

ALTER TABLE performance_db.evaluation_periods
    ALTER COLUMN period_type SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'evaluation_periods_status_check'
          AND conrelid = 'performance_db.evaluation_periods'::regclass
    ) THEN
        ALTER TABLE performance_db.evaluation_periods
            ADD CONSTRAINT evaluation_periods_status_check
            CHECK (status IN ('draft', 'active', 'closed'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'evaluation_periods_name_key'
          AND conrelid = 'performance_db.evaluation_periods'::regclass
    ) THEN
        ALTER TABLE performance_db.evaluation_periods
            ADD CONSTRAINT evaluation_periods_name_key UNIQUE (name);
    END IF;
END
$$;

INSERT INTO performance_db.evaluation_periods (
    name,
    start_date,
    end_date,
    is_active,
    period_type,
    parent_period_id,
    status
)
SELECT
    requested.name,
    requested.start_date,
    requested.end_date,
    requested.is_active,
    requested.period_type,
    requested.parent_period_id,
    requested.status
FROM (
    VALUES
    (
        'Annual 2025',
        DATE '2025-01-01',
        DATE '2025-12-31',
        false,
        'annual',
        NULL::integer,
        'closed'
    ),
    (
        'H1-2026',
        DATE '2026-01-01',
        DATE '2026-06-30',
        false,
        'half_year',
        NULL::integer,
        'draft'
    )
) AS requested(
    name,
    start_date,
    end_date,
    is_active,
    period_type,
    parent_period_id,
    status
)
WHERE NOT EXISTS (
    SELECT 1
    FROM performance_db.evaluation_periods existing
    WHERE existing.name = requested.name
)
ON CONFLICT (name) DO NOTHING;

UPDATE performance_db.evaluation_periods existing
SET start_date = requested.start_date,
    end_date = requested.end_date,
    is_active = requested.is_active,
    period_type = requested.period_type,
    parent_period_id = requested.parent_period_id,
    status = requested.status
FROM (
    VALUES
    (
        'Annual 2025',
        DATE '2025-01-01',
        DATE '2025-12-31',
        false,
        'annual',
        NULL::integer,
        'closed'
    ),
    (
        'H1-2026',
        DATE '2026-01-01',
        DATE '2026-06-30',
        false,
        'half_year',
        NULL::integer,
        'draft'
    )
) AS requested(
    name,
    start_date,
    end_date,
    is_active,
    period_type,
    parent_period_id,
    status
)
WHERE existing.name = requested.name
  AND (
    existing.start_date,
    existing.end_date,
    existing.is_active,
    existing.period_type,
    existing.parent_period_id,
    existing.status
) IS DISTINCT FROM (
    requested.start_date,
    requested.end_date,
    requested.is_active,
    requested.period_type,
    requested.parent_period_id,
    requested.status
);

/*
 * Both inserts and updates are split deliberately. An INSERT ... ON CONFLICT
 * attempt would consume sequence values on every idempotent rerun.
 */
/*
 * Keep the canonical values above synchronized with the update source.
 */

CREATE TABLE IF NOT EXISTS performance_db.evaluation_period_participants (
    period_id integer NOT NULL
        REFERENCES performance_db.evaluation_periods(id) ON DELETE CASCADE,
    user_id integer NOT NULL
        REFERENCES performance_db.users(id) ON DELETE CASCADE,
    is_in_scope boolean NOT NULL DEFAULT true,
    exclusion_reason varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (period_id, user_id),
    CONSTRAINT evaluation_period_participants_reason_check
        CHECK (is_in_scope OR exclusion_reason IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_evaluation_period_participants_user
    ON performance_db.evaluation_period_participants(user_id, period_id);

INSERT INTO performance_db.evaluation_period_participants (
    period_id,
    user_id,
    is_in_scope,
    exclusion_reason
)
SELECT
    period.id,
    users.id,
    users.email NOT IN (
        'esenova@sedamedical.com',
        'govher@sedamedical.com'
    ),
    CASE
        WHEN users.email IN (
            'esenova@sedamedical.com',
            'govher@sedamedical.com'
        ) THEN 'hired_after_period_end'
        ELSE NULL
    END
FROM performance_db.evaluation_periods period
CROSS JOIN performance_db.users users
WHERE period.name = 'H1-2026'
ON CONFLICT (period_id, user_id) DO UPDATE
SET is_in_scope = EXCLUDED.is_in_scope,
    exclusion_reason = EXCLUDED.exclusion_reason,
    updated_at = CASE
        WHEN (
            performance_db.evaluation_period_participants.is_in_scope,
            performance_db.evaluation_period_participants.exclusion_reason
        ) IS DISTINCT FROM (
            EXCLUDED.is_in_scope,
            EXCLUDED.exclusion_reason
        ) THEN now()
        ELSE performance_db.evaluation_period_participants.updated_at
    END
WHERE (
    performance_db.evaluation_period_participants.is_in_scope,
    performance_db.evaluation_period_participants.exclusion_reason
) IS DISTINCT FROM (
    EXCLUDED.is_in_scope,
    EXCLUDED.exclusion_reason
);

COMMIT;
