/**
 * WELCOME_PERIOD_NOTICE — period banner, restored owner visibility copy,
 * criterion-2 title, and the three distinguishable states.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  buildPeriodNotice,
  extractPeriodMeta,
  PERIOD_NOTICE_BODY,
  PERIOD_NOTICE_STATE_LINES,
} from '../src/utils/periodNotice.js';
import { formatPeriodDateRu } from '../src/utils/formatPeriodDateRu.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');

const PARENT_OF_C02377D = 'a86e45b';

const OWNER_ANONYMITY =
  'Оценка вашего менеджера остается <strong>анонимной</strong> - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.';
const OWNER_PURPLE =
  'Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.';

test('formatPeriodDateRu uses Russian month names and does not shift a UTC midnight date', () => {
  assert.equal(formatPeriodDateRu('2026-01-01'), '1 января 2026');
  assert.equal(formatPeriodDateRu('2026-06-30'), '30 июня 2026');
  assert.equal(formatPeriodDateRu('2026-01-01T00:00:00.000Z'), '1 января 2026');
  assert.equal(formatPeriodDateRu(new Date('2026-06-30T00:00:00.000Z')), '30 июня 2026');
  assert.equal(formatPeriodDateRu(null), null);
  assert.equal(formatPeriodDateRu(''), null);
});

test('extractPeriodMeta reads optional name/dates and handles the no-period employees shape', () => {
  // Draft / no current period: the server sends the three meta keys as null.
  const today = extractPeriodMeta({
    success: true,
    campaign_active: false,
    period_in_preparation: false,
    current_period_id: null,
    current_period_status: null,
    period_name: null,
    period_start_date: null,
    period_end_date: null,
    actor_is_in_scope: null,
    data: [],
  });
  assert.deepEqual(today, { periodName: null, startDate: null, endDate: null });

  const future = extractPeriodMeta({
    campaign_active: true,
    period_in_preparation: false,
    period_name: 'H1-EXAMPLE',
    start_date: '2026-01-01',
    end_date: '2026-06-30',
  });
  assert.equal(future.periodName, 'H1-EXAMPLE');
  assert.equal(future.startDate, '2026-01-01');
  assert.equal(future.endDate, '2026-06-30');
});

test('extractPeriodMeta reads the exact keys GET /api/employees now serves (EMPLOYEES_PERIOD_META)', () => {
  const served = extractPeriodMeta({
    success: true,
    campaign_active: false,
    period_in_preparation: true,
    current_period_id: 2,
    current_period_status: 'active',
    period_name: 'H1-2026',
    period_start_date: '2026-01-01',
    period_end_date: '2026-06-30',
    actor_is_in_scope: true,
    data: [],
  });
  assert.deepEqual(served, {
    periodName: 'H1-2026',
    startDate: '2026-01-01',
    endDate: '2026-06-30',
  });
});

test('three period-notice states: copy, title/scope visibility, mocked responses', () => {
  const none = buildPeriodNotice({
    campaignActive: false,
    periodInPreparation: false,
  });
  assert.equal(none.state, 'none');
  assert.equal(none.showTitle, false);
  assert.equal(none.showScope, false);
  assert.equal(none.title, null);
  assert.equal(none.scope, null);
  assert.equal(none.body, PERIOD_NOTICE_BODY);
  assert.equal(none.stateLine, PERIOD_NOTICE_STATE_LINES.none);

  const prepNoDates = buildPeriodNotice({
    campaignActive: false,
    periodInPreparation: true,
  });
  assert.equal(prepNoDates.state, 'preparation');
  assert.equal(prepNoDates.showTitle, false);
  assert.equal(prepNoDates.showScope, false);
  assert.equal(prepNoDates.stateLine, PERIOD_NOTICE_STATE_LINES.preparation);

  const prepWithDates = buildPeriodNotice({
    campaignActive: false,
    periodInPreparation: true,
    periodName: 'Half-A',
    startDate: '2026-01-01',
    endDate: '2026-06-30',
  });
  assert.equal(prepWithDates.state, 'preparation');
  assert.equal(prepWithDates.showTitle, true);
  assert.equal(prepWithDates.showScope, true);
  assert.equal(
    prepWithDates.title,
    'Промежуточная оценка: Half-A (1 января 2026 — 30 июня 2026)',
  );
  assert.equal(
    prepWithDates.scope,
    'Сейчас оценивается работа за период с 1 января 2026 по 30 июня 2026. Оценивайте только этот период: то, что произошло после 30 июня 2026, относится ко второму полугодию и будет учтено в следующей оценке.',
  );

  const started = buildPeriodNotice({
    campaignActive: true,
    periodInPreparation: false,
    periodName: 'Half-A',
    startDate: '2026-01-01',
    endDate: '2026-06-30',
  });
  assert.equal(started.state, 'started');
  assert.equal(started.stateLine, PERIOD_NOTICE_STATE_LINES.started);
  assert.equal(started.showTitle, true);

  const noneIgnoresDates = buildPeriodNotice({
    campaignActive: false,
    periodInPreparation: false,
    periodName: 'Half-A',
    startDate: '2026-01-01',
    endDate: '2026-06-30',
  });
  assert.equal(noneIgnoresDates.showTitle, false);
  assert.equal(noneIgnoresDates.showScope, false);
});

test('restored Welcome visibility strings equal the git originals (parent of c02377d)', () => {
  const current = read('src/pages/Welcome.jsx');
  const original = execSync(`git show ${PARENT_OF_C02377D}:src/pages/Welcome.jsx`, {
    cwd: root,
    encoding: 'utf8',
  });

  const count = (src, needle) => src.split(needle).length - 1;
  assert.equal(count(original, OWNER_ANONYMITY), 2, 'parent has two anonymity boxes');
  assert.equal(count(original, OWNER_PURPLE), 1, 'parent has one purple box');
  assert.equal(count(current, OWNER_ANONYMITY), 2, 'working copy restored both anonymity boxes');
  assert.equal(count(current, OWNER_PURPLE), 1, 'working copy restored the purple box');
  assert.equal(count(current, OWNER_ANONYMITY) - count(original, OWNER_ANONYMITY), 0);
  assert.equal(count(current, OWNER_PURPLE) - count(original, OWNER_PURPLE), 0);
});

test('Welcome period notice is above the task area; out-of-scope still sees it', () => {
  const welcome = read('src/pages/Welcome.jsx');
  const noticeIdx = welcome.indexOf('<PeriodNotice notice={periodNotice} />');
  const taskIdx = welcome.indexOf('Ваши задачи');
  // D-0825-11: the notice now takes the exclusion reason, so the copy can say
  // the true thing instead of the one sentence that only fits a late hire.
  const outIdx = welcome.indexOf('<OutOfScopeNotice embedded reason={outOfScopeReason} />');
  assert.ok(noticeIdx > 0, 'PeriodNotice is mounted');
  assert.ok(taskIdx > noticeIdx, 'PeriodNotice precedes the task heading');
  assert.ok(outIdx > 0, 'OutOfScopeNotice stays on the out-of-scope path');
  assert.match(welcome, /showManagerTrack/);
  assert.match(welcome, /user\?\.has_subordinates/);
  assert.doesNotMatch(welcome, /H1-2026/);
  assert.doesNotMatch(welcome, /2026-06-30/);
});

test('src/ has no hardcoded H1-2026 or 2026-06-30', () => {
  const listed = execSync(
    "rg -l 'H1-2026|2026-06-30' src || true",
    { cwd: root, encoding: 'utf8' },
  ).trim();
  assert.equal(listed, '', `hardcoded period literals in src/: ${listed}`);
});

test('CriteriaOverview quotes the real criterion-2 title, not the fake name', () => {
  const overview = read('src/components/profile/CriteriaOverview.jsx');
  assert.doesNotMatch(overview, /Критерий для оценки руководителя/);
  assert.match(overview, /Number\(criterion\.id\) === 2/);
  assert.match(overview, /Качество управления и развитие команды/);
});

test('Welcome still uses the real criterion title', () => {
  const welcome = read('src/pages/Welcome.jsx');
  assert.doesNotMatch(welcome, /Критерий для оценки руководителя/);
  assert.match(welcome, /Качество управления и развитие команды/);
});

test('GET /api/employees is the notice feed; GET /api/periods is not called from Welcome', () => {
  const welcome = read('src/pages/Welcome.jsx');
  const context = read('src/context/TaskStatusContext.jsx');
  assert.match(context, /API_ENDPOINTS\.EMPLOYEES/);
  assert.match(context, /extractPeriodMeta/);
  assert.doesNotMatch(welcome, /API_ENDPOINTS\.PERIODS/);
  assert.doesNotMatch(context, /API_ENDPOINTS\.PERIODS/);
});
