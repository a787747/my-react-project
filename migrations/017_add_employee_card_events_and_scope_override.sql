-- Migration 017: auditable employee-card edits and durable manual scope precedence
--
-- D-0826-4 / D-0826-5 (owner, 2026-08-26).
--
-- `employee_card_events` is append-only. It records every actual create/update
-- made through admin/save-user, including the old and new hire date, with the
-- authenticated actor and database time. Existing employment and scope history
-- remains in the two specialised tables introduced by migrations 015 and 016;
-- no historical row is copied, rewritten or deleted here.
--
-- `scope_override` is separate from `exclusion_reason` on purpose:
-- exclusion_reason describes why the current row is out, while scope_override
-- records a manual decision in either direction. Without an explicit
-- `included_by_admin` value, turning a join_date_missing row on would clear its
-- reason and the next hire-date recompute would silently turn it off again.
--
-- Safety: additive only, idempotent, one transaction, no existing value moves.

BEGIN;

ALTER TABLE performance_db.evaluation_period_participants
    ADD COLUMN IF NOT EXISTS scope_override varchar(32);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'evaluation_period_participants_scope_override_check'
          AND conrelid = 'performance_db.evaluation_period_participants'::regclass
    ) THEN
        ALTER TABLE performance_db.evaluation_period_participants
            ADD CONSTRAINT evaluation_period_participants_scope_override_check
            CHECK (
                scope_override IS NULL
                OR scope_override IN ('included_by_admin', 'excluded_by_admin')
            );
    END IF;
END
$$;

COMMENT ON COLUMN performance_db.evaluation_period_participants.scope_override IS
    'NULL = date-derived/default state and eligible for hire-date recompute. included_by_admin or excluded_by_admin = a manual per-period decision that recompute must never override. Termination also always wins independently through users.terminated_at and exclusion_reason=terminated.';

CREATE TABLE IF NOT EXISTS performance_db.employee_card_events (
    id          bigserial   PRIMARY KEY,
    user_id     integer     NOT NULL REFERENCES performance_db.users(id),
    actor_id    integer     NOT NULL REFERENCES performance_db.users(id),
    event_type  varchar(20) NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    changes     jsonb       NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_employee_card_events_type'
          AND conrelid = 'performance_db.employee_card_events'::regclass
    ) THEN
        ALTER TABLE performance_db.employee_card_events
            ADD CONSTRAINT chk_employee_card_events_type
            CHECK (event_type IN ('created', 'updated'));
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_employee_card_events_changes_object'
          AND conrelid = 'performance_db.employee_card_events'::regclass
    ) THEN
        ALTER TABLE performance_db.employee_card_events
            ADD CONSTRAINT chk_employee_card_events_changes_object
            CHECK (
                jsonb_typeof(changes) = 'object'
                AND changes <> '{}'::jsonb
            );
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_employee_card_events_user
    ON performance_db.employee_card_events (user_id, occurred_at DESC);

COMMENT ON TABLE performance_db.employee_card_events IS
    'Append-only record of employee-card writes through admin/save-user. changes is an object keyed by changed field; each value carries old and new. Actor comes from the auth guard, never the request.';
COMMENT ON COLUMN performance_db.employee_card_events.changes IS
    'JSON object such as {"join_date":{"old":"2026-04-09","new":null}}. An event is inserted in the same SQL statement as the card write.';

COMMIT;
