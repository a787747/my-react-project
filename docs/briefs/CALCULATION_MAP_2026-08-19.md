You are the executor for EPE. Read `AGENTS.md` first and work under it. Then read `HANDOVER.md` — §4 in full, twice — and `API_CONTRACT.md` §4–§5. Do not read the auth reports; they are noise for this task.

Save this brief verbatim as `docs/briefs/CALCULATION_MAP_2026-08-19.md`. Deliverable: `docs/CALCULATION_MAP.md`.

This is a READ-ONLY task. It changes nothing. It answers the last significant unknown before H1: what every number in the system is, where it is computed, and what it depends on. It must precede any change to submit-evaluation and self-review-submit, and it is the evidence base for the H1 + H2 → annual aggregation decision (DECISIONS.md D-0819-1, being added by a parallel session; do not touch that file).

# Given — do not re-open

The three scoring formulas are intentional (HANDOVER §4):
- Plain average of criterion scores = a RATING, 1–10, feedback to the person (manager / subordinate / c_level_direct).
- Weighted sum ÷ Σweights × grade coefficient = self-review value.
- Weighted sum WITHOUT ÷ Σweights × grade coefficient = a BONUS ALLOCATION INDEX, not a rating; more criteria = deeper project involvement = larger share (admin matrix / final score).
Self-review never feeds bonuses; it exists to expose a gap between self-rating and manager rating. "These three are inconsistent with each other" is not a finding. Findings are things that contradict this table or that it does not describe.

# Outcome

`docs/CALCULATION_MAP.md` with:

A. Inventory — one row per number the system computes, stores or displays. Columns: number · screen/consumer (component, role) · route · where computed (client file+function / n8n Code node / SQL, named) · exact formula · inputs · stored? where · live-joined or snapshot (does it change if grades / weights / criteria / hierarchy change later?) · period filter (how the query decides which period counts) · rounding/scale. Cover at least: manager, upward and c_level_direct ratings; self-review value; weighted_score vs final_score on self-review-submit; final_score on submit-evaluation (client- or server-computed?); my-profile.stats; get-my-manager last/previous scores; evaluation-history; matrix per-criterion manager_score / mid_level_correction / c_level_correction and the UI's getFinalScore averaging; analytics; hr/evaluation-status flags.

B. Findings — answers, in this order, each with evidence:
1. Where self-review is shown next to the manager rating, and whether the comparison is raw (1–10 average vs weighted × grade coefficient, up to 2.20) or normalized. If raw, the "gap" is driven by grade, not disagreement.
2. Which number was used in December 2025 — manager-card rating or admin-matrix index. Look in the 2025 archive: what final_score values are stored per source, whether matrix values are stored or only computed on the fly, whether corrections exist.
3. Where final_score is computed for each write path, and whether the server validates or recomputes it.
4. How mid_level / c_level corrections enter any final number, and whether any exist in 2025.
5. Period filter per query — by period_id, is_active, date range, or none. H1 and H2 will share epe_2026; every unfiltered query is an H2 problem — list them.
6. Grade coefficient, criterion weight, score_coefficients, manager_id: live-joined at read time or stored on the evaluation?
7. Criteria set per subject: how target_audience maps to a person, how many criteria each of the 89 currently gets, whether that count is stored or recomputed. Produce the distribution (project vs general, N criteria each) — it is the input to Alexander's classification check.
8. Scale and rounding: 1–10 UI vs 0–10 checks; where rounding happens; is zero valid anywhere.

C. Reproduction proof — for at least 10 evaluations from the 2025 archive across sources (manager, subordinate, self, c_level_direct if present), the map's formula reproduces the stored final_score from the stored score rows and the inputs the map names. Every mismatch is a finding with the numbers. A map without this is a hypothesis.

# Boundaries

Read-only: no workflow edit, no migration, no data change, no "quick fix". The 2025 archive may be queried read-only — fingerprint `21d323b0…` before and after, both in the report. n8n public dump SHA-256 identical before and after, or the diff explained. Do not classify the three intentional formulas as defects or propose which is "right". Do not touch the frontend build or deploy. Where a value cannot be traced with certainty, write "unverified — because …"; do not fill the gap with a plausible reading.

# Acceptance criteria

Every inventory row traced to a named location — no "computed somewhere". Reproduction proof present. Questions 1–8 each answered or explicitly unverified with reason. Period-filter column filled for every query. Fingerprints unchanged.

# Surface for decision

Close the report with: whether the self-vs-manager comparison as it exists is grade-driven; evidence for the December question; every live-joined value whose history would change if a grade, weight, criterion or manager changes during a period (this becomes the freeze rule); every query without a period filter; every place the server stores a client-computed number unvalidated; the criteria-count distribution across the 89. No recommendation on the formulas themselves. One session, one report.
