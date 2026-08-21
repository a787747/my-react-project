/**
 * moneyScreenGuards.test.js
 *
 * The two client-side guards added after the 2026-08-21 acceptance verification:
 *
 *  M6 — a failed coefficients (or grades, or matrix) fetch must surface as an
 *       explicit error, never as a silently unweighted bonus table.
 *  M1 — /admin/periods renders its write controls for admin only, and «Закрыть
 *       период» is confirmed by typing the period name, not by one click.
 *
 * These are React sources, so the assertions are made against the source text —
 * the same approach apiClientConfig.test.js uses for the API client.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');

const hook = read('src/hooks/useFinalScoresMatrix.js');
const finalScores = read('src/pages/AdminFinalScores.jsx');
const bonus = read('src/pages/BonusCalculation.jsx');
const periods = read('src/pages/AdminPeriods.jsx');
const permissions = read('src/utils/permissions.js');

// ── M6: no silent defaults on the money pipeline ──────────────────────────

test('the coefficients and grades fetches no longer swallow their failures', () => {
  assert.doesNotMatch(
    hook,
    /SCORE_COEFFICIENTS\)\s*\.catch\(/,
    'a failed coefficients call must not fall back to an empty list'
  );
  assert.doesNotMatch(
    hook,
    /ADMIN_USERS_DATA\)\s*\.catch\(/,
    'a failed grades call must not fall back to an empty grade list'
  );
  assert.doesNotMatch(
    hook,
    /catch\(\(\)\s*=>\s*\(\{\s*data:/,
    'no request in this hook may substitute a fabricated empty response'
  );
});

test('every one of the three requests is classified, and any failure sets the error', () => {
  assert.match(hook, /Promise\.allSettled\(\[/, 'failures must be distinguishable per request');
  for (const key of ['matrix', 'coefficients', 'grades']) {
    assert.match(
      hook,
      new RegExp(`failures\\.push\\(LOAD_ERRORS\\.${key}\\)`),
      `a failed ${key} request must be recorded`
    );
  }
  assert.match(
    hook,
    /coefficients: 'Коэффициенты не загружены — расчёт невозможен'/,
    'the coefficients failure carries the agreed message'
  );
  assert.match(hook, /setError\(failures\.join/, 'the failures become the error state');
});

test('a failed load clears the numbers instead of rendering a degraded table', () => {
  const failureBlock = hook.slice(
    hook.indexOf('if (failures.length > 0)'),
    hook.indexOf('const matrixResponse = matrixResult.value')
  );
  assert.ok(failureBlock.length > 0, 'the failure branch must exist');
  for (const setter of ['setEmployees([])', 'setCriteriaList([])', 'setPeriod(null)']) {
    assert.ok(failureBlock.includes(setter), `the failure branch must run ${setter}`);
  }
  assert.match(hook, /^\s*error,$/m, 'the hook must expose the error state to its screens');
});

test('both money screens render the error with a retry instead of numbers', () => {
  for (const [name, src] of [['Итоговые баллы', finalScores], ['Калькуляция бонусов', bonus]]) {
    assert.match(src, /^\s*error,$/m, `${name}: must consume the hook's error`);
    assert.match(src, /if \(error\) \{[\s\S]{0,1600}onClick=\{fetchData\}/,
      `${name}: the error branch must offer a retry`);
    const errorBranch = src.slice(src.indexOf('if (error) {'));
    assert.ok(
      errorBranch.indexOf('return (') < errorBranch.indexOf('MatrixFilters'),
      `${name}: the error branch must return before the table renders`
    );
  }
});

// ── M1: /admin/periods write controls are admin-only ──────────────────────

test('permissions exposes an admin-only check', () => {
  assert.match(permissions, /export const isAdmin = \(role\) => role === 'admin';/);
});

test('rename, reparent, activate and close render only for admin', () => {
  assert.match(periods, /import \{ isAdmin \} from '\.\.\/utils\/permissions'/);
  assert.match(periods, /const canManage = isAdmin\(user\?\.role\);/);
  // each of the four controls sits behind canManage
  assert.match(periods, /\{canManage && \(\s*<button[\s\S]{0,400}Переименовать/, 'rename is gated');
  assert.match(periods, /\{canManage && !isContainer\(period\) && \([\s\S]{0,700}FolderTree/, 'reparent is gated');
  assert.match(periods, /\{canManage && !period\.is_active[\s\S]{0,200}handleActivate/, 'activate is gated');
  assert.match(periods, /\{canManage && \(\s*<button\s*\n\s*onClick=\{\(\) => openCloseModal/, 'close is gated');
});

test('closing a period is confirmed by typing its name, not by window.confirm', () => {
  assert.doesNotMatch(
    periods,
    /window\.confirm\(\s*\n?\s*`Закрыть период/,
    'the close confirmation must no longer be a one-click confirm'
  );
  assert.match(periods, /closeModal, setCloseModal\] = useState\(\{ open: false, period: null, typed: '' \}\)/);
  assert.match(
    periods,
    /closeModal\.typed\.trim\(\) !== period\.name/,
    'the handler must refuse a mismatched name'
  );
  assert.match(
    periods,
    /disabled=\{[\s\S]{0,200}closeModal\.typed\.trim\(\) !== closeModal\.period\?\.name/,
    'the submit button stays disabled until the name matches'
  );
  assert.match(periods, /Действие необратимо/, 'the modal must still say the action is irreversible');
});

test('detaching a child that carries stored results asks first', () => {
  assert.match(
    periods,
    /isDetach && period\.parent_period_id && period\.has_results/,
    'the confirmation is scoped to a detach of a child with results'
  );
  assert.ok(
    periods.includes('перестанут учитываться в годовой сводке'),
    'the confirmation must say the results leave the annual roll-up'
  );
  assert.ok(
    periods.includes('рейтинг (среднее) и годовой индекс (сумма) участников изменятся'),
    'the confirmation must name the consequence: the annual numbers move'
  );
});
