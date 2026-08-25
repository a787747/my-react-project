\set ON_ERROR_STOP on

-- Fixture actors for the MID_YEAR_HIRES_SCOPE brief (2026-08-25).
--
-- Synthetic ids 1601–1611, same discipline as seed_termination_throwaway.sql:
-- the stand is a restored copy of live, and no real person's row is touched by
-- this file. REAL scrypt password hashes, because the brief has to prove that
-- an EXCLUDED employee can still get through the actual login form — which is
-- the whole difference between this and termination. Fixture password for
-- every registered actor: Mid2026-Portal!
--
-- Actor shape, chosen so every claim in the acceptance list is measurable:
--   1601 admin — the actor who excludes.
--   1602 manager — direct reports 1603/1604/1605/1610. Two roles at once: the
--        person whose ratings must not move by a digit when 1603 goes, and the
--        owner of the task list that must lose exactly one card.
--   1603 employee, project participant — THE EXCLUSION SUBJECT. Both gives
--        (upward → 1602) and receives (manager ← 1602, self, c_level ← 1606),
--        so the GAVE / ABOUT split is measurable in period_results.
--        join_date 2026-02-05: on paper an H1 hire, which is exactly the
--        population this brief exists for.
--   1604 employee, general — control colleague; also evaluates 1602 upward.
--   1605 employee, project — control colleague; also evaluates 1602 upward.
--   1606 c_level writer (can_evaluate, never a subject).
--   1607 employee already OUT of H1 scope for hired_after_period_end — proves
--        the new route never clobbers somebody else's exclusion reason and
--        that the reverse action refuses to cancel it.
--   1608 employee who has NEVER registered (password_hash NULL) — excluded by
--        the new route and then required to register through the shared invite.
--        Termination closes that door; this must not.
--   1609 identical to 1608 and NOT excluded — the control that shows the
--        registration result is caused by the fixture and not by luck.
--   1610 employee with NO evaluation_period_participants row for period 2 at
--        all — the "added after the period was created" case. Every read
--        surface is measured against them so the code-reading claim ("no row
--        behaves like is_in_scope=false everywhere except the close") is a
--        measurement and not an opinion.
--   1611 employee who is TERMINATED during the proof through the real
--        employment route — so the two exclusion reasons stand side by side in
--        one database and the two reverse actions can be shown not to cross.
--        Reports to 1601 and has no evaluations, so terminating and reinstating
--        them cannot disturb the close comparison.
--
-- Grade coefficients differ (0.60 / 1.10 / 2.20 / 0.30) so the index arithmetic
-- cannot silently pass on a 1.0 fallback, and every seeded score differs so an
-- accidentally dropped evaluation moves a printed number instead of hiding in
-- an average.
--
-- The stand's period 2 is STARTED here (evaluation_started_at). That is a
-- stand-only change: without the second gate there are no tasks to lose, so
-- there is nothing to prove. Live is never touched by this file — the guard
-- below refuses any database whose name is not a mid-year stand.

DO $$
BEGIN
  IF current_database() !~ '^epe_mid_' THEN
    RAISE EXCEPTION 'Refusing to seed non-throwaway database: %', current_database();
  END IF;
END
$$;

BEGIN;

-- Idempotent teardown of anything a previous run of this seed left behind.
DELETE FROM performance_db.evaluation_scores
WHERE evaluation_id IN (
  SELECT id FROM performance_db.evaluations
  WHERE subject_id BETWEEN 1601 AND 1611 OR evaluator_id BETWEEN 1601 AND 1611
);
DELETE FROM performance_db.score_corrections
WHERE subject_id BETWEEN 1601 AND 1611 OR evaluator_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.evaluations
WHERE subject_id BETWEEN 1601 AND 1611 OR evaluator_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.period_scope_events
WHERE user_id BETWEEN 1601 AND 1611 OR actor_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.employment_events
WHERE user_id BETWEEN 1601 AND 1611 OR actor_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.auth_sessions WHERE user_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.password_reset_tokens WHERE user_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.period_results WHERE user_id BETWEEN 1601 AND 1611;
DELETE FROM performance_db.evaluation_period_participants WHERE user_id BETWEEN 1601 AND 1611;
UPDATE performance_db.evaluation_periods
SET evaluation_started_at = NULL, evaluation_started_by = NULL
WHERE evaluation_started_by BETWEEN 1601 AND 1611;
UPDATE performance_db.period_results
SET closed_by = NULL
WHERE closed_by BETWEEN 1601 AND 1611;
DELETE FROM performance_db.users WHERE id BETWEEN 1601 AND 1611;

-- ── Actors ───────────────────────────────────────────────────────────────────

INSERT INTO performance_db.users (
  id, full_name, email, role, department_id, grade_id, manager_id, job_title,
  is_project_participant, work_category, has_subordinates,
  can_evaluate, can_be_evaluated, token_version, join_date, password_hash
)
VALUES
  (1601, 'MY Admin', 'my.admin@sedamedical.com', 'admin',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C3'),
   NULL, 'Mid-year stand admin', false, 'general', false, true, false, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$8rTsZV1375CTLtZVZIL1dw$nNSebLD9eki_Egs1JE6DThjnJhamLC08LoSAz5H05hHjsAQ1zLtbFNAsxNrVCj6QvzlaHreBPZnDkH2RN-9Veg'),

  (1602, 'MY Manager', 'my.manager@sedamedical.com', 'manager',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S2'),
   1601, 'Mid-year stand manager', false, 'general', true, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$9-IWGrBx2yTTJAuK_oERXg$JIDwsjo16CY-mNV3vnMmwAHqUbSu0i4QvyLH68TAKGdhT7K-uw5Pr35ZOItqoKid1HObdv79SCLfrNRDFC9fQA'),

  -- THE SUBJECT. Project participant, so six manager-path criteria apply.
  -- join_date says February 2026: inside H1 on paper, which is precisely the
  -- case the owner reported.
  (1603, 'MY LateStart', 'my.latestart@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1602, 'Mid-year stand subject', true, 'project', false, true, true, 0,
   DATE '2026-02-05',
   '$scrypt$N=16384,r=8,p=1$ploEDUpqf5vH6s0fdKIH0w$vB6KvPWHGYKXVJmPK6Kf2mTpYau5om5YEZNGqbBVg-Gl2FB9P2GELteow_pDZS0gh0n3t8vam4xPzRDlz7OF4w'),

  (1604, 'MY Stayer A', 'my.stayer.a@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1602, 'Mid-year stand control A', false, 'general', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$_Q0Hj0SEDB7Mr_OZQFXN1A$BNu8flwitnEMJJovoZ4cCLriQY0Ya6zFYT6qIQGjh45QZBfY5gy-TVU4-mfnIsoK_t0_fKvsbe_Nvc0nkiw_Tg'),

  (1605, 'MY Stayer B', 'my.stayer.b@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1602, 'Mid-year stand control B', true, 'project', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$_1BGzJV8qd3Si3a6aO_DvA$tFgZ786s1i1z-3esAN-HljQsCA3fOJGK2ttcuJMFpRHgNRTTaXBLGB8NPpOgk-ZAyuTkHq1HQu1rl4f1W0B_cw'),

  (1606, 'MY CLevel', 'my.clevel@sedamedical.com', 'c_level',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'C1'),
   NULL, 'Mid-year stand c_level writer', false, 'general', false, true, false, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$hfp2Wlb6BokXCgxJoyHgag$xVhz6yl2ZxFeAGJCnD6Tp9cMV-1XjIzQfIX60WZBasawFjnp85RxtkrZC86irgbi9a63EAnsG-MgBtOmC62brw'),

  -- Hired after the period ended: already excluded, for a different reason.
  (1607, 'MY Newcomer', 'my.newcomer@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1601, 'Mid-year stand newcomer', false, 'general', false, true, true, 0,
   DATE '2026-07-06',
   '$scrypt$N=16384,r=8,p=1$2dJiVqDP6g8uq3_zWFfyig$XiGTBZ_4np3a4_4eajO_Yah5qVZLRuAAVqfHZN7MpLyRtaulKuNPKfuxibGCZtOOg5U_7-7_OQVZyb5yf7UYtg'),

  -- Never registered: password_hash stays NULL, so the shared invite is their
  -- only way in. 1608 is EXCLUDED during the proof and must still get in;
  -- 1609 is the control.
  (1608, 'MY Unregistered Excluded', 'my.unreg.excluded@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1601, 'Mid-year stand unregistered excluded', false, 'general', false, true, true, 0,
   DATE '2025-01-01', NULL),

  (1609, 'MY Unregistered Control', 'my.unreg.control@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1601, 'Mid-year stand unregistered control', false, 'general', false, true, true, 0,
   DATE '2025-01-01', NULL),

  -- No participants row for period 2 is inserted for this person below. This
  -- is the "added to the system after the period was created" case.
  (1610, 'MY NoRow', 'my.norow@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'S1'),
   1602, 'Mid-year stand missing participants row', false, 'general', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$S7ZGUppFdHIZHFJGbZi_FQ$tEi2aAq7ptaD_5c6xFoGu4TyOpru74pS2rprxYyX3-yIr8KYdu3byFb9iLRZK1YxBqKeOY7-qaoV32lcdyQRsw'),

  -- The leaver, terminated through the REAL employment route during the proof
  -- so both exclusion reasons exist side by side. No evaluations and no
  -- subordinates: terminating and reinstating them cannot move a single number
  -- in the close comparison.
  (1611, 'MY Leaver', 'my.leaver@sedamedical.com', 'employee',
   (SELECT min(id) FROM performance_db.departments),
   (SELECT id FROM performance_db.grades WHERE code = 'A'),
   1601, 'Mid-year stand leaver', false, 'general', false, true, true, 0,
   DATE '2025-01-01',
   '$scrypt$N=16384,r=8,p=1$Fca5tKN3DtmpyjSCA5IGhQ$orX5ovYu7qBOMFZZL7wirhUmDHctlheJg0ZnFvy8XyeOiEy0nayiKpqYLQdLrzi_XtVND64DMksKjypvmqntKg');

-- has_subordinates is owned by trg_update_has_subordinates, which fires on the
-- INSERTs above. Asserted rather than set.
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM performance_db.users u
  WHERE u.id BETWEEN 1601 AND 1611
    AND u.has_subordinates <> EXISTS (SELECT 1 FROM performance_db.users s WHERE s.manager_id = u.id);
  IF bad > 0 THEN
    RAISE EXCEPTION 'trg_update_has_subordinates disagreed with the graph on % fixture rows', bad;
  END IF;
END
$$;

-- ── Period membership (period 2 = H1-2026 on the restored copy) ──────────────
-- 1610 is deliberately absent from period 2. Everyone else is present.

INSERT INTO performance_db.evaluation_period_participants
  (period_id, user_id, is_in_scope, exclusion_reason)
VALUES
  (2, 1601, true,  NULL),
  (2, 1602, true,  NULL),
  (2, 1603, true,  NULL),
  (2, 1604, true,  NULL),
  (2, 1605, true,  NULL),
  (2, 1606, true,  NULL),
  (2, 1607, false, 'hired_after_period_end'),
  (2, 1608, true,  NULL),
  (2, 1609, true,  NULL),
  (2, 1611, true,  NULL),
  -- Every real person also has a row on the Annual 2026 container (period 5).
  -- 1610 gets one here on purpose: the missing row must be missing on ONE
  -- period only, so "no row" and "row present" can be compared inside one
  -- database. It is also what shows that excluding somebody from period 2
  -- leaves period 5 alone.
  (5, 1601, true,  NULL),
  (5, 1602, true,  NULL),
  (5, 1603, true,  NULL),
  (5, 1604, true,  NULL),
  (5, 1605, true,  NULL),
  (5, 1606, true,  NULL),
  (5, 1607, true,  NULL),
  (5, 1608, true,  NULL),
  (5, 1609, true,  NULL),
  (5, 1610, true,  NULL),
  (5, 1611, true,  NULL);

-- Open the campaign on the stand: without the second gate nobody has tasks.
UPDATE performance_db.evaluation_periods
SET evaluation_started_at = now(), evaluation_started_by = 1601
WHERE id = 2 AND evaluation_started_at IS NULL;

-- ── Evaluations ─────────────────────────────────────────────────────────────
-- Every score is distinct, so an evaluation that silently disappears moves a
-- printed average instead of hiding inside one.
--
-- calculated_score is the plain mean of the rows below it (formula #1 of
-- HANDOVER §4) and is written explicitly here, exactly as the submit route
-- would compute it.

-- 1602 → 1603 (manager). The ABOUT evaluation: must stop counting for 1603.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1603, 1602, 2, 7.0000, 'manager', false, 'completed', 'stand: manager on latestart', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,8),(4,7),(8,6),(12,7),(13,7),(14,7)) AS v(c,s);

-- 1602 → 1604 (manager)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1604, 1602, 2, 5.5000, 'manager', false, 'completed', 'stand: manager on stayer A', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,6),(4,5),(12,5),(14,6)) AS v(c,s);

-- 1602 → 1605 (manager)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1605, 1602, 2, 8.1667, 'manager', false, 'completed', 'stand: manager on stayer B', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,9),(4,8),(8,8),(12,7),(13,9),(14,8)) AS v(c,s);

-- 1601 → 1602 (manager). Feeds 1602's own final_rating and bonus_index.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1602, 1601, 2, 7.4000, 'manager', false, 'completed', 'stand: admin on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,8),(3,7),(4,7),(12,8),(14,7)) AS v(c,s);

-- 1603 → 1602 (upward). THE GAVE EVALUATION. It must survive 1603's exclusion
-- and keep feeding 1602's rating_upward to the digit.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1602, 1603, 2, 9.0000, 'subordinate', false, 'completed', 'stand: latestart upward on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,9),(3,9),(4,9),(12,9),(14,9)) AS v(c,s);

-- 1604 → 1602 (upward)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1602, 1604, 2, 4.0000, 'subordinate', false, 'completed', 'stand: stayer A upward on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,4),(3,4),(4,4),(12,4),(14,4)) AS v(c,s);

-- 1605 → 1602 (upward)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1602, 1605, 2, 6.0000, 'subordinate', false, 'completed', 'stand: stayer B upward on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (2,6),(3,6),(4,6),(12,6),(14,6)) AS v(c,s);

-- 1603 self-review (ABOUT)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, weighted_score,
     evaluation_source, is_self_evaluation, status, general_comment, updated_at)
  VALUES (1603, 1603, 2, 8.0000, 4.5000, 'self', true, 'completed', 'stand: latestart self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,8),(4,8),(12,8)) AS v(c,s);

-- 1604 self-review
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, weighted_score,
     evaluation_source, is_self_evaluation, status, general_comment, updated_at)
  VALUES (1604, 1604, 2, 5.0000, 1.5000, 'self', true, 'completed', 'stand: stayer A self', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (3,5),(4,5),(12,5)) AS v(c,s);

-- 1606 → 1603 (c_level_direct, c_level_only criteria). ABOUT.
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1603, 1606, 2, 6.5000, 'c_level_direct', false, 'completed', 'stand: c_level on latestart', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,7),(10,6)) AS v(c,s);

-- 1606 → 1602 (c_level_direct)
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES (1602, 1606, 2, 5.5000, 'c_level_direct', false, 'completed', 'stand: c_level on manager', now())
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,6),(10,5)) AS v(c,s);

COMMIT;
