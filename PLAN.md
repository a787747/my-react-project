# Evaluation Portal Revival Plan

## Vision
Restore the employee evaluation portal to a secure, maintainable, production-ready state, then evolve it around updated business priorities.

## Current Architecture
- Frontend: React 19, Vite 7, React Router 7, Tailwind CSS 3
- Backend: n8n webhook workflows
- Database: PostgreSQL, schema `performance_db`
- Legacy production frontend: `http://135.232.120.40:8080`
- Legacy backend host: `92.51.45.147`
- Repository: GitHub `a787747/my-react-project`

## Ground Rules
- Keep project documentation in this repository.
- Do not commit, push, or deploy unless explicitly requested.
- Preserve existing data and infrastructure until backups and ownership are confirmed.
- Fix root causes in small, verifiable steps.

## Phase 0 — Establish Baseline
- [x] Install locked frontend dependencies.
- [x] Verify production build.
- [x] Verify local development server and client-side routes.
- [x] Probe the legacy backend host and n8n port.
- [x] Run lint and dependency security checks.
- [x] Identify and verify the former public frontend URL.
- [ ] Identify the frontend deployment platform and service manager.
- [ ] Confirm SSH access and inspect the legacy server without changing it.
- [ ] Inventory n8n, PostgreSQL, reverse proxy, TLS, backups, and service managers.

## Phase 1 — Recover Backend Safely
- [ ] Create verified backups of the database, n8n workflows, credentials, and server configuration.
- [ ] Determine why ports 80, 443, and 5678 are closed.
- [ ] Restore n8n and PostgreSQL in a controlled environment.
- [ ] Add an authenticated health endpoint.
- [ ] Move public API traffic behind HTTPS and a reverse proxy.
- [ ] Verify migrations against the actual production schema.

## Phase 2 — Stabilize the Application
- [ ] Fix runtime-significant lint errors first.
- [ ] Remove duplicate and hard-coded API URLs.
- [ ] Update vulnerable production dependencies and rerun regression checks.
- [ ] Add automated tests for authentication, roles, evaluations, and score calculations.
- [ ] Add reproducible local and production environment documentation.

## Phase 3 — Product Reprioritization
- [ ] Reconfirm roles, evaluation workflow, scoring model, and reporting needs.
- [ ] Classify existing features as keep, change, remove, or defer.
- [ ] Convert approved priorities into small milestones with acceptance criteria.

## Phase 4 — Release Readiness
- [ ] Add CI checks for lint, tests, build, and dependency auditing.
- [ ] Verify authorization server-side for every privileged workflow.
- [ ] Run security and data-integrity reviews.
- [ ] Prepare a deployment and rollback runbook.
- [ ] Perform staging acceptance testing before production release.

## Known Risks
- The production frontend is publicly available over plain HTTP on port 8080.
- The legacy host responds to ping and SSH, but web and n8n ports refuse connections.
- The frontend currently depends on an insecure hard-coded HTTP API URL.
- The repository has a large uncommitted working tree and only a minimal committed history.
- There are currently no automated tests in `package.json`.
- Production dependency audit reports high-severity advisories.
