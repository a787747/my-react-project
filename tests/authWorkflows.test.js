import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const AUTH_DIR = join(ROOT, 'n8n_workflows', 'auth_core');

const EXPECTED_FILES = [
  'auth-guard.json',
  'login.json',
  'protected-employees.json',
  'register.json',
  'request-password-reset.json',
  'reset-password.json',
];

function load(filename) {
  return JSON.parse(readFileSync(join(AUTH_DIR, filename), 'utf8'));
}

function nodesOfType(wf, type) {
  return wf.nodes.filter((n) => n.type === type);
}

function codeNodeByName(wf, name) {
  return wf.nodes.find(
    (n) => n.name === name && n.type === 'n8n-nodes-base.code',
  );
}

// ── 1. Corpus ────────────────────────────────────────────────────────────────

test('all six auth_core workflow files are present', () => {
  const present = readdirSync(AUTH_DIR)
    .filter((f) => f.endsWith('.json'))
    .sort();
  assert.deepEqual(present, EXPECTED_FILES);
});

// ── 2. Execution-data persistence disabled on every workflow ─────────────────

test('every auth_core workflow disables data persistence', () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const { settings } = wf;
    assert.equal(
      settings.saveDataErrorExecution,
      'none',
      `${filename}: saveDataErrorExecution must be "none"`,
    );
    assert.equal(
      settings.saveDataSuccessExecution,
      'none',
      `${filename}: saveDataSuccessExecution must be "none"`,
    );
    assert.equal(
      settings.saveManualExecutions,
      false,
      `${filename}: saveManualExecutions must be false`,
    );
  }
});

// ── 3. JWT shape: 4-hour expiry, empty payload (no role claim) ───────────────

test('login workflow signs JWT with 4-hour expiry', () => {
  const wf = load('login.json');
  const node = codeNodeByName(wf, 'Verify Password');
  assert.ok(node, 'Verify Password node must exist in login workflow');
  assert.ok(
    node.parameters.jsCode.includes("expiresIn: '4h'"),
    "JWT expiresIn must be '4h'",
  );
});

test('login JWT sign call uses an empty payload object — no role claim', () => {
  const wf = load('login.json');
  const node = codeNodeByName(wf, 'Verify Password');
  assert.ok(node, 'Verify Password node must exist');

  // The sign call must be jwt.sign({}, ...) — empty first arg
  assert.ok(
    /jwt\.sign\(\s*\{\s*\}/.test(node.parameters.jsCode),
    'jwt.sign() first argument must be an empty object {}',
  );

  // The jsCode must not embed a role property in the token
  assert.ok(
    !/jwt\.sign\([^)]*role/.test(node.parameters.jsCode),
    'JWT payload must not contain a role claim',
  );
});

// ── 4. Guard is a sub-workflow (executeWorkflowTrigger), not a public endpoint

test('auth guard workflow uses executeWorkflowTrigger, not a public webhook', () => {
  const wf = load('auth-guard.json');
  const triggers = nodesOfType(wf, 'n8n-nodes-base.executeWorkflowTrigger');
  assert.equal(triggers.length, 1, 'guard must have exactly one executeWorkflowTrigger');

  const webhooks = nodesOfType(wf, 'n8n-nodes-base.webhook');
  assert.equal(webhooks.length, 0, 'guard must have no public webhook trigger');
});

// ── 5. Protected route invokes the guard exactly once ────────────────────────

test('protected-employees workflow calls the auth guard exactly once', () => {
  const wf = load('protected-employees.json');
  const guardCalls = nodesOfType(wf, 'n8n-nodes-base.executeWorkflow');
  assert.equal(
    guardCalls.length,
    1,
    'protected-employees must have exactly one executeWorkflow (the auth guard call)',
  );
  const guardNode = guardCalls[0];
  const workflowId = guardNode.parameters.workflowId;
  assert.ok(
    typeof workflowId === 'string' && workflowId.length > 0,
    'guard workflowId must be a non-empty string',
  );
});

test('protected-employees lists only in-scope subordinates of the active period', () => {
  const wf = load('protected-employees.json');
  const build = codeNodeByName(wf, 'Build Identity-Bound Query');
  assert.ok(build, 'Build Identity-Bound Query node must exist');
  const sql = build.parameters.jsCode;
  assert.ok(
    sql.includes('evaluation_period_participants') && sql.includes('is_in_scope'),
    'employees SQL must join period participants and require is_in_scope',
  );
  assert.ok(
    sql.includes("status = 'active'") && sql.includes('is_active = true'),
    'employees SQL must require the active period',
  );
  assert.ok(
    sql.includes('campaign_active'),
    'employees response must expose campaign_active',
  );
});

// ── 6. Every Postgres node carries a non-empty credential ID ─────────────────

test('every postgres node in auth_core workflows has a credential ID', () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    for (const n of nodesOfType(wf, 'n8n-nodes-base.postgres')) {
      const credId = n.credentials?.postgres?.id;
      assert.ok(
        typeof credId === 'string' && credId.length > 0,
        `${filename} › node "${n.name}" must have a non-empty postgres credential ID`,
      );
    }
  }
});

test('register keeps the invite token reusable and accepts base64url tokens', () => {
  const wf = load('register.json');
  const loadSql = wf.nodes.find((n) => n.name === 'Load Registration Context')?.parameters?.query || '';
  const hashJs = wf.nodes.find((n) => n.name === 'Hash Password')?.parameters?.jsCode || '';
  const validateJs = wf.nodes.find((n) => n.name === 'Validate Registration')?.parameters?.jsCode || '';
  assert.equal(loadSql.includes('COALESCE(invites.is_used, false) = false'), false);
  assert.equal(hashJs.includes('SET is_used = true'), false);
  assert.ok(hashJs.includes('SELECT id FROM performance_db.invite_tokens'));
  assert.ok(validateJs.includes('A-Za-z0-9_-'));
  assert.equal(validateJs.includes('a-f0-9-]{16,128}'), false);
});
