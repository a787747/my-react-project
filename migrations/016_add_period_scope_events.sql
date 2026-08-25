-- Migration 016: taking an EMPLOYED person out of scope of an existing period
--
-- Brief MID_YEAR_HIRES_SCOPE (2026-08-25). The owner reports people who only
-- started working in the second half of the year but whose recorded join_date
-- puts them inside H1. Scope was computed exactly once, at period creation, from
-- `join_date > end_date`; no route on live can change it for a period that
-- already exists — except termination, and these people are not leaving.
--
-- What this migration adds:
--
--   period_scope_events — the RECORD for a scope change made by hand: who took
--                         whom out of which period, when, with which reason and
--                         which note; and the same for putting them back.
--                         Append-only, never updated, never deleted.
--
-- Why a separate table and not employment_events:
--
--   employment_events (migration 015) is deliberately scoped to EMPLOYMENT
--   events — terminated / reinstated — and its own comment says so. The people
--   this migration is for are employed, keep their login, and will participate
--   in H2. Filing them under "employment events" would make a future reader
--   believe they left the company. The two records also answer different
--   questions: employment_events answers "is this person still with us", this
--   one answers "which periods was this person deliberately kept out of, and on
--   whose signature".
--
--   The period is a first-class NOT NULL column here, because a scope change is
--   meaningless without one. In employment_events period_id is nullable and
--   only records which period happened to be active at the time.
--
-- What this migration deliberately does NOT do:
--
--   * No new column on users. Being out of scope of one period is not a
--     property of the person; it is a property of the (period, person) pair,
--     and evaluation_period_participants already is that pair.
--   * No column on evaluation_period_participants. It already carries
--     is_in_scope + exclusion_reason + updated_at with
--     CHECK (is_in_scope OR exclusion_reason IS NOT NULL). The only thing it
--     cannot record is the actor and the reason in words — that is this table.
--   * It does not touch can_evaluate / can_be_evaluated (D-0821-4 policy flags),
--     terminated_at / termination_date (employment), password_hash or
--     token_version (login). A person excluded this way keeps their login and
--     can still register.
--   * It does not delete, rewrite or recompute anything. No evaluation row, no
--     score, no correction and no stored result is touched by this file.
--
-- Safety: idempotent; additive only; single transaction; starts empty.

BEGIN;

CREATE TABLE IF NOT EXISTS performance_db.period_scope_events (
    id          bigserial   PRIMARY KEY,
    period_id   integer     NOT NULL REFERENCES performance_db.evaluation_periods(id),
    user_id     integer     NOT NULL REFERENCES performance_db.users(id),
    event_type  varchar(20) NOT NULL,
    reason      varchar(64),
    actor_id    integer     NOT NULL REFERENCES performance_db.users(id),
    occurred_at timestamptz NOT NULL DEFAULT now(),
    note        varchar(500)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_period_scope_events_type'
    ) THEN
        ALTER TABLE performance_db.period_scope_events
            ADD CONSTRAINT chk_period_scope_events_type
            CHECK (event_type IN ('excluded', 'included'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_period_scope_events_reason_pairing'
    ) THEN
        -- An exclusion without its reason is the row that cannot say WHY the
        -- pool lost this person — the same silent exclusion the participants
        -- table's own CHECK already forbids. An inclusion carries no reason:
        -- being in scope is the default state and needs none.
        ALTER TABLE performance_db.period_scope_events
            ADD CONSTRAINT chk_period_scope_events_reason_pairing
            CHECK ((event_type = 'excluded') = (reason IS NOT NULL));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_period_scope_events_user
    ON performance_db.period_scope_events (user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_period_scope_events_period
    ON performance_db.period_scope_events (period_id, occurred_at DESC);

COMMENT ON TABLE performance_db.period_scope_events IS
    'Append-only record of a hand-made scope change on an existing period (brief MID_YEAR_HIRES_SCOPE, 2026-08-25). Never updated, never deleted: evaluation_period_participants holds only the current flag, this holds the history and the signature. The FKs deliberately carry no ON DELETE CASCADE. Termination and reinstatement are NOT recorded here — they live in employment_events, because they are employment events and this is not.';
COMMENT ON COLUMN performance_db.period_scope_events.reason IS
    'The exclusion_reason written onto the participants row: ''excluded_by_admin'' for this route. Distinct by construction from ''terminated'' (a leaver) and ''hired_after_period_end'' (computed automatically at period creation), so the three populations never blur.';
COMMENT ON COLUMN performance_db.period_scope_events.actor_id IS
    'users.id of the admin who made the change. Taken from the auth token, never from the request body.';
COMMENT ON COLUMN performance_db.period_scope_events.note IS
    'The owner''s words for why. The machine reason is one value; this is where "started in September, offer signed in April" goes.';

COMMIT;
