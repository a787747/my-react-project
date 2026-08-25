-- Migration 015: terminated employees — a state on the person, an event in the log
--
-- Decision D-0825-7 (owner, 2026-08-25): a terminated employee disappears from
-- every list, task and calculation. They are not evaluated, they do not
-- evaluate, and they take no share of the bonus pool for the period. The state
-- is reversible. Evaluations they GAVE stay in force; evaluations ABOUT them
-- are excluded.
--
-- What this migration adds, and why each piece exists:
--
--   users.terminated_at   — the CURRENT state, and the only thing a list query
--                           or a login check has to read. NULL = employed.
--                           It is the moment the state was set in the system,
--                           not the moment the person stopped working.
--   users.termination_date— the owner's date (the last working day). Separate
--                           from terminated_at on purpose: the owner marks
--                           somebody terminated days after the fact, and the
--                           money question ("which period did they drop out
--                           of") is answered by the date they left, not by the
--                           date somebody got round to clicking.
--
--   employment_events     — the RECORD. Append-only, never updated, never
--                           deleted. users.terminated_at holds only the latest
--                           state, so a terminate → reinstate → terminate
--                           sequence would otherwise lose its own history —
--                           and D-0825-7 says the termination event must stay
--                           readable after the period closes. Every row names
--                           the actor, the moment, the effective date and the
--                           campaign period that was current at the time.
--                           This is also the first audit row this database has
--                           ever had for a change to a person (BUG-059); it is
--                           deliberately scoped to employment events and is not
--                           a general audit log.
--
-- What this migration deliberately does NOT do:
--
--   * It does not touch can_evaluate / can_be_evaluated. Those are the owner's
--     standing policy flags for the read-only C-level trio (D-0821-4). Writing
--     them at termination would make the state unrecoverable on reinstatement:
--     you could no longer tell whether can_evaluate=false meant "read-only by
--     decision" or "was terminated once". Exclusion from tasks, submits and the
--     pool is achieved by evaluation_period_participants.is_in_scope, which is
--     period-bound — which is what the money record needs.
--   * It does not add a column to evaluation_period_participants. That table
--     already carries is_in_scope + exclusion_reason + updated_at, and its
--     CHECK (is_in_scope OR exclusion_reason IS NOT NULL) already forbids a
--     silent exclusion. The one thing it cannot record is the actor, and that
--     is what employment_events is for.
--   * It does not delete, rewrite or recompute anything. No evaluation row, no
--     score, no correction, no stored result is touched by this file.
--
-- Safety: idempotent; additive only; single transaction. Every existing user
--   keeps terminated_at = NULL and termination_date = NULL, so nobody is
--   retroactively terminated. employment_events starts empty.

BEGIN;

-- ── 1. Current state on the person ───────────────────────────────────────────

ALTER TABLE performance_db.users
    ADD COLUMN IF NOT EXISTS terminated_at timestamptz;

ALTER TABLE performance_db.users
    ADD COLUMN IF NOT EXISTS termination_date date;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_users_termination_pair'
    ) THEN
        -- Neither half is meaningful alone: a terminated_at with no date leaves
        -- the money question unanswerable, and a date with no terminated_at is
        -- a person the product still treats as employed.
        ALTER TABLE performance_db.users
            ADD CONSTRAINT chk_users_termination_pair
            CHECK ((terminated_at IS NULL) = (termination_date IS NULL));
    END IF;
END
$$;

COMMENT ON COLUMN performance_db.users.terminated_at IS
    'When the terminated state was set in the system. NULL = employed. Reversible: reinstatement sets it back to NULL and appends a reinstated row to performance_db.employment_events. Never written by admin/save-user.';
COMMENT ON COLUMN performance_db.users.termination_date IS
    'The owner-supplied last working day. Decides which period the person dropped out of. NULL exactly when terminated_at is NULL.';

-- ── 2. The append-only record ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS performance_db.employment_events (
    id            bigserial PRIMARY KEY,
    user_id       integer     NOT NULL REFERENCES performance_db.users(id),
    event_type    varchar(20) NOT NULL,
    effective_date date,
    period_id     integer     REFERENCES performance_db.evaluation_periods(id),
    actor_id      integer     NOT NULL REFERENCES performance_db.users(id),
    occurred_at   timestamptz NOT NULL DEFAULT now(),
    note          varchar(500)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_employment_events_type'
    ) THEN
        ALTER TABLE performance_db.employment_events
            ADD CONSTRAINT chk_employment_events_type
            CHECK (event_type IN ('terminated', 'reinstated'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_employment_events_terminated_has_date'
    ) THEN
        -- A termination without its effective date is exactly the row that
        -- cannot answer "which period did the pool lose this person from".
        ALTER TABLE performance_db.employment_events
            ADD CONSTRAINT chk_employment_events_terminated_has_date
            CHECK (event_type <> 'terminated' OR effective_date IS NOT NULL);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_employment_events_user
    ON performance_db.employment_events (user_id, occurred_at DESC);

COMMENT ON TABLE performance_db.employment_events IS
    'Append-only record of termination and reinstatement (D-0825-7). Never updated, never deleted: users.terminated_at holds only the current state, this holds the history. The FKs deliberately carry no ON DELETE CASCADE — a person referenced here cannot be hard-deleted, which is the point.';
COMMENT ON COLUMN performance_db.employment_events.period_id IS
    'The active leaf campaign period at the moment of the event, or NULL if none was active. The full set of periods the person was scoped out of is readable from evaluation_period_participants where exclusion_reason = ''terminated''.';
COMMENT ON COLUMN performance_db.employment_events.actor_id IS
    'users.id of the admin who set the state. Taken from the auth token, never from the request body.';

COMMIT;
