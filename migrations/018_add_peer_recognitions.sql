-- Migration 018: peer recognition — «Отметить коллегу»
--
-- Brief PEER_RECOGNITION (2026-08-27). The owner adds an optional surface where
-- any employed, registered person may name ONE colleague whose help genuinely
-- mattered in the period, and describe it in three short free-text fields
-- (situation → action → outcome).
--
-- What this is NOT, stated in the schema because the schema is what a later
-- reader trusts:
--
--   * It is NOT a vote, NOT a rating and NOT money. There is no score column,
--     no weight, no coefficient and no numeric field of any kind in this table.
--   * It has NO foreign key into `evaluations`, `evaluation_scores`,
--     `score_corrections` or `period_results`, in either direction. Nothing
--     that computes a rating, a final score, a bonus index or a completion
--     counter can reach these rows by a join it already performs.
--   * A COUNT of these rows is never displayed to anybody. That is a product
--     rule, not a database one — but the moment a count appears the surface
--     becomes a popularity contest, which is the one outcome the owner's design
--     is built to prevent. No index here exists to make counting-by-nominee
--     fast, and none should be added for that purpose.
--
-- Shape:
--
--   ONE nomination per (period, author), enforced by the primary key of the
--   uniqueness — `uq_peer_recognitions_period_author`. The author may replace
--   their nomination until the period closes; a replacement is an UPDATE of the
--   same row, so "exactly one" is a database fact, not an application promise.
--
--   period_id is NOT NULL: a nomination without a period could never be scoped,
--   shown or aged out. The FK carries no ON DELETE CASCADE — there is no route
--   that deletes a period, and a nomination must not disappear silently if one
--   day there is.
--
--   author_id and nominee_id both reference users. `chk_peer_recognitions_not_self`
--   makes self-nomination impossible in the database as well as in the route:
--   the other two refusals (own manager, own direct report) are graph facts that
--   change over time and are therefore enforced in the route, where the graph is
--   read at write time — a CHECK cannot see another row.
--
--   The three texts are NOT NULL and are CHECKed non-empty after trimming: a
--   nomination whose three fields are blank is the "he is a nice guy" nomination
--   the form is designed to make impossible.
--
-- What this migration deliberately does NOT do:
--
--   * It does not touch `users`, `evaluation_periods`,
--     `evaluation_period_participants`, `criteria`, `score_coefficients`,
--     `grades`, or any campaign table. It reads none of them and alters none.
--   * It creates no trigger, no view and no function. Nothing existing can start
--     behaving differently because this file ran.
--
-- Safety: idempotent; additive only; single transaction; starts empty.

BEGIN;

CREATE TABLE IF NOT EXISTS performance_db.peer_recognitions (
    id         bigserial   PRIMARY KEY,
    period_id  integer     NOT NULL REFERENCES performance_db.evaluation_periods(id),
    author_id  integer     NOT NULL REFERENCES performance_db.users(id),
    nominee_id integer     NOT NULL REFERENCES performance_db.users(id),
    situation  text        NOT NULL,
    action     text        NOT NULL,
    outcome    text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_peer_recognitions_period_author'
    ) THEN
        -- "One optional nomination per person per period, replaceable until the
        -- period closes" — the replaceability is an UPDATE onto this key, so a
        -- second row can never exist even if a route is one day written badly.
        ALTER TABLE performance_db.peer_recognitions
            ADD CONSTRAINT uq_peer_recognitions_period_author
            UNIQUE (period_id, author_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_peer_recognitions_not_self'
    ) THEN
        ALTER TABLE performance_db.peer_recognitions
            ADD CONSTRAINT chk_peer_recognitions_not_self
            CHECK (author_id <> nominee_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_peer_recognitions_texts_present'
    ) THEN
        ALTER TABLE performance_db.peer_recognitions
            ADD CONSTRAINT chk_peer_recognitions_texts_present
            CHECK (
                btrim(situation) <> ''
                AND btrim(action) <> ''
                AND btrim(outcome) <> ''
            );
    END IF;
END
$$;

-- The only index beyond the two constraints. It serves the reader screen, which
-- lists a period newest-first. There is deliberately NO index on nominee_id: the
-- one query it would make cheap is "how many times was this person named", and
-- that query must never be run.
CREATE INDEX IF NOT EXISTS idx_peer_recognitions_period_created
    ON performance_db.peer_recognitions (period_id, created_at DESC);

COMMENT ON TABLE performance_db.peer_recognitions IS
    'Optional peer recognition (brief PEER_RECOGNITION, 2026-08-27). One nomination per author per period, replaceable until the period closes. NOT a vote, NOT a rating, NOT money: no numeric column, no foreign key into evaluations / evaluation_scores / score_corrections / period_results, and absent from the matrix, the final scores, the bonus calculation, the close dataset, every completion counter, every export and every analytics figure. A COUNT of nominations is never shown to anybody — displaying one turns the surface into a popularity contest and destroys the reason it exists.';
COMMENT ON COLUMN performance_db.peer_recognitions.author_id IS
    'users.id of the person doing the naming. Taken from the auth token, never from the request body.';
COMMENT ON COLUMN performance_db.peer_recognitions.nominee_id IS
    'users.id of the named colleague. The route refuses oneself, one''s own manager, one''s own direct report and anyone terminated; only the self-refusal is also a CHECK, because the other three are graph facts that a row-local CHECK cannot see.';
COMMENT ON COLUMN performance_db.peer_recognitions.situation IS
    'Free text: «В какой ситуации это было?». A situation, an action and an outcome together are what a nomination for a drinking buddy cannot be filled in with.';
COMMENT ON COLUMN performance_db.peer_recognitions.action IS
    'Free text: «Что конкретно он или она сделал(а)?» — an action, not a character trait.';
COMMENT ON COLUMN performance_db.peer_recognitions.outcome IS
    'Free text: «Что изменилось благодаря этому?» — for the author, the project or the client.';

COMMIT;
