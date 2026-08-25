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
  '1. Оцениваете период, не человека. Только факты H1 2026: не должность, не стаж, не прошлый год, не потенциал. Последний месяц не важнее первых пяти.',
  '2. Норма — это 6. По критериям 3, 4, 8, 10, 12, 13 (и 2 для руководителей) уровень 6 = «выполняет ожидания, нареканий нет». Это хорошая оценка, а не «серединка»; 5 — «в целом справляется, требует внимания». Не бойтесь ставить 6 большинству.',
  '3. Критерий 14: норма — 2, и это не упрёк. 2 = «делал своё, сверхзадач не возникало» — состояние большинства. Выше 2 — только за конкретный взятый сверх роли факт. Критерий 13 — шкала объёма, а не качества: 2–3 у консультанта — это факт малого объёма, не плохая работа.',
  '4. Один факт оплачивается один раз. Свой объём в проекте → 13. Чужая работа или участок, взятые и сделанные → 14 (даже у проектного). Помощь и взаимодействие в проекте → 8; принятая ответственность за участок → 14. Качество своей функции → 3; удобство работы с вами руководителя → 4. Изучил новое → 12; отвечал за новое → 14.',
  '5. Крайние оценки — только с фактом. Ставите 1–2 или 9–10 — назовите конкретный факт в комментарии. Без факта такая оценка не переживёт калибровку.',
  '6. Чего не оцениваем: лояльность, похожесть на себя, часы и переработки, «своего человека», обещания. Оцениваем результат и наблюдаемое поведение.',
  '7. Оцениваете своего руководителя (критерий 2): ставьте только по тому, что видели сами — постановка задач, объяснение «зачем», обратная связь, атмосфера, помощь при проблемах. Не гадайте про «кадровый резерв» и «школу кадров» — это видно только сверху.',
  '8. Самооценка (3, 4, 12): оцените, как по фактам периода оценил бы вас руководитель. Расхождение с его оценкой — не ошибка и не наказание, а материал для разговора.',
  '9. C-level (1 и 10): по 1 оценивайте фактическую роль периода, как сказано в описании критерия, а не строчку в штатном расписании. По 10 перед оценкой ниже 6 «потому что не знаю человека» — выполните текст критерия: спросите тех, кто с ним работает. Сверьте оценки между собой.',
  '10. Описания уровней — архетипы. Выбирайте доминирующий паттерн периода, а не худший эпизод и не среднее арифметическое. Если подходят два уровня — берите тот, чьё «ядро» точнее описывает главный факт периода.',
];

test('rating guide title and ten rules are verbatim', () => {
  assert.equal(RATING_GUIDE_TITLE, 'Как ставить оценки — 10 правил H1');
  assert.equal(RATING_GUIDE_RULES.length, 10);
  RATING_GUIDE_RULES.forEach((rule, index) => {
    assert.equal(formatRatingGuideRule(rule), VERBATIM_RULES[index]);
  });
});

test('employee subset is rules 1, 7 and 8 only', () => {
  assert.deepEqual(EMPLOYEE_GUIDE_RULE_NUMBERS, [1, 7, 8]);
  const employee = getRatingGuideRules('employee');
  assert.deepEqual(employee.map((r) => r.n), [1, 7, 8]);
  assert.equal(employee.length, 3);
});

test('Welcome manager track mounts the full guide; employee track mounts 1/7/8', () => {
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

test('manager evaluation form reaches the full guide in one click', () => {
  const modal = read('src/components/EvaluationModal.jsx');
  assert.match(modal, /<RatingGuide variant="full" collapsible defaultOpen=\{false\} \/>/);
});

test('employee upward and self-assessment surfaces show rules 1, 7 and 8', () => {
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
  assert.match(read('src/components/admin/FinalScoresMatrixTable.jsx'), /getScoreColor\(criterionScore, c\)/);
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
