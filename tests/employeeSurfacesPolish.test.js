/**
 * EMPLOYEE_SURFACES_POLISH — employee profile, task links and sealed payload.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = (path) => readFileSync(join(root, path), 'utf8');
const out = mkdtempSync(join(tmpdir(), 'employee-surfaces-'));

execFileSync(
  'python3',
  [
    join(root, 'scripts/build_route_guard_workflows.py'),
    '--output-directory',
    out,
  ],
  { cwd: root },
);

const workflow = JSON.parse(readFileSync(join(out, 'my-profile.json'), 'utf8'));
const nodeCode = (name) => workflow.nodes.find((node) => node.name === name)?.parameters?.jsCode || '';
const build = nodeCode('Build Profile Query');
const format = nodeCode('Format Response');
const profile = read('src/pages/Profile.jsx');
const welcome = read('src/pages/Welcome.jsx');
const taskSummary = read('src/components/TaskSummary.jsx');
const guide = read('src/components/RatingGuide.jsx');

test('profile read payload carries employee labels and current-period scope only', () => {
  for (const field of [
    'full_name',
    'job_title',
    'department_name',
    'manager_name',
    'grade_label',
    'join_date',
    'is_in_scope',
    'exclusion_reason',
    'scope_override',
  ]) {
    assert.match(`${build}\n${format}`, new RegExp(field));
  }
  assert.match(build, /to_char\(actor_u\.join_date, 'YYYY-MM-DD'\)/);
  assert.match(format, /\n\s{6}employee,/);
  assert.match(format, /current_period:/);
});

test('profile payload exposes neither compensation nor employee-facing money inputs', () => {
  const payloadCode = `${build}\n${format}`;
  assert.doesNotMatch(payloadCode, /salary|compensation|salary_current|salary_proposed/i);
  assert.doesNotMatch(payloadCode, /grade_coefficient|bonus_index|criteria_weight|score_coefficient/i);
});

test('D-0820-17: only a self row can receive numeric score fields', () => {
  const selfGate = format.indexOf('if (isSelfEvaluation)');
  assert.ok(selfGate >= 0);
  for (const assignment of [
    'evaluation.score =',
    'evaluation.calculated_score =',
    'evaluation.weighted_score =',
  ]) {
    assert.ok(format.indexOf(assignment, selfGate) > selfGate);
  }
  assert.doesNotMatch(format.slice(0, selfGate), /evaluation\.(score|calculated_score|weighted_score)\s*=/);
});

test('profile renders identity, scope wording, task status and self-assessment', () => {
  assert.match(profile, /profileData\.employee/);
  assert.match(profile, /department_name/);
  assert.match(profile, /manager_name/);
  assert.match(profile, /grade_label/);
  assert.match(profile, /join_date/);
  assert.match(profile, /welcomeExclusionText/);
  assert.match(profile, /<TaskSummary/);
  assert.match(profile, /<SelfEvaluationCard/);
});

test('every task icon is a link to the page where that task is done', () => {
  assert.match(taskSummary, /from 'react-router-dom'/);
  assert.match(taskSummary, /<Link/);
  assert.match(taskSummary, /\/self-review/);
  assert.match(taskSummary, /\/dashboard/);
  assert.match(taskSummary, /\/manager-evaluation/);
  assert.match(welcome, /<TaskSummary/);
});

test('employee subset keeps approved words but displays as a local 1–3 list', () => {
  assert.match(guide, /variant === 'employee' \? index \+ 1 : rule\.n/);
  assert.doesNotMatch(guide, /Правила 1, 6 и 7/);
});

// ── Gap tests ────────────────────────────────────────────────────────────────

test('no-evaluation response always carries employee and current_period (no early return)', () => {
  // Old code returned early without employee/current_period when data was empty.
  // If that early return is restored, Profile.jsx crashes on profileData.employee.
  assert.doesNotMatch(format, /if \(!data\.length\)/);
  assert.match(format, /has_evaluations: evaluations\.length > 0/);
  assert.match(format, /\n\s+employee,/);
  assert.match(format, /current_period: currentPeriod,/);
});

test('currentPeriod resolves to literal null when no active period row is present', () => {
  // Without the null guard, a period with current_period_id=null would surface an
  // object full of null fields rather than a clean null — crashing === false checks.
  assert.match(
    format,
    /current_period_id === null \|\| first\.current_period_id === undefined\s*\n\s*\? null/,
  );
});

test('is_in_scope inside currentPeriod uses asBoolean with explicit null guard', () => {
  // PostgreSQL returns 't'/'f' strings; without asBoolean, "'f' === false" is false.
  // Without the null guard, a null participant row (scope unknown) coerces to false
  // and would wrongly trigger the exclusion banner on Profile.
  assert.match(format, /const asBoolean = value => value === true \|\| value === 't'/);
  assert.match(format, /is_in_scope: first\.is_in_scope === null \|\| first\.is_in_scope === undefined/);
  assert.match(format, /: asBoolean\(first\.is_in_scope\)/);
});

test('profile scope-reason banner uses strict is_in_scope === false, not loose falsy', () => {
  // null (no participant row) must not trigger the banner.
  // Changing to !is_in_scope would falsely show the exclusion notice for every
  // employee with no entry in evaluation_period_participants.
  assert.match(profile, /is_in_scope === false/);
  const falseGuardIdx = profile.indexOf('is_in_scope === false');
  const testidIdx = profile.indexOf('profile-scope-reason');
  assert.ok(testidIdx > falseGuardIdx, 'profile-scope-reason testid must appear after the === false guard');
});

test('employee guide rule set is locked to [1, 6, 7] with owner-approved H1 wording', () => {
  // EMPLOYEE_GUIDE_RULE_NUMBERS silently changed would pass test-6 but alter
  // what employees see during H1. Canonical lead texts pin the approved content.
  const content = read('src/content/ratingGuideH1.js');
  assert.match(content, /EMPLOYEE_GUIDE_RULE_NUMBERS\s*=\s*\[1,\s*6,\s*7\]/);
  // rule 1 — period-scoped facts only
  assert.match(content, /Оцениваете факты по критериям за этот период/);
  // rule 6 — manager feedback (anonymity context)
  assert.match(content, /Оценка руководителя — возможность дать ему объективную обратную связь/);
  // rule 7 — self-evaluation intent
  assert.match(content, /оцените, как по фактам периода оценил бы вас руководитель/);
});
