/**
 * D-0824-3 upward-channel seal — static compared values from generated
 * live-shaped workflows. Read-only: no workflow PUT.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const H1_DIR = mkdtempSync(join(tmpdir(), 'upward-h1-'));
const AUTH_DIR = mkdtempSync(join(tmpdir(), 'upward-auth-'));
const DEF_DIR = mkdtempSync(join(tmpdir(), 'upward-def-'));

execSync(
  `python3 "${join(REPO_ROOT, 'scripts', 'build_route_guard_workflows.py')}" --output-directory "${H1_DIR}" 2>&1`,
  { cwd: REPO_ROOT },
);
execSync(
  `python3 "${join(REPO_ROOT, 'scripts', 'build_auth_workflows.py')}" --output-directory "${AUTH_DIR}" 2>&1`,
  { cwd: REPO_ROOT },
);
execSync(
  `python3 "${join(REPO_ROOT, 'scripts', 'build_route_guard_deferred.py')}" --output-directory "${DEF_DIR}" 2>&1`,
  { cwd: REPO_ROOT },
);

const load = (dir, file) => JSON.parse(readFileSync(join(dir, file), 'utf8'));
const jsOf = (wf, name) => {
  const node = (wf.nodes || []).find((n) => n.name === name);
  assert.ok(node, `node "${name}" must exist in ${wf.name}`);
  return node.parameters?.jsCode || '';
};
const allJs = (wf) => (wf.nodes || []).map((n) => n.parameters?.jsCode || '').join('\n');
const guardRoles = (wf) => {
  const js = jsOf(wf, 'Prepare Guard Input');
  const match = js.match(/required_roles:\s*(\[[^\]]*\])/);
  assert.ok(match, `${wf.name}: Prepare Guard Input must declare required_roles`);
  return match[1];
};

test('evaluation-details: evaluated manager is not a reader (404)', () => {
  const js = jsOf(load(H1_DIR, 'evaluation-details.json'), 'Build Details Query');
  const privileged = "const privileged = ['admin', 'c_level'].includes(actorRole);";
  const where = `AND (
          \${privileged}
          OR e.evaluator_id = \${actorId}
          OR (e.subject_id = \${actorId} AND e.is_self_evaluation = true)
        )`;
  assert.equal(js.includes(privileged), true, `privileged compared: ${privileged}`);
  assert.equal(js.includes("OR e.evaluator_id = ${actorId}"), true);
  assert.equal(
    js.includes('(e.subject_id = ${actorId} AND e.is_self_evaluation = true)'),
    true,
  );
  assert.equal(js.includes(where.replace(/\s+/g, ' ')) || js.includes('is_self_evaluation = true'), true);
  assert.equal(js.includes("'hr'"), false, 'HR is not privileged on details');
});

test('evaluation-details Format: subject of a non-self row never reaches Format', () => {
  const js = jsOf(load(H1_DIR, 'evaluation-details.json'), 'Format Response');
  assert.match(js, /http_status: 404/);
  assert.match(js, /Оценка не найдена или недоступна вам/);
});

test('my-profile: upward row reaches the subject without scores, comments, or evaluator identity', () => {
  const build = jsOf(load(H1_DIR, 'my-profile.json'), 'Build Profile Query');
  const format = jsOf(load(H1_DIR, 'my-profile.json'), 'Format Response');

  assert.match(build, /WHERE e\.subject_id = \$\{actorId\}/);
  assert.match(build, /e\.calculated_score/);
  assert.match(build, /e\.weighted_score/);
  assert.equal(build.includes('general_comment'), false, 'SQL does not select general_comment');
  assert.equal(build.includes('private_comment'), false, 'SQL does not select private_comment');

  const identityNull =
    "evaluator_name: row.evaluation_source === 'subordinate' ? null : row.evaluator_name";
  const titleNull =
    "evaluator_title: row.evaluation_source === 'subordinate' ? null : row.evaluator_title";
  assert.equal(format.includes(identityNull), true, `compared: ${identityNull}`);
  assert.equal(format.includes(titleNull), true, `compared: ${titleNull}`);

  const scoreGate = 'if (isSelfEvaluation) {';
  assert.equal(format.includes(scoreGate), true);
  assert.match(format, /evaluation\.score = row\.calculated_score/);
  assert.match(format, /evaluation\.calculated_score = row\.calculated_score/);
  assert.match(format, /evaluation\.weighted_score = row\.weighted_score/);
  assert.match(format, /const selfEvaluations = evaluations\.filter\(e => e\.is_self_evaluation\)/);
  assert.equal(format.includes('general_comment'), false);
  assert.equal(format.includes('private_comment'), false);
});

test('evaluation-history is given-only (evaluator_id = actor); received upward is not on this route', () => {
  const js = jsOf(load(H1_DIR, 'evaluation-history.json'), 'Build History Query');
  assert.match(js, /WHERE e\.evaluator_id = \$\{actorId\}/);
  assert.match(js, /e\.is_self_evaluation = false/);
  assert.equal(js.includes('e.subject_id = ${actorId}'), false);
});

test('HR evaluation-status: completion flags only, no score or comment columns', () => {
  const js = jsOf(load(H1_DIR, 'hr-evaluation-status.json'), 'Build Status Query');
  assert.equal(guardRoles(load(H1_DIR, 'hr-evaluation-status.json')), '["hr", "admin", "c_level"]');
  assert.match(js, /has_self_review/);
  assert.match(js, /evaluated_manager/);
  assert.match(js, /evaluated_subordinates/);
  assert.equal(js.includes('calculated_score'), false);
  assert.equal(js.includes('score_value'), false);
  assert.equal(js.includes('general_comment'), false);
  assert.equal(js.includes('private_comment'), false);
  assert.equal(js.includes('weighted_score'), false);
});

test('employees campaign payload has flags, not period name/dates and not upward content', () => {
  const wf = load(AUTH_DIR, 'protected-employees.json');
  const build = jsOf(wf, 'Build Identity-Bound Query');
  const format = jsOf(wf, 'Format Response');
  assert.equal(guardRoles(wf), '[]', 'any authenticated session');
  assert.match(build, /SELECT id, status, is_active, evaluation_started_at/);
  assert.equal(build.includes('cp.name'), false);
  assert.equal(build.includes('start_date'), false);
  assert.equal(build.includes('end_date'), false);
  assert.match(format, /campaign_active:/);
  assert.match(format, /period_in_preparation:/);
  assert.match(format, /current_period_id:/);
  assert.equal(format.includes('period_name'), false);
  assert.equal(format.includes('start_date'), false);
  assert.equal(format.includes('end_date'), false);
});

test('GET api/periods does not admit employee or manager', () => {
  const wf = load(H1_DIR, 'manage-periods.json');
  const roles = jsOf(wf, 'Prepare Guard Input GET').match(/required_roles:\s*(\[[^\]]*\])/);
  assert.equal(roles[1], '["admin", "hr", "c_level"]');
});

test('manager-role matrix has no upward score cell; admin matrix upward CTE is not manager-reachable', () => {
  const mm = allJs(load(DEF_DIR, 'manager-subordinates-matrix.json'));
  assert.equal(
    guardRoles(load(DEF_DIR, 'manager-subordinates-matrix.json')),
    '["admin", "c_level", "manager"]',
  );
  assert.match(mm, /evaluation_source = 'manager'/);
  assert.equal(
    /evaluation_source = 'subordinate'/.test(mm),
    false,
    'manager-subordinates-matrix must not read upward rows',
  );
  assert.equal(mm.includes('avg_subordinate_score'), false);
  assert.equal(mm.includes('manager_scores_from_subordinates'), false);

  const matrix = load(DEF_DIR, 'evaluations-matrix.json');
  assert.equal(guardRoles(matrix), '["admin", "c_level"]');
  assert.match(allJs(matrix), /manager_scores_from_subordinates/);

  const byUser = load(DEF_DIR, 'evaluation-details-by-user.json');
  assert.equal(guardRoles(byUser), '["admin", "c_level"]');
});
