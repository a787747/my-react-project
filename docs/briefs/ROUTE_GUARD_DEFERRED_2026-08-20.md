You are the executor for EPE. Read `AGENTS.md` first and work under it. Then read `docs/HANDOVER.md` (2026-08-20) — §4 before anything about formulas, §7 "September" list. Then `docs/ROUTE_GUARD_H1_2026-08-19.md` as the pattern this brief repeats. `docs/CALCULATION_MAP.md` only where a route's data shape is unclear.

Context: 25 launch workflows are active and PROVEN — they are out of scope and must not be edited. H1 (id=2) is draft; campaign starts 31 Aug. The remaining ~16 deferred API workflows (matrices, analytics, corrections, criteria/admin management, reporting) must be behind `EPE: Auth Guard` before results work starts in September. Doing it now, while H1 is draft, keeps proof-cleanup cheap. The list and rules below are hypotheses; the workflow export and the code win.

Outcome:
- Every deferred API workflow is behind the guard: identity only from guard.identity, every client-supplied identity field ignored, per-route authorization enforced.
- Hypothesised route rules to verify and refine (the reporting/read routes: evaluations-matrix, all-evaluations, evaluation-details-by-user, analytics, get-admin-data → admin + c_level; manager-subordinates-matrix → also manager, but strictly manager_id = actor; employee-self-review → no known call site, see surface; the write routes: score-correction → correction_level c_level only for c_level role, mid_level rule to verify against how it was used in 2025 and surface; manage-criteria save/delete and update-admin-data → admin only AND rejected (409) while a period is active — same freeze pattern migration 012 applied to classification/coefficients).
- Ownership on reads: a manager must not pull another manager's subordinates matrix; identity-conflict proof per route that accepts an identity parameter.
- No route logic, SQL shape, computed number, or response contract changes beyond the guard insertion and the authorization/freeze checks. Known data defects (period filters, manager_score source-vs-role, corrections period column) are September logic work — record where you see them, fix nothing.

Boundaries:
- ZERO edits to the 25 active workflows and to `EPE: Auth Guard` itself (md5 must be unchanged at the end). If a deferred route needs something the guard cannot express, surface it — do not fork the guard.
- Activation state at the end = as at the start: the same 25 active. Temporary activation of deferred routes for proof is fine; deactivate after.
- Proof writes only while H1 stays draft or under temporary activation you fully roll back, as in the dress rehearsal: at the end evaluations=0, corrections=0, sessions=0, registered=1 (Alexander), H1 draft/inactive, invite id=4 unused.
- epe_2026 dump before; n8n public dump SHA-256 before/after with any diff explained; 2025 fingerprint 21d323b0… unchanged. No schema change (a corrections period column is explicitly NOT this brief).
- If 31 Aug arrives mid-brief or Alexander sends the invitation and real registrations appear: stop write-proofs immediately and report what is done — do not test against a live campaign.

Report to docs/ROUTE_GUARD_DEFERRED_2026-08-2x.md, same format as ROUTE_GUARD_H1:
per-route evidence table (no_token/forged/expired/wrong_role/ownership/valid),
identity-conflict proofs, freeze-rule proofs for the write routes, final workflow
activation list by name, cleanup proof, dumps and fingerprint.

Surface for decision (do not resolve silently):
- employee-self-review: no React call site exists — guard it, or delete the workflow?
- get-admin-data: same question (contract says nothing calls it).
- Who besides admin sees company-wide reporting: does HR get all-evaluations / analytics / details-by-user, or admin+c_level only? Report current audience assumptions in the UI, recommend, let Alexander decide.
- mid_level score-correction: who exactly may write it (which roles/relations), based on how the three 2025 corrections were actually made.
- c_level_direct submit currently returns 422 "until the matrix is back" — guarding the matrix makes it technically possible again. Re-enable now or keep 422 until September? (Architect's pick: keep 422; re-enable with the results work.)
