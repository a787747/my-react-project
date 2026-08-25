/**
 * PRELAUNCH_GUIDE_AND_ZONES — verbatim H1 guide placement and score-band labels.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  RATING_GUIDE_TITLE,
  RATING_GUIDE_RULES,
  EMPLOYEE_GUIDE_RULE_NUMBERS,
  formatRatingGuideRule,
  getRatingGuideRules,
} from '../src/content/ratingGuideH1.js';
import {
  calculateFinalScore,
  getScoreScale,
  getScoreZone,
} from '../src/utils/evaluationUtils.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');

const VERBATIM_RULES = [
  '1. Оцениваете факты по критериям за этот период. Только факты первого полугодия 2026: не должность, не стаж, не прошлый год, не потенциал, не дружбу, не общее впечатление. Последний месяц не важнее первых пяти.',
  '2. Норма — это 6. Уровень 6 = «выполняет ожидания, нареканий нет». Это хорошая оценка, а не «серединка»; 5 — «в целом справляется, требует внимания». Не бойтесь ставить 6 большинству.',
  '3. Критерий «Ответственность сверх роли»: норма — 2, и это не упрёк. 2 = «делал своё, сверхзадач не возникало» — состояние большинства. Выше 2 — только за конкретный взятый сверх роли факт. Критерий «Объем проектной работы и загрузка» — шкала объёма, а не качества: 2–3 у консультанта — это факт малого объёма, не плохая работа.',
  '4. Крайние оценки — только с фактом. Ставите 1–2 или 9–10 — назовите конкретный факт в комментарии. Без факта такая оценка не переживёт калибровку.',
  '5. Чего не оцениваем: лояльность, похожесть на себя, часы и переработки, «своего человека», обещания, намерения. Оцениваем результат и наблюдаемое поведение.',
  '6. Оценка руководителя — возможность дать ему объективную обратную связь для развития. Критерий «Качество управления и развитие команды». Цель — помочь руководителю расти. Ставьте по тому, что видели сами: постановка задач, объяснение «зачем», обратная связь, атмосфера, помощь при проблемах, поддержка в исполнении, но не работа за вас.',
  '7. Самооценка: оцените, как по фактам периода оценил бы вас руководитель. Расхождение с его оценкой — не ошибка и не наказание, а материал для разговора. Эта оценка важна ещё и для того, чтобы вы понимали, как вас оценивают.',
  '8. Описания уровней — обычное поведение, не разовый случай. Оценивайте то, как человек работал обычно в течение периода, а не один удачный или неудачный эпизод. Если подходят два уровня — берите тот, чьё «ядро» точнее описывает типичное поведение.',
];

test('rating guide title and eight rules are verbatim', () => {
  assert.equal(RATING_GUIDE_TITLE, 'Как ставить оценки — 8 правил H1');
  assert.equal(RATING_GUIDE_RULES.length, 8);
  RATING_GUIDE_RULES.forEach((rule, index) => {
    assert.equal(formatRatingGuideRule(rule), VERBATIM_RULES[index]);
  });
});

test('employee subset is rules 1, 6 and 7 only', () => {
  assert.deepEqual(EMPLOYEE_GUIDE_RULE_NUMBERS, [1, 6, 7]);
  const employee = getRatingGuideRules('employee');
  assert.deepEqual(employee.map((r) => r.n), [1, 6, 7]);
  assert.equal(employee.length, 3);
});

test('Welcome manager track mounts the full guide; employee track mounts 1/6/7', () => {
  const welcome = read('src/pages/Welcome.jsx');
  const managerIdx = welcome.indexOf('Процесс оценки (для менеджеров с подчиненными)');
  const employeeIdx = welcome.indexOf('Процесс оценки (для сотрудников без подчиненных)');
  const extraIdx = welcome.indexOf('Дополнительные критерии');
  assert.ok(managerIdx > 0 && employeeIdx > managerIdx);
  const managerBlock = welcome.slice(managerIdx, employeeIdx);
  const employeeBlock = welcome.slice(employeeIdx, extraIdx);
  assert.match(managerBlock, /<RatingGuide variant="full" \/>/);
  assert.doesNotMatch(managerBlock, /variant="employee"/);
  assert.match(employeeBlock, /<RatingGuide variant="employee" \/>/);
  assert.doesNotMatch(employeeBlock, /variant="full"/);
});

test('Welcome and criteria cards share one title/body type scale', () => {
  const overview = read('src/components/profile/CriteriaOverview.jsx');
  const welcome = read('src/pages/Welcome.jsx');
  const period = read('src/components/common/PeriodNotice.jsx');
  assert.match(overview, /text-base font-semibold text-gray-900 mb-1 leading-normal/);
  assert.match(overview, /text-sm text-gray-600 mb-2 leading-normal/);
  assert.match(welcome, /text-base font-semibold text-brand-900 mb-1 leading-normal/);
  assert.match(welcome, /text-sm text-brand-800 leading-normal/);
  assert.match(welcome, /text-sm text-slate-700 leading-normal mb-3/);
  assert.match(period, /text-xl md:text-xl font-bold text-slate-900 mb-2 leading-normal/);
  assert.match(period, /text-sm text-slate-700 leading-normal mb-3/);
  assert.doesNotMatch(welcome, /leading-relaxed/);
  assert.doesNotMatch(period, /leading-relaxed/);
});

test('Welcome extra-criteria card describes project criteria, not management', () => {
  const welcome = read('src/pages/Welcome.jsx');
  const extraIdx = welcome.indexOf('Дополнительные критерии');
  const extra = welcome.slice(extraIdx);
  assert.match(extra, /Взаимодействие и надежность в проекте/);
  assert.match(extra, /вклад в общий результат, а не только выполнение своей функции/);
  assert.match(extra, /Объем проектной работы и загрузка/);
  assert.match(extra, /долю рабочего времени, занятую проектом/);
  assert.match(extra, /не ограничивался рутинной работой/);
  assert.doesNotMatch(extra, /только у участников проектов/);
  assert.doesNotMatch(extra, /Качество управления и развитие команды/);
});

test('manager evaluation form reaches the full guide in one click', () => {
  const modal = read('src/components/EvaluationModal.jsx');
  assert.match(modal, /<RatingGuide variant="full" collapsible defaultOpen=\{false\} \/>/);
});

test('employee upward and self-assessment surfaces show the employee guide', () => {
  assert.match(read('src/pages/ManagerEvaluation.jsx'), /<RatingGuide variant="employee" \/>/);
  assert.match(read('src/pages/SelfReview.jsx'), /<RatingGuide variant="employee" \/>/);
  assert.match(read('src/components/self-review/SelfReviewModal.jsx'), /<RatingGuide variant="employee" \/>/);
});

test('self-review no longer promises yellow/green zones', () => {
  const selfReview = read('src/pages/SelfReview.jsx');
  assert.doesNotMatch(selfReview, /желтую и зеленую зоны/);
  assert.doesNotMatch(selfReview, /85-90%/);
});

test('default scale: 6 is the first Хорошо; 5 is attention, not good', () => {
  assert.equal(getScoreZone(5).label, 'В целом справляется, требует внимания');
  assert.equal(getScoreZone(6).label, 'Хорошо');
  assert.equal(getScoreZone(7).label, 'Хорошо');
  assert.notEqual(getScoreZone(5).label, 'Хорошо');
  assert.notEqual(getScoreZone(5).label, 'Зона нормы');
  assert.notEqual(getScoreZone(6).label, 'Зона нормы');
  assert.equal(getScoreZone(2).label, 'Зона риска');
  assert.equal(getScoreZone(4).label, 'Ниже ожиданий');
  assert.equal(getScoreZone(8).label, 'Выше нормы');
  assert.equal(getScoreZone(9).label, 'Зона исключительности');
});

test('criterion 14: norm is 2; above 2 is beyond-role, not a quality grade', () => {
  assert.equal(getScoreScale(14), 'beyond_role');
  assert.equal(getScoreScale({ id: 14 }), 'beyond_role');
  assert.equal(getScoreScale({ criteria_id: 14 }), 'beyond_role');
  assert.equal(getScoreZone(1, 14).label, 'Ниже нормы');
  assert.equal(getScoreZone(2, 14).label, 'Норма');
  assert.equal(getScoreZone(5, 14).label, 'Сверх роли');
  assert.notEqual(getScoreZone(5, 14).label, 'В целом справляется, требует внимания');
  assert.equal(getScoreZone(8, 14).label, 'Крупный вклад сверх роли');
});

test('criterion 13: low is small volume, not bad work; 6 is volume norm', () => {
  assert.equal(getScoreScale(13), 'volume');
  assert.equal(getScoreZone(3, 13).label, 'Малый объём');
  assert.notEqual(getScoreZone(3, 13).label, 'Зона риска');
  assert.equal(getScoreZone(5, 13).label, 'Умеренный объём');
  assert.equal(getScoreZone(6, 13).label, 'Норма объёма');
  assert.equal(getScoreZone(9, 13).label, 'Высокий объём');
});

test('calculateFinalScore is unchanged (plain average, two decimals)', () => {
  assert.equal(calculateFinalScore({ a: 5, b: 7 }, 1), '6.00');
  assert.equal(calculateFinalScore({ a: 6 }, 1.5), '9.00');
});

test('matrix and slider call sites pass the criterion into the zone helper', () => {
  assert.match(read('src/components/CriterionSlider.jsx'), /getScoreZone\(currentScore, criterion\)/);
  assert.match(read('src/components/EvaluationModal.jsx'), /getScoreZone\(score, criterion\)/);
  assert.match(read('src/pages/ManagerSubordinatesMatrix.jsx'), /getScoreStyle\(score, criterion\)/);
  assert.match(read('src/components/admin/ScoreDetailModal.jsx'), /getScoreZone\(score, criterion\)/);
  // Inverted 2026-08-25. The zones in evaluationUtils describe a raw 1–10
  // score; this call site was handing them the WEIGHTED product, so criterion
  // 14 at its documented norm of 2 painted as «сверх роли» (2 × 1.00 × 1.50 =
  // 3.00) and criterion 12 at 7 painted «зона исключительности» (7 × 1.30 ×
  // 1.00 = 9.10). The cell now colours by the raw score and prints the
  // weighted one.
  assert.match(read('src/components/admin/FinalScoresMatrixTable.jsx'), /getScoreColor\(rawScore, c\)/);
  assert.doesNotMatch(read('src/components/admin/FinalScoresMatrixTable.jsx'), /getScoreColor\(criterionScore/);
});

test('manager-subordinates legend no longer calls 5–7 Хорошо', () => {
  const matrix = read('src/pages/ManagerSubordinatesMatrix.jsx');
  assert.doesNotMatch(matrix, /5-7/);
  assert.match(matrix, /6-7/);
  assert.match(matrix, /В целом справляется, требует внимания/);
});

test('Analytics pie buckets stay hard-wired (surfaced, not retargeted)', () => {
  const analytics = read('src/pages/Analytics.jsx');
  assert.match(analytics, /if \(score >= 8\) acc\.excellent\+\+/);
  assert.match(analytics, /else if \(score >= 6\) acc\.good\+\+/);
  assert.match(analytics, /else if \(score >= 4\) acc\.average\+\+/);
  assert.match(analytics, /Отлично \(8-10\)/);
  assert.match(analytics, /Хорошо \(6-8\)/);
});
