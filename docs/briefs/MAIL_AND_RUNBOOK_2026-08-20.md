You are the executor for EPE. Read `AGENTS.md` first and work under it. Then read `HANDOVER.md` §2, §7 and `docs/LAUNCH_PREP_2026-08-19.md` §2, §5 and the "Surface for decision" section. Nothing else.

Save this brief verbatim as `docs/briefs/MAIL_AND_RUNBOOK_2026-08-20.md`. Report to `docs/MAIL_AND_RUNBOOK_<date>.md`.

Architect statements are hypotheses; verify, and where the code disagrees, the code wins and the disagreement goes into the report.

# Context

Invitation waves start 26 Aug. Employees can register only if the verification code from `noreply@sedamedical.com` reaches their inbox. Today: DKIM not published, n8n SMTP host unverified, no inbox test done, and the `verify-invite` throttle is keyed by IP behind Caddy — if that IP is the proxy's, the limit is global.

# Outcome

1. **System mail provably reaches an inbox.** Establish which SMTP host and account n8n's `SMTP account` credential uses (you have root and the n8n encryption key; do not paste secrets into the report — host, port, auth user domain are enough). Confirm that host is covered by the current SPF for `sedamedical.com`; if it is not, say exactly what SPF must become. Send one verification-code email (or the reset-mail path, whichever is cleaner) to `[COMPANY_MAILBOX]` and `[EXTERNAL_MAILBOX]` only, and report for each: inbox or spam, and the SPF/DKIM/DMARC results from the received headers. Alexander will publish DKIM in Google Workspace in parallel; if DKIM is live by the time you test, report it; if not, report the expected effect and the exact TXT record name to check.

2. **Throttle keyed on the real client.** Verify what IP `verify-invite` (and any other per-IP limit) actually sees behind Caddy. If it is the proxy address, make it use the client IP from the forwarding header — trusting that header only because port 5678 is closed to the internet and Caddy is the sole path; state that reasoning in the report. Prove it: two different client IPs get independent counters. If trusting the header is not possible cleanly, remove the verify-invite throttle for H1 and say so — an unregisterable company is worse than an unthrottled token-validity check.

3. **Launch runbook** — `docs/LAUNCH_RUNBOOK_H1.md`, written for Alexander, not for an engineer. 31 Aug morning: what he clicks (Admin → Periods → activate H1), what he must see afterwards (`in scope = 87`, a manager sees tasks, an employee sees self-review), what to do if something is wrong (deactivate the period → lists go empty, nobody can write; whom to call), and what he must NOT do during the campaign (no criteria/weights/coefficient edits — routes are frozen anyway; no classification edits after the first submission — 409 by design; no period switch). Also: how to read the registered-users badge during the waves, and the one SQL from `INVITATION_WAVES.md` §4 if he wants the number. One page.

# Boundaries

- No scoring change, no guard change, no deferred route, no schema change.
- Test mail only to the two named mailboxes. Throwaway users/codes/throttle rows removed; end state as in `LAUNCH_PREP` (registered = 1, evaluations = 0, sessions = 0, H1 draft/inactive).
- Dumps + 2025 fingerprint before/after if any workflow is modified.

# Acceptance criteria

- SMTP host/port/auth-domain named; SPF coverage stated; two received-header verdicts (inbox/spam, SPF/DKIM/DMARC pass/fail).
- Throttle proof with two client IPs, or the throttle removed with the reason.
- Runbook exists, one page, readable by a non-developer.
- End-state block; report written; `HANDOVER.md` §7 one paragraph.

# Surface for decision

- If the SMTP host is not Google: the SPF change Alexander must make, verbatim.
- If DKIM still absent at test time: recommend go/no-go for 26 Aug with the measured spam result.
- Anything in the runbook Alexander must decide (e.g. who is the second person with admin access on launch day — today there is none).
