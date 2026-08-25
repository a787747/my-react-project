\set ON_ERROR_STOP on

-- Fixture actors for the TERMINATED_EMPLOYEES brief (2026-08-25, D-0825-7).
--
-- Synthetic ids 1501–1509, same discipline as seed_walkthrough_throwaway.sql:
-- the stand is a restored copy of live, and no real person's row is touched by
-- this file. REAL scrypt password hashes, because the brief drives the actual
-- login form in a browser and has to prove that a terminated employee can no
-- longer get through it. Fixture password for every actor: Term2026-Portal!
--
-- Actor shape, chosen so the GAVE/ABOUT split is measurable:
--   1501 admin — the actor who terminates.
--   1502 manager — three direct reports (1503/1504/1505). Two roles at once:
--        the person termination must be REFUSED for (has direct reports), and
--        the person whose ratings must not move by a digit when 1503 goes.
--   1503 employee, project participant — THE TERMINATION SUBJECT. Both gives
--        (upward → 1502) and receives (manager ← 1502, self, c_level ← 1506).
--   1504 employee, general — control colleague; also evaluates 1502 upward.
--   1505 employee, project — control colleague; also evaluates 1502 upward.
--   1506 c_level writer (can_evaluate, never a subject).
--   1507 employee already OUT of H1 scope for hired_after_period_end — proves
--        that terminating and reinstating never clobbers somebody else's
--        exclusion reason.
--   1508 employee who has NEVER registered (password_hash NULL) — the shared
--        invite is the one door a terminated employee could still walk
--        through, so the refusal has to be proven on somebody who has no
--        password to refuse. 1508 gets terminated.
--   1509 identical to 1508 and NOT terminated — the control that shows the
--        registration refusal is caused by the termination and not by a
--        broken fixture.
--
-- Grade coefficients differ (0.60 / 1.10 / 2.20 / 0.30) so the index arithmetic
-- cannot silently pass on a 1.0 fallback, and every seeded score differs so an
-- accidentally dropped evaluation moves a printed number instead of hiding in
-- an average.
--
-- The stand's period 2 is STARTED here (evaluation_started_at). That is a
-- stand-only change: without the second gate there are no tasks to lose, so
-- there is nothing to prove. Live is never touched by this file — the guard
-- below refuses any database whose name is not a termination stand.

DO $$
BEGIN
  IF current_database() !~ '^epe_term_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

-- Idempotent teardown of anything a previous run of this seed left behind.
DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id BETWEEN 1501 AND 1509 OR evaluator_id BETWEEN 1501 AND 1509
);
DELETE FROM performance_db.score_corrections
WHERE subject_id BETWEEN 1501 AND 1509 OR evaluator_id BETWEEN 1501 AND 1509;
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1501 AND 1509 OR evaluator_id BETWEEN 1501 AND 1509;
DELETE FROM performance_db.employment_events
WHERE user_id BETWEEN 1501 AND 1509 OR actor_id BETWEEN 1501 AND 1509;
DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1501 AND 1509;
DELETE FROM performance_db.password_reset_tokens WHERE user_id BETWEEN 1501 AND 1509;
DELETE FROM performance_db.period_results WHERE user_id BETWEEN 1501 AND 1509;
DELETE FROM performance_db.evaluation_period_participants WHERE user_id BETWEEN 1501 AND 1509;
-- A previous run of this seed started the period as 1501 and a previous close
-- may have stamped closed_by; both are FKs into users and would block the
-- DELETE below. Clearing them is what makes re-running this file a no-op
-- rather than an error.
UPDATE performance_db.evaluation_periods
SET evaluation_started_at = NULL, evaluation_started_by = NULL
WHERE evaluation_started_by BETWEEN 1501 AND 1509;
UPDATE performance_db.period_results
SET closed_by = NULL
WHERE closed_by BETWEEN 1501 AND 1509;
DELETE FROM performance_db.users WHERE id BETWEEN 1501 AND 1509;

-- ── Actors ───────────────────────────────────────────────────────────────────

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date, password_hash
)
VALUES
  (1501, 'TM Admin', 'tm.admin@sedamedical.com', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C3'),
   NULL, 'Termination stand admin', false, 'general', false, true, false, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$XJ-ytKgjuUq4WKA6Mewuhg$BmAibqss6PKiJTPts--z3MnMEu3Ff7uLBYzjwxgLRm-0NjIiEw8424t_hdUgcUWSGgLBRhuIvDtB3ACiBCQZ2Q'),

  (1502, 'TM Manager', 'tm.manager@sedamedical.com', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1501, 'Termination stand manager', false, 'general', true, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$S8_EdOtr3KSepyOy_0wSQQ$j1_qF2mDi6l6JCil0MbGUCRcurFy0nJ34dg1h4nYH0ygRtTTN5qyqbSUy_xE2LDbwf_05gV4-Ro8xYtwmiHuMw'),

  -- THE SUBJECT. Project participant, so six manager-path criteria apply.
  (1503, 'TM Leaver', 'tm.leaver@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1502, 'Termination stand subject', true, 'project', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$rDWJHXiU_duTDyicjo2RQg$jdL9ag-BAEDhBeT0TKek5pHgzYZnrZoQJM7s2j3X57gGIserwUeV2S-RB8h0LycP7VBLltNkqBgfyuhtm7tFCw'),

  (1504, 'TM Stayer A', 'tm.stayer.a@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1502, 'Termination stand control A', false, 'general', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$XWST-Z9cMVZiSTqMCfX_AA$fc52eo4MCmTrrxiRNnRoGnwm_KoD515K9z8oJYGBKwS7dPGxs6UsWn_m1o-YX9QTS7y45JPM_IQ89FF2yoE1_A'),

  (1505, 'TM Stayer B', 'tm.stayer.b@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1502, 'Termination stand control B', true, 'project', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$gVZq3hgx5xoMDTLdLsVXnw$1q1ohSnpgvn8pQI_j-pAZMbDeEsL3m3gwRejTQxXLfSPupdoFfz8lR_VIqPbdt78Agom5ewW9eu1TlJHdDvAzg'),

  (1506, 'TM CLevel', 'tm.clevel@sedamedical.com', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C1'),
   NULL, 'Termination stand c_level writer', false, 'general', false, true, false, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$u8O7mApYMsVvMflvRkO4bw$4ASJVC70T7QGFYIxog-gPWxebAQYE8JLC0_cUrKmt2NL6G3owaPDt67vkyUTzE4T9g8N-HtBp-vrK6ym691jnw'),

  -- Hired after the period ended: already excluded, for a different reason.
  (1507, 'TM Newcomer', 'tm.newcomer@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1501, 'Termination stand newcomer', false, 'general', false, true, true, 0,
   DATE '2026-07-06',
   '$scrypt$N=16384,r=8,p=1$kTWzL0Kgh30FqG2zMMQ4QA$CGb4Ng2Udph9O2pLcgMvFy2UEbbl_Ofyin7-GYkfvrCJnwBHJy859yxbg5QTxO3A_pQEgj3l2cCLzQFyti_ZyQ'),

  -- Never registered: password_hash stays NULL, so the shared invite is their
  -- only way in. 1508 is terminated during the proof; 1509 is the control.
  (1508, 'TM Unregistered Leaver', 'tm.unreg.leaver@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1501, 'Termination stand unregistered leaver', false, 'general', false, true, true, 0,
   DATE '2025-01-01', NULL),

  (1509, 'TM Unregistered Stayer', 'tm.unreg.stayer@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1501, 'Termination stand unregistered control', false, 'general', false, true, true, 0,
   DATE '2025-01-01', NULL);

-- has_subordinates is owned by trg_update_has_subordinates, which fires on the
-- INSERTs above. Asserted rather than set.
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM performance_db.users u
  WHERE u.id BETWEEN 1501 AND 1509
    AND u.has_subordinates <> EXISTS (SELECT 1 FROM performance_db.users s WHERE s.manager_id = u.id);
  IF bad > 0 THEN
    RAISE EXCEPTION 'trg_update_has_subordinates disagreed with the graph on % fixture rows', bad;
  END IF;
END
$$;

-- ── Period membership (period 2 = H1-2026 on the restored copy) ──────────────

INSERT INTO performance_db.evaluation_period_participants
  (period_id, user_id, is_in_scope, exclusion_reason)
VALUES
  (2, 1501, true,  NULL),
  (2, 1502, true,  NULL),
  (2, 1503, true,  NULL),
  (2, 1504, true,  NULL),
  (2, 1505, true,  NULL),
  (2, 1506, true,  NULL),
  (2, 1507, false, 'hired_after_period_end'),
  (2, 1508, true,  NULL),
  (2, 1509, true,  NULL),
  -- Every real person also has a row on the Annual 2026 container (period 5).
  -- The fixtures need one too, or the proof cannot show that a termination
  -- takes somebody out of a future period as well as the running one.
  (5, 1501, true,  NULL),
  (5, 1502, true,  NULL),
  (5, 1503, true,  NULL),
  (5, 1504, true,  NULL),
  (5, 1505, true,  NULL),
  (5, 1506, true,  NULL),
  (5, 1507, true,  NULL),
  (5, 1508, true,  NULL),
  (5, 1509, true,  NULL);

-- Open the campaign on the stand: without the second gate nobody has tasks.
UPDATE performance_db.evaluation_periods
SET evaluation_started_at = now(), evaluation_started_by = 1501
WHERE id = 2 AND evaluation_started_at IS NULL;

-- ── Evaluations ─────────────────────────────────────────────────────────────
-- Every score is distinct, so an evaluation that silently disappears moves a
-- printed average instead of hiding inside one.
--
-- calculated_score is the plain mean of the rows below it (formula #1 of
-- HANDOVER §4) and is written explicitly here, exactly as the submit route
-- would compute it.

-- 1502 → 1503 (manager). The ABOUT evaluation: must stop counting for 1503.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1503, 1502, 2, 7.0000, 'manager', false, 'completed', 'stand: manager on leaver', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,8),(4,7),(8,6),(12,7),(13,7),(14,7)) AS v(c,s);

-- 1502 → 1504 (manager)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1504, 1502, 2, 5.5000, 'manager', false, 'completed', 'stand: manager on stayer A', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,6),(4,5),(12,5),(14,6)) AS v(c,s);

-- 1502 → 1505 (manager)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1505, 1502, 2, 8.1667, 'manager', false, 'completed', 'stand: manager on stayer B', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,9),(4,8),(8,8),(12,7),(13,9),(14,8)) AS v(c,s);

-- 1501 → 1502 (manager). Feeds 1502's own final_rating and bonus_index.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1502, 1501, 2, 7.4000, 'manager', false, 'completed', 'stand: admin on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,8),(3,7),(4,7),(12,8),(14,7)) AS v(c,s);

-- 1503 → 1502 (upward). THE GAVE EVALUATION. It must survive 1503's
-- termination and keep feeding 1502's rating_upward.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1502, 1503, 2, 9.0000, 'subordinate', false, 'completed', 'stand: leaver upward on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,9),(3,9),(4,9),(12,9),(14,9)) AS v(c,s);

-- 1504 → 1502 (upward)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1502, 1504, 2, 4.0000, 'subordinate', false, 'completed', 'stand: stayer A upward on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,4),(3,4),(4,4),(12,4),(14,4)) AS v(c,s);

-- 1505 → 1502 (upward)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1502, 1505, 2, 6.0000, 'subordinate', false, 'completed', 'stand: stayer B upward on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,6),(3,6),(4,6),(12,6),(14,6)) AS v(c,s);

-- 1503 self-review (ABOUT)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, weighted_score,
     evaluation_source, is_self_evaluation, status, general_comment, updated_at)
  VALUES (1503, 1503, 2, 8.0000, 4.5000, 'self', true, 'completed', 'stand: leaver self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,8),(4,8),(12,8)) AS v(c,s);

-- 1504 self-review
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, weighted_score,
     evaluation_source, is_self_evaluation, status, general_comment, updated_at)
  VALUES (1504, 1504, 2, 5.0000, 1.5000, 'self', true, 'completed', 'stand: stayer A self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,5),(4,5),(12,5)) AS v(c,s);

-- 1506 → 1503 (c_level_direct, c_level_only criteria). ABOUT.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1503, 1506, 2, 6.5000, 'c_level_direct', false, 'completed', 'stand: c_level on leaver', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,7),(10,6)) AS v(c,s);

-- 1506 → 1502 (c_level_direct)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1502, 1506, 2, 5.5000, 'c_level_direct', false, 'completed', 'stand: c_level on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,6),(10,5)) AS v(c,s);

COMMIT;
