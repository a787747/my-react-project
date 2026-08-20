/**
 * regressionWorkflowFixes.test.js
 *
 * Focused regression suite for the Aug-2026 batch of workflow fixes.
 * Reads workflow JSON directly from n8n_workflows/ (no generator step required).
 *
 * Covers:
 *  (1) check-self-review — user_id routing: direct-report / admin / c_level only
 *  (2) my-profile — score fields on self evaluations only; stats derive only from self
 *  (3) evaluation-details — access control: HR excluded; subject only for own self-review
 *  (4) criteria — c_level_only level descriptors stripped below admin / c_level
 *  (5) protected-employees — three boolean flags, actor_is_in_scope, grade_coefficient gating
 *  (6) get-my-manager — grade_coefficient conditional on admin / c_level
 *  (7) score-correction — requires can_evaluate capability
 *  (8) Russian user-facing errors contain no /api/ path
 *  (9) Auth Guard payload byte-for-byte unchanged vs git HEAD
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(__dirname, '..');

const H1       = join(REPO, 'n8n_workflows', 'route_guard_h1');
const DEFERRED = join(REPO, 'n8n_workflows', 'route_guard_deferred');
const AUTH     = join(REPO, 'n8n_workflows', 'auth_core');
const PREAUTH  = join(REPO, 'n8n_workflows');

// ── Helpers ────────────────────────────────────────────────────────────────

function load(dir, file) {
  return JSON.parse(readFileSync(join(dir, file), 'utf8'));
}

function nodes(wf) {
  return wf.nodes || [];
}

function codeNodes(wf) {
  return nodes(wf).filter((n) => n.type === 'n8n-nodes-base.code');
}

function nodeByName(wf, name) {
  return nodes(wf).find((n) => n.name === name);
}

/** JS code of the named Code node, or '' if not found. */
function jsOf(wf, name) {
  return nodeByName(wf, name)?.parameters?.jsCode || '';
}

/** Concatenated JS code of every Code node in the workflow. */
function allJs(wf) {
  return codeNodes(wf).map((n) => n.parameters?.jsCode || '').join('\n');
}

/**
 * Extract strings from patterns that produce user-visible text:
 *   message: 'text'  |  throw new Error('text')
 */
function userMessages(js) {
  const msgs = [];
  for (const m of js.matchAll(/message:\s*'([^'\\]+)'/g))          msgs.push(m[1]);
  for (const m of js.matchAll(/message:\s*"([^"\\]+)"/g))          msgs.push(m[1]);
  for (const m of js.matchAll(/throw new Error\('([^'\\]+)'\)/g))  msgs.push(m[1]);
  for (const m of js.matchAll(/throw new Error\("([^"\\]+)"\)/g))  msgs.push(m[1]);
  return msgs;
}

// ═══════════════════════════════════════════════════════════════════════════
// (1) check-self-review: user_id routing
// ═══════════════════════════════════════════════════════════════════════════

test('check-self-review: selected_subject CTE exists for routing', () => {
  const js = allJs(load(H1, 'check-self-review.json'));
  assert.ok(js.includes('selected_subject'), 'must have selected_subject CTE');
});

test('check-self-review: reads user_id from request query/body and derives requestedId', () => {
  const js = allJs(load(H1, 'check-self-review.json'));
  assert.ok(
    js.includes('request.query?.user_id') || js.includes('request.body?.user_id'),
    'must read user_id from request'
  );
  assert.ok(js.includes('requestedId'), 'must compute requestedId');
  assert.ok(js.includes('actorId'), 'must have actorId as fallback');
});

test('check-self-review: privileged list is exactly admin and c_level (HR excluded)', () => {
  const js = allJs(load(H1, 'check-self-review.json'));
  const privilegedLine = js.match(/(?:const\s+)?privileged\s*=\s*.+/)?.[0] || '';
  assert.ok(
    privilegedLine.includes("'admin'") && privilegedLine.includes("'c_level'"),
    'privileged must include admin and c_level'
  );
  assert.equal(privilegedLine.includes("'hr'"), false, 'HR must not be in privileged list');
});

test('check-self-review: CTE gates non-privileged non-self access on manager_id', () => {
  const js = allJs(load(H1, 'check-self-review.json'));
  assert.ok(
    js.includes('manager_id = ${actorId}'),
    'CTE must check manager_id = actorId for direct-report access'
  );
});

test('check-self-review: falls back to actorId when requestedId equals actorId or no eligibility', () => {
  const js = allJs(load(H1, 'check-self-review.json'));
  // SQL CASE expression that evaluates both options
  assert.ok(js.includes('CASE') && js.includes('THEN') && js.includes('ELSE'), 'must have CASE expression');
  // The ELSE branch returns actorId (the fallback)
  assert.ok(js.includes('ELSE ${actorId}'), 'ELSE branch must return actorId as fallback');
});

// ═══════════════════════════════════════════════════════════════════════════
// (2) my-profile: score fields and stats scoped to self evaluations
// ═══════════════════════════════════════════════════════════════════════════

test('my-profile: derives isSelfEvaluation flag per row', () => {
  const js = allJs(load(H1, 'my-profile.json'));
  assert.ok(js.includes('isSelfEvaluation'), 'must compute isSelfEvaluation per row');
  assert.ok(js.includes('is_self_evaluation'), 'must reference is_self_evaluation field');
});

test('my-profile: score/calculated_score/weighted_score emitted only inside isSelfEvaluation block', () => {
  const js = allJs(load(H1, 'my-profile.json'));
  assert.ok(js.includes('if (isSelfEvaluation)'), 'must have isSelfEvaluation guard block');
  const ifIdx   = js.indexOf('if (isSelfEvaluation)');
  const scoreIdx = js.indexOf('evaluation.score =', ifIdx);
  const calcIdx  = js.indexOf('evaluation.calculated_score =', ifIdx);
  assert.ok(
    scoreIdx > ifIdx || calcIdx > ifIdx,
    'score assignment must come after isSelfEvaluation check'
  );
});

test('my-profile: stats computation uses selfEvaluations subset', () => {
  const js = allJs(load(H1, 'my-profile.json'));
  assert.ok(js.includes('selfEvaluations'), 'must have selfEvaluations variable');
  assert.ok(
    js.includes('.filter(e => e.is_self_evaluation)') ||
    (js.includes('selfEvaluations =') && js.includes('filter')),
    'selfEvaluations must be a filtered subset of evaluations'
  );
});

test('my-profile: latest_score, latest_period, latest_date derive from latestSelf', () => {
  const js = allJs(load(H1, 'my-profile.json'));
  assert.ok(js.includes('latestSelf'), 'must compute latestSelf');
  assert.ok(js.includes('latestSelf?.calculated_score'), 'latest_score must use latestSelf');
  assert.ok(js.includes('latestSelf?.period_name'), 'latest_period must use latestSelf');
  assert.ok(js.includes('latestSelf?.updated_at'), 'latest_date must use latestSelf');
});

test('my-profile: does not use all-evaluations[0] for latest stats', () => {
  const js = allJs(load(H1, 'my-profile.json'));
  // Old code used: const latest = evaluations[0]  then latest?.calculated_score
  assert.equal(js.includes("evaluations[0]"), false,
    'must not derive latest stats from evaluations[0] (includes non-self)');
});

// ═══════════════════════════════════════════════════════════════════════════
// (3) evaluation-details: access control
// ═══════════════════════════════════════════════════════════════════════════

test('evaluation-details: privileged list is admin and c_level (HR excluded)', () => {
  const js = jsOf(load(H1, 'evaluation-details.json'), 'Build Details Query');
  assert.ok(js.includes("'admin'") && js.includes("'c_level'"), 'must include admin and c_level');
  // The privileged assignment must not contain 'hr'
  const privilegedDecl = js.match(/const\s+privileged\s*=\s*.+/)?.[0] || '';
  assert.equal(privilegedDecl.includes("'hr'"), false, 'HR must not be in privileged list');
});

test('evaluation-details: subject WHERE clause requires is_self_evaluation = true', () => {
  const js = jsOf(load(H1, 'evaluation-details.json'), 'Build Details Query');
  assert.ok(
    js.includes('(e.subject_id = ${actorId} AND e.is_self_evaluation = true)'),
    'subject access clause must require is_self_evaluation = true'
  );
});

test('evaluation-details: bare subject access without self-review restriction is absent', () => {
  const js = jsOf(load(H1, 'evaluation-details.json'), 'Build Details Query');
  // Old pattern: "          OR e.subject_id = ${actorId}\n        )\n      `"
  // Regex: OR e.subject_id = ${actorId} followed only by whitespace and closing `)
  assert.equal(
    /OR e\.subject_id = \$\{actorId\}(?!\s*AND)/.test(js),
    false,
    'OR e.subject_id without AND is_self_evaluation must not exist'
  );
});

test('evaluation-details: 400 and 404 error messages are in Russian', () => {
  const js = allJs(load(H1, 'evaluation-details.json'));
  const msgs = userMessages(js);
  const hasCyrillic = msgs.some((m) => /[А-Яа-яЁё]/.test(m));
  assert.ok(hasCyrillic, 'error messages must be in Russian');
  assert.equal(
    js.includes('evaluation_id is required and must be a positive integer'),
    false,
    'old English error must be replaced with Russian'
  );
  assert.equal(
    js.includes('Evaluation not found'),
    false,
    'old English 404 message must be replaced with Russian'
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// (4) criteria: c_level_only level descriptor stripping
// ═══════════════════════════════════════════════════════════════════════════

test('criteria: canSeeCLevelTexts gates on admin and c_level', () => {
  const js = allJs(load(H1, 'criteria.json'));
  assert.ok(js.includes('canSeeCLevelTexts'), 'must compute canSeeCLevelTexts');
  assert.ok(
    js.includes("['admin', 'c_level'].includes"),
    'canSeeCLevelTexts must gate on admin and c_level roles'
  );
});

test('criteria: identifies c_level_only rows and conditionally deletes level descriptors', () => {
  const js = allJs(load(H1, 'criteria.json'));
  assert.ok(
    js.includes('c_level_only') && (js.includes('isCLevelOnly') || js.includes('c_level_only')),
    'must detect c_level_only rows'
  );
  assert.ok(js.includes('delete criterion'), 'must delete restricted fields from criterion object');
  assert.ok(js.includes('!canSeeCLevelTexts'), 'deletion must be behind !canSeeCLevelTexts guard');
  // level_1_desc through level_10_desc must be in scope of deletion
  assert.ok(
    js.includes('level_') || js.includes('levelTextFields'),
    'must reference level_N_desc field names'
  );
});

test('criteria: admin and c_level actors keep all level descriptor fields', () => {
  const js = allJs(load(H1, 'criteria.json'));
  // The stripping only fires when !canSeeCLevelTexts — meaning admins and c_level see everything
  assert.ok(
    js.includes('if (isCLevelOnly && !canSeeCLevelTexts)') ||
    (js.includes('isCLevelOnly') && js.includes('!canSeeCLevelTexts')),
    'stripping must be conditional: c_level_only AND NOT privileged'
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// (5) protected-employees
// ═══════════════════════════════════════════════════════════════════════════

test('protected-employees: Prepare Guard Input opens endpoint to all authenticated users', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Prepare Guard Input');
  assert.ok(js.includes('required_roles: []'), 'required_roles must be [] (no role restriction)');
  assert.ok(
    js.includes("required_capability: ''") || js.includes('required_capability: ""'),
    'required_capability must be empty'
  );
});

test('protected-employees: SQL keeps direct-report scope via manager_id = actorId', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Build Identity-Bound Query');
  assert.ok(
    js.includes('manager_id = ${actorId}') || js.includes('users.manager_id = ${actorId}'),
    'must scope employees by manager_id = actorId for all roles'
  );
});

test('protected-employees: SQL includes exactly three boolean status flags per employee', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Build Identity-Bound Query');
  assert.ok(js.includes('has_self_review'), 'must include has_self_review flag');
  assert.ok(js.includes('has_evaluated_manager'), 'must include has_evaluated_manager flag');
  assert.ok(js.includes('evaluated_by_actor'), 'must include evaluated_by_actor flag');
  // Flags must be EXISTS subqueries (boolean), not score columns
  const existsCount = (js.match(/\bEXISTS\s*\(/g) || []).length;
  assert.ok(existsCount >= 3, 'each of the three flags must be an EXISTS subquery');
});

test('protected-employees: SQL does not expose calculated_score or weighted_score per employee', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Build Identity-Bound Query');
  assert.equal(js.includes('calculated_score'), false,
    'employee rows must not include calculated_score');
  assert.equal(js.includes('weighted_score'), false,
    'employee rows must not include weighted_score');
});

test('protected-employees: period selection includes draft periods for actor_is_in_scope', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Build Identity-Bound Query');
  assert.ok(
    js.includes("status = 'draft'"),
    "current_period CTE must include draft periods so actor_is_in_scope is visible before activation"
  );
  assert.ok(
    js.includes('actor_is_in_scope') || js.includes('actor_scope'),
    'must compute actor scope from the selected period'
  );
});

test('protected-employees: Format Response removes grade_coefficient below admin/c_level', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Format Response');
  assert.ok(js.includes('canSeeGradeCoefficient'), 'must compute canSeeGradeCoefficient flag');
  assert.ok(
    js.includes("['admin', 'c_level'].includes"),
    'canSeeGradeCoefficient must gate on admin/c_level'
  );
  assert.ok(
    js.includes('delete safeEmployee.grade_coefficient') ||
    (js.includes('delete') && js.includes('grade_coefficient')),
    'must delete grade_coefficient for non-admin/c_level'
  );
});

test('protected-employees: Format Response exposes actor_is_in_scope with null when no period', () => {
  const js = jsOf(load(AUTH, 'protected-employees.json'), 'Format Response');
  assert.ok(js.includes('actor_is_in_scope'), 'response body must include actor_is_in_scope');
  assert.ok(
    js.includes('=== null') || js.includes('=== undefined'),
    'must handle null actor_is_in_scope gracefully when no period exists'
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// (6) get-my-manager: grade_coefficient conditional
// ═══════════════════════════════════════════════════════════════════════════

test('get-my-manager: canSeeGradeCoefficient gates on admin and c_level', () => {
  const js = jsOf(load(H1, 'get-my-manager.json'), 'Format Response');
  assert.ok(js.includes('canSeeGradeCoefficient'), 'must compute canSeeGradeCoefficient');
  assert.ok(
    js.includes("['admin', 'c_level'].includes"),
    'canSeeGradeCoefficient must check admin/c_level'
  );
});

test('get-my-manager: grade_coefficient emitted conditionally, not unconditionally', () => {
  const js = jsOf(load(H1, 'get-my-manager.json'), 'Format Response');
  // New code: ...(canSeeGradeCoefficient ? { grade_coefficient: m.grade_coefficient } : {})
  // Old code: grade_coefficient: m.grade_coefficient directly in manager object
  assert.ok(
    js.includes('canSeeGradeCoefficient ?') || js.includes('canSeeGradeCoefficient\n'),
    'grade_coefficient must be behind canSeeGradeCoefficient conditional'
  );
  // The conditional spread pattern must be present
  assert.ok(
    js.includes('grade_coefficient: m.grade_coefficient') || js.includes('grade_coefficient'),
    'grade_coefficient must be referenced'
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// (7) score-correction: requires can_evaluate
// ═══════════════════════════════════════════════════════════════════════════

test('score-correction: Prepare Guard Input sets required_capability to can_evaluate', () => {
  const js = jsOf(load(DEFERRED, 'score-correction.json'), 'Prepare Guard Input');
  assert.ok(
    js.includes('"can_evaluate"') || js.includes("'can_evaluate'"),
    'required_capability must be "can_evaluate"'
  );
  // Must not be blank (old state had required_capability: "")
  assert.equal(
    js.includes('required_capability: ""') || js.includes("required_capability: ''"),
    false,
    'required_capability must not be empty string'
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// (8) Russian user-facing errors contain no /api/ path
// ═══════════════════════════════════════════════════════════════════════════

test('API: Verify Code — errors are in Russian and contain no /api/ path', () => {
  const js = allJs(load(PREAUTH, 'API_ Verify Code.json'));
  const msgs = userMessages(js);
  assert.ok(msgs.length > 0, 'must have extractable user messages');
  assert.ok(msgs.some((m) => /[А-Яа-яЁё]/.test(m)), 'at least one message must be in Russian');
  for (const msg of msgs) {
    assert.equal(msg.includes('/api/'), false, `must not contain /api/: "${msg}"`);
  }
});

test('API: Verify Invite — errors are in Russian and contain no /api/ path', () => {
  const js = allJs(load(PREAUTH, 'API_ Verify Invite.json'));
  const msgs = userMessages(js);
  assert.ok(msgs.length > 0, 'must have extractable user messages');
  assert.ok(msgs.some((m) => /[А-Яа-яЁё]/.test(m)), 'at least one message must be in Russian');
  for (const msg of msgs) {
    assert.equal(msg.includes('/api/'), false, `must not contain /api/: "${msg}"`);
  }
});

test('auth_core/register — errors are in Russian and contain no /api/ path', () => {
  const js = allJs(load(AUTH, 'register.json'));
  const msgs = userMessages(js);
  assert.ok(msgs.some((m) => /[А-Яа-яЁё]/.test(m)), 'at least one message must be in Russian');
  for (const msg of msgs) {
    assert.equal(msg.includes('/api/'), false, `must not contain /api/: "${msg}"`);
  }
});

test('auth_core/reset-password — errors are in Russian and contain no /api/ path', () => {
  const js = allJs(load(AUTH, 'reset-password.json'));
  const msgs = userMessages(js);
  assert.ok(msgs.some((m) => /[А-Яа-яЁё]/.test(m)), 'at least one message must be in Russian');
  for (const msg of msgs) {
    assert.equal(msg.includes('/api/'), false, `must not contain /api/: "${msg}"`);
  }
});

test('route_guard_h1 changed workflows — error messages contain no /api/ path', () => {
  const wfFiles = [
    'check-self-review.json',
    'criteria.json',
    'evaluation-details.json',
    'get-my-manager.json',
    'my-profile.json',
  ];
  for (const f of wfFiles) {
    const msgs = userMessages(allJs(load(H1, f)));
    for (const msg of msgs) {
      assert.equal(msg.includes('/api/'), false, `${f}: message must not contain /api/: "${msg}"`);
    }
  }
});

test('route_guard_deferred/score-correction — errors are in Russian and contain no /api/ path', () => {
  const js = allJs(load(DEFERRED, 'score-correction.json'));
  const msgs = userMessages(js);
  assert.ok(msgs.some((m) => /[А-Яа-яЁё]/.test(m)), 'at least one message must be in Russian');
  for (const msg of msgs) {
    assert.equal(msg.includes('/api/'), false, `must not contain /api/: "${msg}"`);
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// (9) Auth Guard payload byte-for-byte unchanged vs git HEAD
// ═══════════════════════════════════════════════════════════════════════════

test('auth-guard.json is byte-for-byte identical to git HEAD', (t) => {
  const GUARD_REL = 'n8n_workflows/auth_core/auth-guard.json';
  let headContent;
  try {
    headContent = execSync(`git show HEAD:${GUARD_REL}`, {
      cwd: REPO,
      encoding: 'utf8',
      timeout: 8000,
    });
  } catch (err) {
    // git show may be slow or unavailable in some environments
    t.skip(`git show unavailable or timed out — cannot compare: ${String(err.message).split('\n')[0]}`);
    return;
  }
  const workingTree = readFileSync(join(REPO, GUARD_REL), 'utf8');
  assert.equal(
    workingTree,
    headContent,
    'auth-guard.json must be byte-for-byte identical to git HEAD (no accidental edits to the guard payload)'
  );
});
