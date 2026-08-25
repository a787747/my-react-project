-- TEAM_PAGE_AND_DEPLOY_LOCK stand seed (2026-08-25).
--
-- Deliberately adds NO synthetic people. The point of this stand is that a real
-- manager sees their REAL subordinates, so the org tree is the live one,
-- restored from a dated dump, and the only thing this seed changes is that two
-- existing accounts become loggable-in on the throwaway copy:
--
--   id 2  Alexander Petrosov  admin    — presses «Запустить оценку» on the stand
--   id 88 Yelena Son          manager  — the manager under test: 13 direct
--                                        reports, of whom 2 are terminated and
--                                        out of H1 scope (Kuvvat Garayev 51,
--                                        Murad Bayramov 66), so the page must
--                                        show exactly 11.
--
-- This file writes to REAL user rows, so it carries two locks:
--
--   1. It refuses to run against any database whose name is not `epe_team_%`.
--      `epe_2026` can therefore never be a target, however the file is invoked.
--   2. The hashes are NOT in this file. They are generated per run and passed
--      in as -v admin_hash=... -v manager_hash=... by
--      scripts/setup_team_throwaway.sh, so nothing credential-shaped is
--      committed and no two stands share a secret.
--
-- Live password_hash values are never read, copied or written. token_version is
-- left alone: nothing here invalidates a session.

\set ON_ERROR_STOP on

DO $$
BEGIN
  IF current_database() NOT LIKE 'epe\_team\_%' THEN
    RAISE EXCEPTION
      'seed_team_throwaway refuses to run against %: stand databases are named epe_team_<stamp>',
      current_database();
  END IF;
END
$$;

BEGIN;

UPDATE performance_db.users
   SET password_hash = :'admin_hash'
 WHERE id = 2 AND email = 'alexander@sedamedical.com';

UPDATE performance_db.users
   SET password_hash = :'manager_hash'
 WHERE id = 88 AND email = 'yelena@sedamedical.com';

-- Refuse the seed if either account was not the one expected.
DO $$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n FROM performance_db.users
   WHERE id IN (2, 88) AND password_hash IS NOT NULL;
  IF n <> 2 THEN
    RAISE EXCEPTION 'seed_team_throwaway: expected 2 seeded accounts, found %', n;
  END IF;
END
$$;

COMMIT;

-- What the stand must look like afterwards, for the record.
SELECT 'SEEDED' AS marker, id, full_name, role, (password_hash IS NOT NULL) AS can_login
  FROM performance_db.users WHERE id IN (2, 88) ORDER BY id;
