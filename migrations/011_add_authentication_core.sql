BEGIN;

ALTER TABLE performance_db.users
    ADD COLUMN IF NOT EXISTS token_version integer NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'users_token_version_check'
          AND conrelid = 'performance_db.users'::regclass
    ) THEN
        ALTER TABLE performance_db.users
            ADD CONSTRAINT users_token_version_check
            CHECK (token_version >= 0);
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower
    ON performance_db.users(lower(email));

CREATE TABLE IF NOT EXISTS performance_db.auth_sessions (
    jti uuid PRIMARY KEY,
    user_id integer NOT NULL
        REFERENCES performance_db.users(id) ON DELETE CASCADE,
    token_version integer NOT NULL,
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT auth_sessions_expiry_check CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
    ON performance_db.auth_sessions(user_id, expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS performance_db.password_reset_tokens (
    id bigserial PRIMARY KEY,
    user_id integer NOT NULL
        REFERENCES performance_db.users(id) ON DELETE CASCADE,
    token_hash char(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT password_reset_tokens_expiry_check
        CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_active
    ON performance_db.password_reset_tokens(user_id, expires_at)
    WHERE used_at IS NULL;

CREATE TABLE IF NOT EXISTS performance_db.auth_login_attempts (
    email varchar(150) PRIMARY KEY,
    window_started_at timestamptz NOT NULL,
    failed_count integer NOT NULL DEFAULT 0,
    locked_until timestamptz,
    last_failed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT auth_login_attempts_failed_count_check
        CHECK (failed_count >= 0)
);

COMMIT;
