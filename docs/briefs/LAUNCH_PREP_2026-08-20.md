You are the executor for EPE. Read `AGENTS.md` first and work under it. Then read `HANDOVER.md`, `docs/ROUTE_GUARD_H1_2026-08-19.md`, and `bugs.md` (BUG-007, BUG-008). From `docs/CALCULATION_MAP.md` read only §B.3. Nothing else.

Save this brief verbatim as `docs/briefs/LAUNCH_PREP_2026-08-20.md`. Your report goes to `docs/LAUNCH_PREP_<date>.md`.

Everything below that describes the code is a hypothesis from an architect with no code access. Verify before acting; where the code disagrees, the code wins and the disagreement goes into the report.

# Context

The 19 launch routes are guarded, active, and accepted (report above). H1 (period id=2) is draft/inactive. Invitations go out from 26 Aug in waves, managers first; campaign starts 31 Aug. This brief makes the system ready for both. Nothing in it changes a scoring formula, the guard, or the deferred routes.

# Outcome

1. **BUG-007 closed.** Campaign employee lists, manager task status, and HR/status denominators include only people in scope in `evaluation_period_participants` for the active period; the organisation tree outside campaign views is untouched. Esenova no longer appears as a task for her manager; "all subordinates evaluated" can actually become true. Report what campaign views show when no period is active.

2. **Pre-auth abuse limits.** `send-verification-code` gets a resend cooldown; `verify-invite` gets a basic request throttle. The brief that kept pre-auth routes unchanged is superseded for these two routes only. No other pre-auth behaviour changes.

3. **Write-path integrity (addendum item 2 of the route brief, not yet done).** After any submit or update on the manager/subordinate paths, the stored rating equals the plain average of its own stored score rows; score values are validated 1–10 server-side; out-of-range or mismatched client numbers cannot be stored. Same formula, no scoring change. `weighted_score` on self-review is untouched.

4. **Rehearsal.** End-to-end on the production bundle with real user rows via temporary sessions (never by setting passwords on real accounts): employee self-review + upward, manager → subordinate, manager edit via update, one HR status view, one admin classification edit before the first submission and its 409 after. H1 is activated temporarily for this and returned to draft/inactive; rehearsal rows are removed with dumps before and after (no clear-test route exists any more — that is deliberate). **Verify and ensure that the classification/coefficient freeze lifts once rehearsal rows are deleted** — Alexander must still be able to edit classification between rehearsal and 31 Aug.

5. **Invitations.** The system sends only verification-code and reset emails; the invitation itself is an email Alexander sends with the shared registration link. Produce `docs/INVITATION_WAVES.md`: wave list (managers first, then by department), a registration one-pager for employees, an invitation email draft in Russian with a clearly marked slot for a second language (Alexander decides), and a query or admin view that shows who has registered. Check deliverability of the system's own emails: sending domain, SPF/DKIM/DMARC, a test send to at least one external mailbox and one company mailbox, spam-folder result. Anything that needs DNS is Alexander's action — state it exactly.

6. **Housekeeping.** `DECISIONS.md` and `PROJECT_DECISIONS.md` merged into one register, the other left as a pointer. Confirm in the report: `registered users` count (expected 1) and that no real user's `password_hash` was set during any acceptance; whether `acceptance_tokens.json` / `browser_accounts.json` were ever committed to git — if yes, say so and what was rotated. Verify the guarded `periods/create` handles `period_type` and `status` correctly (HANDOVER §7.3).

# Boundaries

- No scoring-formula change; no change to `EPE: Auth Guard`; deferred routes stay inactive.
- No schema change unless required for item 3 — surface first.
- Dumps (`epe_2026`, n8n public) with SHA-256 before and after; 2025 fingerprint `21d323b0…` before and after.
- No email to any employee is sent by you except deliverability tests to mailboxes Alexander names.
- End state: H1 draft/inactive, `evaluations=0`, `active_sessions=0`, temporary artefacts 0, activation state by workflow name unchanged from the start of the brief.

# Acceptance criteria

- BUG-007: proof that the excluded pair is absent from their managers' campaign lists and denominators, with the 87-in-scope count visible somewhere verifiable.
- Cooldown/throttle: proof of the limit (second call inside the window rejected), and the numbers chosen.
- Integrity: tampered `final_score` → stored value equals the mean of rows; out-of-range score → 4xx and no row.
- Rehearsal: per-step result, end state block, freeze-lift proof.
- `docs/INVITATION_WAVES.md` exists with all five parts; deliverability result with the actual sender domain and DNS status.
- Housekeeping answers, one line each.
- Report written; `HANDOVER.md` §3/§7 updated in one paragraph each; `bugs.md` updated.

# Surface for decision — do not resolve silently

- Anything that needs a frontend rebuild (state what, and whether it can wait).
- What campaign views should show with no active period (your recommendation).
- Any DNS/mailbox action needed from Alexander for deliverability.
- Whether the shared single invite link is acceptable for the waves (BUG-008) or per-wave tokens are worth it now.
- Cooldown/throttle values you chose, if they could block a legitimate employee.
