/**
 * PRELAUNCH_BATCH_NIGHT — D-0825-11 … D-0825-14.
 *
 * Pins, in order of the brief:
 *   item 2  the participants rule sends a NULL hire date OUT of scope
 *   item 3  the exclusion reason reaches the person and their manager
 *   item 4  a half-year pays nothing, verbatim, on both surfaces
 *   item 5  /admin/users opens A→Z and shows the period state
 *   item 6  the matrix header is the union of every row; colours read the raw score
 *   item 7  a budget is distributed and the amounts sum to it exactly
 *   item 8  the pool rule is a predicate, never an id list
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

import {
  PERIOD_NOTICE_NO_BONUS,
  buildPeriodNotice,
} from '../src/utils/periodNotice.js';
import {
  RATING_GUIDE_STANDING_NOTE,
} from '../src/content/ratingGuideH1.js';
import {
  EXCLUSION_REASONS,
  WELCOME_AFTER_PERIOD_END,
  WELCOME_LATE_HIRE,
  teamExclusionText,
  welcomeExclusionText,
} from '../src/utils/scopeExclusion.js';
import {
  EVALUATION_STATES,
  evaluationStateOf,
} from '../src/utils/evaluationState.js';
import {
  FILTER_KEYS,
  INITIAL_FILTERS,
  buildFacets,
  filterUsers,
} from '../src/utils/userFilters.js';
import { DEFAULT_SORT_DIRECTION, DEFAULT_SORT_FIELD, sortUsers } from '../src/utils/userSort.js';
import {
  buildSharedCriteriaList,
  distributeBudget,
  parseHumanNumber,
  takesBonusShare,
} from '../src/utils/matrixUtils.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');
const read = (relative) => readFileSync(join(root, relative), 'utf8');

// ── generated workflow definitions, regenerated into a temp dir ─────────────

const OUT = mkdtempSync(join(tmpdir(), 'night-wf-'));
execSync(`python3 "${join(root, 'scripts', 'build_route_guard_workflows.py')}" --output-directory "${OUT}"`,
  { cwd: root, stdio: 'pipe' });
const OUT_DEFERRED = mkdtempSync(join(tmpdir(), 'night-wf-def-'));
execSync(`python3 "${join(root, 'scripts', 'build_route_guard_deferred.py')}" --output-directory "${OUT_DEFERRED}"`,
  { cwd: root, stdio: 'pipe' });
const OUT_AUTH = mkdtempSync(join(tmpdir(), 'night-wf-auth-'));
execSync(`python3 "${join(root, 'scripts', 'build_auth_workflows.py')}" --output-directory "${OUT_AUTH}"`,
  { cwd: root, stdio: 'pipe' });

const loadFrom = (dir, file) => JSON.parse(readFileSync(join(dir, file), 'utf8'));
const nodeCode = (workflow, name) => {
  const found = workflow.nodes.find((n) => n.name === name);
  assert.ok(found, `node «${name}» exists`);
  return found.parameters.jsCode ?? found.parameters.query ?? '';
};

// ── item 2 ──────────────────────────────────────────────────────────────────

test('item 2: a NULL hire date puts a person OUT of scope, with a reason', () => {
  const code = nodeCode(loadFrom(OUT, 'manage-periods.json'), 'Build Create SQL');
  assert.match(code, /WHEN u\.join_date IS NULL THEN false/);
  assert.match(code, /WHEN u\.join_date IS NULL THEN 'join_date_missing'/);
  // The NULL branch must come BEFORE the comparison, or the comparison's own
  // NULL result falls through to ELSE true — the shape of BUG-066.
  const nullBranch = code.indexOf('WHEN u.join_date IS NULL THEN false');
  const dateBranch = code.indexOf("WHEN u.join_date > '${endDate}'::date THEN false");
  assert.ok(nullBranch > 0 && dateBranch > nullBranch,
    'the NULL branch is evaluated before the date comparison');
  // Termination still outranks both.
  assert.ok(code.indexOf('WHEN u.terminated_at IS NOT NULL THEN false') < nullBranch);
});

test('item 2: the new reason is reversible by hand, terminated is not', () => {
  const code = nodeCode(loadFrom(OUT, 'manage-period-scope.json'), 'Build Include SQL');
  assert.match(code, /REVERSIBLE_REASONS = \['excluded_by_admin', 'join_date_missing'\]/);
  assert.match(code, /exclusion_reason IN \('excluded_by_admin', 'join_date_missing'\)/);
  assert.doesNotMatch(code, /REVERSIBLE_REASONS.*terminated/);
});

// ── item 3 ──────────────────────────────────────────────────────────────────

test('item 3: /api/employees carries the actor reason and an out-of-scope team array', () => {
  const employees = loadFrom(OUT_AUTH, 'protected-employees.json');
  const sql = nodeCode(employees, 'Build Identity-Bound Query');
  assert.match(sql, /out_of_scope_team AS \(/);
  assert.match(sql, /AND epp\.is_in_scope = false/);
  // Terminated people stay hidden: this is the clause that keeps the two states
  // from merging, and it is the whole difference from D-0825-7.
  assert.match(sql, /AND users\.terminated_at IS NULL/);
  assert.match(sql, /AS actor_exclusion_reason/);

  const format = nodeCode(employees, 'Format Response');
  assert.match(format, /actor_exclusion_reason: row\.actor_exclusion_reason \|\| null/);
  assert.match(format, /out_of_scope_data: outOfScope/);
  // The task list must not grow: an out-of-scope person reaching `data` would
  // become a task, a counter and a clickable evaluation form.
  assert.match(format, /data: employees,/);
});

test('item 3: the task-list CTE still admits only in-scope people', () => {
  const sql = nodeCode(loadFrom(OUT_AUTH, 'protected-employees.json'), 'Build Identity-Bound Query');
  const scoped = sql.slice(sql.indexOf('scoped AS ('), sql.indexOf('SELECT\n        EXISTS(SELECT 1 FROM active_period)'));
  assert.match(scoped, /AND epp\.is_in_scope = true/);
});

test('item 3: the person is told the true reason, not the one that fits a late hire', () => {
  assert.equal(welcomeExclusionText(EXCLUSION_REASONS.EXCLUDED_BY_ADMIN), WELCOME_LATE_HIRE);
  assert.equal(welcomeExclusionText(EXCLUSION_REASONS.HIRED_AFTER_PERIOD_END), WELCOME_AFTER_PERIOD_END);
  // An absent reason degrades to the previous copy rather than to a blank.
  assert.equal(welcomeExclusionText(null), WELCOME_AFTER_PERIOD_END);
  assert.equal(welcomeExclusionText(undefined), WELCOME_AFTER_PERIOD_END);
});

test('item 3: the owner’s two texts are verbatim', () => {
  assert.equal(
    WELCOME_LATE_HIRE,
    'В оценке за первое полугодие (1 января — 30 июня 2026) вы не участвуете: вы приступили '
    + 'к работе после 31 марта, и отработанного периода недостаточно для оценки. Это не оценка '
    + 'вашей работы. В оценке за второе полугодие вы участвуете в полном объёме, и её результат '
    + 'войдёт в ваш годовой результат.',
  );
  assert.equal(
    teamExclusionText(EXCLUSION_REASONS.EXCLUDED_BY_ADMIN, '2026-04-09'),
    'Не оценивается в этом периоде: принят(а) 9 апреля 2026, меньше трёх месяцев '
    + 'в периоде. Оценка — со второго полугодия.',
  );
});

test('item 3: with no hire date the manager line does not print a hole', () => {
  const text = teamExclusionText(EXCLUSION_REASONS.JOIN_DATE_MISSING, null);
  assert.match(text, /не заполнена дата приёма/);
  assert.doesNotMatch(text, /принят\(а\)\s*,/);
  assert.doesNotMatch(teamExclusionText(EXCLUSION_REASONS.EXCLUDED_BY_ADMIN, null), /принят\(а\)/);
});

test('item 3: the team section is separate markup and never a task', () => {
  const section = read('src/components/common/OutOfScopeTeamSection.jsx');
  assert.match(section, /teamExclusionText/);
  assert.doesNotMatch(section, /onEvaluate|onEdit|Оценить/);
  for (const page of ['src/pages/TeamView.jsx', 'src/pages/Dashboard.jsx']) {
    assert.match(read(page), /<OutOfScopeTeamSection employees=\{outOfScopeEmployees\}/, page);
  }
});

// ── item 4 ──────────────────────────────────────────────────────────────────

const NO_BONUS = 'Оценка за первое полугодие — промежуточная. По её итогам премия не '
  + 'выплачивается: результат первого полугодия войдёт в годовую оценку вместе с результатом '
  + 'второго полугодия и повлияет на годовой результат.';

test('item 4: the half-year sentence is verbatim in both places, and identical', () => {
  assert.equal(PERIOD_NOTICE_NO_BONUS, NO_BONUS);
  assert.equal(RATING_GUIDE_STANDING_NOTE, NO_BONUS);
});

test('item 4: it rides on the period notice in every state, so nobody misses it', () => {
  for (const state of [
    { campaignActive: false, periodInPreparation: false },
    { campaignActive: false, periodInPreparation: true },
    { campaignActive: true, periodInPreparation: false },
  ]) {
    assert.equal(buildPeriodNotice(state).noBonus, NO_BONUS);
  }
  assert.match(read('src/components/common/PeriodNotice.jsx'), /notice\.noBonus/);
});

test('item 4: the guide note renders in every variant, above the numbered rules', () => {
  const guide = read('src/components/RatingGuide.jsx');
  assert.match(guide, /RATING_GUIDE_STANDING_NOTE/);
  assert.ok(guide.indexOf('RATING_GUIDE_STANDING_NOTE') < guide.indexOf('rules.map'),
    'the standing note precedes the rule list');
  // Not a numbered rule: the title still counts eight, and the employee subset
  // is untouched.
  assert.doesNotMatch(read('src/content/ratingGuideH1.js'), /n: 9/);
});

// ── item 5 ──────────────────────────────────────────────────────────────────

test('item 5: the roster opens ascending by name', () => {
  assert.equal(DEFAULT_SORT_FIELD, 'name');
  assert.equal(DEFAULT_SORT_DIRECTION, 'asc');
  const hook = read('src/hooks/useUserFilters.js');
  assert.match(hook, /useState\(DEFAULT_SORT_FIELD\)/);
  assert.match(hook, /useState\(DEFAULT_SORT_DIRECTION\)/);
  assert.doesNotMatch(hook, /setSortField\(null\)/);

  const roster = [
    { id: 3, full_name: 'Яна' }, { id: 1, full_name: 'Anna' }, { id: 2, full_name: 'Boris' },
  ];
  assert.deepEqual(
    sortUsers(roster, DEFAULT_SORT_FIELD, DEFAULT_SORT_DIRECTION).map((u) => u.id),
    [1, 2, 3],
  );
});

const stateRoster = [
  { id: 1, full_name: 'In scope', period_id: 2, has_period_row: true, period_is_in_scope: true, join_date: '2020-01-01' },
  { id: 2, full_name: 'Late hire', period_id: 2, has_period_row: true, period_is_in_scope: false, period_exclusion_reason: 'excluded_by_admin', join_date: '2026-04-09' },
  { id: 3, full_name: 'After end', period_id: 2, has_period_row: true, period_is_in_scope: false, period_exclusion_reason: 'hired_after_period_end', join_date: '2026-07-06' },
  { id: 4, full_name: 'Leaver', period_id: 2, has_period_row: true, period_is_in_scope: false, period_exclusion_reason: 'terminated', terminated_at: '2026-08-25T15:54:23Z', join_date: '2024-08-12' },
  { id: 5, full_name: 'No hire date', period_id: 2, has_period_row: true, period_is_in_scope: true, join_date: null },
  { id: 6, full_name: 'No row', period_id: 2, has_period_row: false, join_date: '2026-09-01' },
];

test('item 5: five states, each distinct from the others and from «в оценке»', () => {
  assert.deepEqual(stateRoster.map(evaluationStateOf), [
    EVALUATION_STATES.IN_EVALUATION,
    EVALUATION_STATES.EXCLUDED_BY_ADMIN,
    EVALUATION_STATES.HIRED_AFTER_PERIOD_END,
    EVALUATION_STATES.TERMINATED,
    EVALUATION_STATES.JOIN_DATE_MISSING,
    EVALUATION_STATES.NO_PERIOD_ROW,
  ]);
  assert.equal(new Set(stateRoster.map(evaluationStateOf)).size, 6);
});

test('item 5: an unknown exclusion reason never reads as participation', () => {
  const unknown = { id: 9, period_id: 2, has_period_row: true, period_is_in_scope: false, period_exclusion_reason: 'something_new', join_date: '2020-01-01' };
  assert.notEqual(evaluationStateOf(unknown), EVALUATION_STATES.IN_EVALUATION);
  assert.equal(evaluationStateOf(unknown), EVALUATION_STATES.EXCLUDED_BY_ADMIN);
});

test('item 5: the state filter narrows and its options carry live counts', () => {
  assert.ok(FILTER_KEYS.includes('evaluation_state'));
  assert.equal(INITIAL_FILTERS.evaluation_state, 'all');
  // Default view: employment=active hides the leaver, everybody else stays.
  assert.deepEqual(filterUsers(stateRoster, INITIAL_FILTERS).map((u) => u.id), [1, 2, 3, 5, 6]);
  const narrowed = { ...INITIAL_FILTERS, evaluation_state: EVALUATION_STATES.EXCLUDED_BY_ADMIN };
  assert.deepEqual(filterUsers(stateRoster, narrowed).map((u) => u.id), [2]);

  const facets = buildFacets(stateRoster, INITIAL_FILTERS);
  const byValue = Object.fromEntries(facets.evaluation_state.map((o) => [o.value, o.count]));
  assert.equal(byValue[EVALUATION_STATES.IN_EVALUATION], 1);
  assert.equal(byValue[EVALUATION_STATES.EXCLUDED_BY_ADMIN], 1);
  // The leaver is a real state in the population, offered with the count the
  // employment filter would leave — zero, visible before the click (D-0825-8).
  assert.equal(byValue[EVALUATION_STATES.TERMINATED], 0);
});

test('item 5: the route returns what the state is derived from', () => {
  const code = nodeCode(loadFrom(OUT, 'admin-users-data.json'), 'Build Users Query');
  assert.match(code, /WITH active_period AS/);
  assert.match(code, /epp\.is_in_scope AS period_is_in_scope/);
  assert.match(code, /epp\.exclusion_reason AS period_exclusion_reason/);
  assert.match(code, /\(epp\.user_id IS NOT NULL\) AS has_period_row/);
  assert.match(code, /to_char\(u\.join_date, 'YYYY-MM-DD'\) AS join_date/);
  // LEFT JOIN, or a person with no participants row vanishes from the roster
  // and the page empties out whenever no period is active.
  assert.match(code, /LEFT JOIN performance_db\.evaluation_period_participants epp/);
});

test('item 5: the state column and control are off wherever the payload cannot feed them', () => {
  assert.match(read('src/components/admin/UserTable.jsx'), /showEvaluationState = false,/);
  assert.match(read('src/components/admin/UserFilters.jsx'), /showEvaluationState = false/);
  const admin = read('src/pages/AdminUsers.jsx');
  assert.match(admin, /showEvaluationState\n/);
  assert.doesNotMatch(read('src/pages/TeamView.jsx'), /showEvaluationState/);
});

// ── item 6 ──────────────────────────────────────────────────────────────────

test('item 6: the matrix header is the union of every row, not employees[0]', () => {
  const general = { id: 1, criteria: [{ criteria_id: 3 }, { criteria_id: 4 }] };
  const project = { id: 2, criteria: [{ criteria_id: 3 }, { criteria_id: 8, target_audience: 'project_participants' }] };
  const manager = { id: 3, criteria: [{ criteria_id: 2, target_audience: 'managers_only' }, { criteria_id: 1, c_level_only: true }] };
  const ids = buildSharedCriteriaList([general, project, manager]).map((c) => c.criteria_id);
  assert.deepEqual(ids.slice().sort((a, b) => a - b), [1, 2, 3, 4, 8]);
  assert.match(read('src/hooks/useFinalScoresMatrix.js'), /buildSharedCriteriaList\(rawEmployees\)/);
  assert.doesNotMatch(read('src/hooks/useFinalScoresMatrix.js'), /rawEmployees\[0\]\.criteria/);
});

test('item 6: managers_only applicability is identical in the matrix and in the close', () => {
  const matrix = nodeCode(loadFrom(OUT_DEFERRED, 'evaluations-matrix.json'), 'Build Matrix Query');
  assert.match(matrix, /c\.target_audience <> 'managers_only' OR u\.has_subordinates = true/);
  const close = nodeCode(loadFrom(OUT, 'manage-periods.json'), 'Build Close Dataset Query');
  assert.match(close, /cd\.target_audience <> 'managers_only'\s*\n?\s*OR u\.has_subordinates = true/);
});

test('item 6: the money totals count the pool, not the page', () => {
  const hook = read('src/hooks/useFinalScoresMatrix.js');
  assert.match(hook, /if \(emp\.takes_bonus_share === false\) return;/);
  assert.match(hook, /averageWeightedScore: poolCount > 0/);
});

// ── item 7 ──────────────────────────────────────────────────────────────────

test('item 7: the amounts sum to the budget exactly, at every awkward ratio', () => {
  const cases = [
    { rows: [{ key: 1, index: 1 }, { key: 2, index: 1 }, { key: 3, index: 1 }], budget: 100 },
    { rows: [{ key: 1, index: 118.92 }, { key: 2, index: 356.76 }, { key: 3, index: 35.68 }], budget: 3000000 },
    { rows: Array.from({ length: 80 }, (_, i) => ({ key: i, index: 1 + (i % 7) * 0.37 })), budget: 2500000.55 },
    { rows: [{ key: 1, index: 7 }, { key: 2, index: 0 }], budget: 999.99 },
  ];
  for (const { rows, budget } of cases) {
    const amounts = distributeBudget(rows, budget);
    const sum = [...amounts.values()].reduce((a, b) => a + b, 0);
    assert.equal(Math.round(sum * 100), Math.round(budget * 100),
      `budget ${budget} over ${rows.length} rows reconciles`);
  }
});

test('item 7: shares stay proportional to the index — the sum is not smeared', () => {
  const amounts = distributeBudget([{ key: 'a', index: 300 }, { key: 'b', index: 100 }], 4000);
  assert.equal(amounts.get('a'), 3000);
  assert.equal(amounts.get('b'), 1000);
});

test('item 7: nothing to distribute yields zeros, never NaN', () => {
  const rows = [{ key: 1, index: 0 }, { key: 2, index: 0 }];
  assert.deepEqual([...distributeBudget(rows, 1000).values()], [0, 0]);
  assert.deepEqual([...distributeBudget(rows, 0).values()], [0, 0]);
  assert.deepEqual([...distributeBudget([], 1000).values()], []);
});

test('item 7: a ru-locale budget parses as typed', () => {
  assert.equal(parseHumanNumber('3.000.000'), 3000000);
  assert.equal(parseHumanNumber('3 000 000'), 3000000);
  assert.equal(parseHumanNumber('3 000 000'), 3000000);
  assert.equal(parseHumanNumber('1.234,56'), 1234.56);
  assert.equal(parseHumanNumber('1,234.56'), 1234.56);
  assert.equal(parseHumanNumber('1234,56'), 1234.56);
  assert.equal(parseHumanNumber(''), 0);
  assert.equal(parseHumanNumber('abc'), 0);
});

test('item 7: the integer point price is gone from the screen', () => {
  const page = read('src/pages/BonusCalculation.jsx');
  assert.doesNotMatch(page, /roundToInt/);
  assert.match(page, /distributeBudget\(/);
  assert.match(page, /pointValue: totalPoints > 0 \? budget \/ totalPoints : 0/);
});

// ── item 8 ──────────────────────────────────────────────────────────────────

test('item 8: the pool rule is a predicate on two fields, not a list of ids', () => {
  const util = read('src/utils/matrixUtils.js');
  const page = read('src/pages/BonusCalculation.jsx');
  for (const id of ['18', '21', '40', '47', '61']) {
    assert.doesNotMatch(util, new RegExp(`id\\s*===\\s*${id}`), `no hardcoded id ${id}`);
    assert.doesNotMatch(page, new RegExp(`id\\s*===\\s*${id}`), `no hardcoded id ${id}`);
  }
  assert.doesNotMatch(util, /cem@|hemra@|mekan@/);
});

test('item 8: the rule removes exactly the two named populations', () => {
  const roster = [
    { id: 10, is_in_scope: true, can_be_evaluated: true },   // ordinary
    { id: 18, is_in_scope: true, can_be_evaluated: false },  // evaluated by nobody
    { id: 25, is_in_scope: false, can_be_evaluated: true },  // out of period scope
    { id: 51, is_in_scope: false, can_be_evaluated: false }, // both
  ];
  assert.deepEqual(roster.filter(takesBonusShare).map((r) => r.id), [10]);
  // A row that simply never carried the flags (an older payload) must not be
  // silently dropped out of the money: absent is not false.
  assert.equal(takesBonusShare({ id: 99 }), true);
});

test('item 8: the excluded are named on screen, not silently removed', () => {
  const page = read('src/pages/BonusCalculation.jsx');
  assert.match(page, /not-in-pool-list/);
  assert.match(page, /Не берут долю фонда/);
  assert.match(page, /не оценивается никем/);
  assert.match(page, /вне охвата периода/);
});

// ── item 9: the one day-one defect the walkthrough found and this session fixed

test('item 9: HR can reach the tasks the portal tells them they have', () => {
  const sidebar = read('src/components/Sidebar.jsx');
  // The personal group is no longer suppressed for HR. Both HR people are in H1
  // scope, `can_be_evaluated`, and API: Submit Self Review accepts role `hr` —
  // so Welcome listed «Самооценка» as their task while the navigation offered
  // no route to the form.
  assert.doesNotMatch(sidebar, /\{!isHR\(safeUser\.role\) && \(\s*\n\s*<NavGroup title="Личные"/);
  assert.match(sidebar, /const showTaskPanel = true;/);
  // The HR panel itself is unchanged, and the team group stays manager-only.
  assert.match(sidebar, /\{isHR\(safeUser\.role\) && \(\s*\n\s*<NavGroup title="HR Панель"/);
  assert.match(sidebar, /!isOutOfScope && !isHR\(safeUser\.role\) && \(hasSubordinates/);
});
