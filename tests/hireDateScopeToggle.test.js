import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import {
  mkdtempSync,
  readFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = mkdtempSync(join(tmpdir(), 'hire-date-scope-'));
execFileSync('python3', [
  join(root, 'scripts', 'build_route_guard_workflows.py'),
  '--output-directory', out,
], { cwd: root, stdio: 'pipe' });

const read = (path) => readFileSync(join(root, path), 'utf8');
const load = (file) => JSON.parse(readFileSync(join(out, file), 'utf8'));
const nodeCode = (workflow, name) => {
  const found = workflow.nodes.find((node) => node.name === name);
  assert.ok(found, `node ${name} exists`);
  return found.parameters.jsCode ?? found.parameters.query ?? '';
};

test('migration is additive: card events plus a two-direction manual override', () => {
  const sql = read('migrations/017_add_employee_card_events_and_scope_override.sql');
  assert.match(sql, /ADD COLUMN IF NOT EXISTS scope_override/);
  assert.match(sql, /included_by_admin/);
  assert.match(sql, /excluded_by_admin/);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS performance_db\.employee_card_events/);
  assert.match(sql, /actor_id/);
  assert.match(sql, /occurred_at/);
  assert.match(sql, /changes\s+jsonb/);
  assert.doesNotMatch(sql, /\bDROP TABLE\b|\bDELETE FROM\b|\bTRUNCATE\b/);
});

test('period creation uses the final-three-calendar-month rule and the new reason', () => {
  const code = nodeCode(load('manage-periods.json'), 'Build Create SQL');
  assert.match(
    code,
    /date_trunc\('month', '\$\{endDate\}'::date\)::date[\s\S]*interval '2 months'[\s\S]*interval '1 day'/
  );
  assert.match(code, /THEN 'insufficient_tenure'/);
  assert.doesNotMatch(
    code,
    /WHEN u\.join_date > '\$\{endDate\}'::date THEN 'hired_after_period_end'/
  );
});

test('save-user refuses partial existing rows and accepts an empty hire date', () => {
  const validate = nodeCode(load('save-user.json'), 'Validate User Data');
  assert.match(validate, /INCOMPLETE_USER_ROW/);
  assert.match(validate, /'role', 'work_category'/);
  assert.match(validate, /'join_date'/);
  assert.match(validate, /const joinDateSql = rawJoinDate \?/);
  assert.match(validate, /: 'NULL'/);
});

test('hire-date recompute preserves manual and terminated rows and refuses data loss', () => {
  const build = nodeCode(load('save-user.json'), 'Build User Upsert');
  assert.match(build, /ps\.scope_override IS NULL/);
  assert.match(build, /ps\.old_reason = 'excluded_by_admin'/);
  assert.match(build, /ps\.user_terminated OR ps\.old_reason = 'terminated'/);
  assert.match(build, /blocked_periods AS/);
  assert.match(build, /refused_has_evaluations/);
  assert.match(build, /employee_card_events/);
  assert.match(build, /period_scope_events/);
  assert.match(build, /ORDER BY o\.period_id/);
});

test('manual off has no confirmation escape hatch; manual on records precedence', () => {
  const workflow = load('manage-period-scope.json');
  const validate = nodeCode(workflow, 'Validate Exclude');
  const exclude = nodeCode(workflow, 'Build Exclude SQL');
  const include = nodeCode(workflow, 'Build Include SQL');
  assert.doesNotMatch(validate, /confirm_existing_evaluations/);
  assert.match(exclude, /if \(total > 0\)/);
  assert.doesNotMatch(exclude, /prev\.confirmed/);
  assert.match(exclude, /scope_override = 'excluded_by_admin'/);
  assert.match(include, /scope_override = 'included_by_admin'/);
  assert.match(include, /insufficient_tenure/);
});

test('admin payload and modal expose named per-period toggles and visible outcomes', () => {
  const query = nodeCode(load('admin-users-data.json'), 'Build Users Query');
  assert.match(query, /AS period_scopes/);
  assert.match(query, /'period_name', p\.name/);
  assert.match(query, /'scope_cutoff_date'/);
  assert.match(query, /'scope_override', pp\.scope_override/);

  const modal = read('src/components/admin/UserModal.jsx');
  assert.match(modal, /canManageScope &&/);
  assert.match(modal, /Дата приёма/);
  assert.match(modal, /Участвует в оценке/);
  assert.match(modal, /Что произошло с охватом/);
  assert.match(modal, /Журнал изменений/);
});

test('one admin-only read surface unifies card, scope and employment history', () => {
  const workflow = load('manage-period-scope.json');
  const paths = workflow.nodes
    .filter((node) => node.type === 'n8n-nodes-base.webhook')
    .map((node) => node.parameters.path);
  assert.ok(paths.includes('api/admin/employee-events'));
  const query = nodeCode(workflow, 'Build Employee Events Query');
  assert.match(query, /employee_card_events/);
  assert.match(query, /period_scope_events/);
  assert.match(query, /employment_events/);
});

test('actor identity in save-user comes from guard, not from body; invalid actor is refused', () => {
  const validate = nodeCode(load('save-user.json'), 'Validate User Data');
  // Must read from guard output — a body field must never supply the actor.
  assert.match(validate, /actorId = Number\(guard\.identity\.id\)/);
  assert.doesNotMatch(validate, /body\.actor_id|body\.admin_id/);
  // Server must refuse a non-finite or zero actor rather than record a phantom id.
  assert.match(validate, /INVALID_ACTOR/);
  assert.match(validate, /!Number\.isFinite\(actorId\)/);
});

test('whole-card rollback: Format Response emits 409 with HIRE_DATE_SCOPE_HAS_EVALUATIONS and full wording', () => {
  const format = nodeCode(load('save-user.json'), 'Format Response');
  assert.match(format, /HIRE_DATE_SCOPE_HAS_EVALUATIONS/);
  assert.match(format, /http_status: 409/);
  // The message must make clear that NO field was saved, not just the hire date.
  assert.match(format, /Карточка не сохранена целиком/);
  assert.match(format, /Все поля, включая остальные правки, остались прежними/);
  // The blocked-period list is returned so the UI can surface the evaluation counts.
  assert.match(format, /refused_has_evaluations/);
  assert.match(format, /blockedPeriods/);
});

test('scope and events endpoints require a positive integer user_id', () => {
  const workflow = load('manage-period-scope.json');
  // Both manual-toggle endpoints must guard the user_id field.
  assert.match(nodeCode(workflow, 'Validate Exclude'), /INVALID_USER_ID/);
  assert.match(nodeCode(workflow, 'Validate Include'), /INVALID_USER_ID/);
  // The events endpoint must refuse a completely absent user_id (not just an invalid one),
  // so it never returns the unfiltered cross-employee event log.
  const eventsQuery = nodeCode(workflow, 'Build Employee Events Query');
  assert.match(eventsQuery, /USER_ID_REQUIRED/);
  assert.match(eventsQuery, /if \(!userFilter\)/);
});

test('employee-facing payload distinguishes new manual marks from legacy late-hire marks', () => {
  const authOut = mkdtempSync(join(tmpdir(), 'hire-date-auth-'));
  execFileSync('python3', [
    join(root, 'scripts', 'build_auth_workflows.py'),
    '--output-directory', authOut,
  ], { cwd: root, stdio: 'pipe' });
  const workflow = JSON.parse(
    readFileSync(join(authOut, 'protected-employees.json'), 'utf8')
  );
  const query = nodeCode(workflow, 'Build Identity-Bound Query');
  const format = nodeCode(workflow, 'Format Response');
  assert.match(query, /epp\.scope_override/);
  assert.match(query, /AS actor_scope_override/);
  assert.match(format, /actor_scope_override: row\.actor_scope_override \|\| null/);
});
