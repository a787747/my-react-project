# EPE Review Checklist

Load this only when doing review work. Standard passes (logic bugs, security, architecture, performance, tests) apply as usual; below are the checks specific to this system. Verify each one against the actual code, schema, workflow export, or logs — not against what the docs claim.

## 1. Historical data integrity

- Where do last year's scores physically live? Is there a backup? Restore-tested, or assumed?
- Recompute one known historical result from its source inputs today. Does it match the stored value? If not, the scoring formula has already drifted and the drift is undocumented.
- Can a completed period be edited after the fact, and is that edit recorded?

## 2. Period model

- Is there a first-class "evaluation period" entity, or is the year implied?
- Do unique keys include the period? Is any year hardcoded in workflow nodes, queries, sheet ranges, or file names?
- Are the scale, criteria, and weights versioned? If weights change between H1 and H2, does last year's score stay reproducible under the rules that produced it?
- Walk the scenario end to end: H1 entered now, H2 in six months, annual in January. Name the exact place it breaks.

## 3. Single source of truth for scoring

- Where is the final score actually computed — n8n nodes, SQL, spreadsheet formulas, frontend?
- Is the same formula implemented in more than one place? Divergent copies are why an employee and a manager see different numbers.
- Are rounding, missing-value handling, and mid-period joiners handled once, or ad hoc per site?

## 4. n8n as backend

Check each specifically; do not assume:

- Are workflows exported to git, or do they exist only inside the instance? Any UI edit outside git is unrecoverable and untraceable.
- Are webhooks authenticated? Anyone with the URL can otherwise submit or read evaluations.
- Is the flow idempotent? A retried or double-fired run must not create duplicate scores.
- Where do credentials live, and what happens to them if the container is lost?
- What is the state of a record if the container restarts mid-execution?
- Are there structured logs sufficient to reconstruct an incident afterwards?

## 5. Access and confidentiality

Evaluation scores are sensitive HR data.

- Who can read whose scores? Are the roles employee / manager / HR / executive actually separated, and enforced server-side rather than hidden in the UI?
- Do scores leak into logs, exports, error messages, notification payloads, or URLs?
- Is there an audit trail of who changed a score and when?

## 6. Methodology defects (report as bugs)

- Period goals not fixed at the start of the period → the evaluation is done from memory and cannot be defended.
- No calibration step across managers → one manager's "4" is not another's "4".
- Central tendency: everyone lands mid-scale → the system does not discriminate and adds no information.
- No mandatory comment on extreme scores.
- No self-assessment or second input; single-rater scores only.
- Recency: the last month dominates a six-month period.
- One scale applied to all staff. The three role groups are structurally different work — project delivery (BOQ accuracy, milestone dates, client acceptance, post-handover claims, training quality), routine supply (OTIF, order cycle, document errors, overdue rate, claim handling), and back office (internal SLA, document accuracy, no downstream failures). Different criteria sets normalised to a comparable final score, not one questionnaire for everyone.

## 7. Report format

Write to `docs/REVIEW.md`:

1. Overall state, three sentences, plus a health rating.
2. What is done well — real items, not filler.
3. Quick wins: under five minutes each, meaningful effect.
4. Findings by severity (critical / high / medium / low / performance). Each with location, consequence, fix.
5. Security section, always present, even if clean.
6. Architecture observations: what becomes painful as this grows.
7. **HR methodology risks** — separate from technical findings, each with its management consequence.
8. **H1 readiness: yes / no** — and the minimum blocker list.
9. Recommended action order, five to seven items.

Report everything you found. Filtering by importance is a separate pass, done with Alexander.
