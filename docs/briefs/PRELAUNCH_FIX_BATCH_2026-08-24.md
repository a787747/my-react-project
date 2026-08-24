# BRIEF: Prelaunch fix batch — BUG-051 matrix alignment, /tmp dump cleanup, small riders

## Context
The browser walkthrough (docs/BROWSER_WALKTHROUGH_2026-08-2x.md) retired the last
prelaunch debt and filed two findings. This batch closes them. Launch stays
paused; live stays campaign-inert.

## Outcome
1. **BUG-051.** The admin evaluations matrix renders a fixed, shared column list
   for every row (the final-scores screen already shows the correct shape):
   non-project rows show N/A in the project columns instead of shifting C-level
   cells two columns left. Prove in a real browser on a stand with both a
   project and a general subject side by side: every cell under its own header,
   DOM assertion or screenshot per row type. Money values themselves must not
   change — reconcile one project and one general row to the recorded
   walkthrough figures.
2. **BUG-053 (Alexander approved).** Delete the seven world-readable live-data
   dumps from VPS /tmp (list them in the report with sizes and dates before
   deletion; verify local dated copies exist in backups/ for each — if any has
   no local copy, move it into the root-only backup directory instead of
   deleting). Add to PROJECT_RULES.md: stand and rollback artifacts never live
   in /tmp; use a root-only directory; teardown includes their removal.
3. **Refresh check by hand.** In the stand browser, as a manager: submit an
   evaluation and watch the dashboard WITHOUT reloading — does the card state
   update? If it does not, file a bug with severity by launch-day impact and
   your read on the cause; fix only if it is a one-liner under the walkthrough's
   latitude rules.
4. **Riders.** If EVALUATION_METHODOLOGY.md is attached: commit verbatim to
   docs/, approval line in DECISIONS.md, link from HANDOVER §10. Make
   check_live_drift.py list generator outputs absent from live as explicit
   warnings instead of silently tolerating them. Reconcile HANDOVER §10
   counters. bugs.md closures with evidence; PROGRESS.md; report
   docs/PRELAUNCH_FIXES_2026-08-2x.md; commit AND push; deploy with the
   established drift-check + dump discipline.

## Boundaries
No activation, no campaign writes on live, no mail; Auth Guard canonical
untouched; §4 formulas and money computation untouched — item 1 is presentation
only, and the acceptance proves values unchanged; stand torn down.

## Acceptance
Browser evidence for item 1 (both row types), the /tmp listing before/after with
the local-copy verification, the refresh answer with evidence, suite green,
drift clean before and after, live period state verified untouched.
