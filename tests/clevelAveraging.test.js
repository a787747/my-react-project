/**
 * CLEVEL_AVERAGING — D-0826-1.
 *
 * When more than one C-level person files a direct evaluation on the same
 * subject in the same period, the scores are AVERAGED and the number of
 * evaluators is carried. Last-writer-wins is replaced.
 *
 * The pins, in the order the brief states them:
 *   item 1  both source rows persist — the write path conflicts on
 *           (subject, evaluator, source, period), so a second C-level person
 *           can never overwrite the first
 *   item 2  matrix SQL, close-dataset SQL and every client consumer read the
 *           mean, and the count travels with it
 *   item 2  one evaluator is identical to the old behaviour, to the digit
 *   item 3  a c_level CORRECTION still does not enter a c_level_only cell —
 *           unchanged, surfaced, and pinned so a later change is deliberate
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

import {
  formatCLevelChannel,
  formatCorrectionTooltip,
  formatScoreCompact,
  getCLevelChannel,
  getCriterionFinalScore,
} from '../src/utils/matrixUtils.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

const OUT = mkdtempSync(join(tmpdir(), 'clevel-wf-'));
execSync(`python3 "${join(root, 'scripts', 'build_route_guard_workflows.py')}" --output-directory "${OUT}"`,
  { cwd: root, stdio: 'pipe' });
const OUT_DEFERRED = mkdtempSync(join(tmpdir(), 'clevel-wf-def-'));
execSync(`python3 "${join(root, 'scripts', 'build_route_guard_deferred.py')}" --output-directory "${OUT_DEFERRED}"`,
  { cwd: root, stdio: 'pipe' });

const loadFrom = (dir, file) => JSON.parse(readFileSync(join(dir, file), 'utf8'));
const nodeCode = (workflow, name) => {
  const found = workflow.nodes.find((n) => n.name === name);
  assert.ok(found, `node «${name}» exists`);
  return found.parameters.jsCode ?? found.parameters.query ?? '';
};

const matrixQuery = () => nodeCode(loadFrom(OUT_DEFERRED, 'evaluations-matrix.json'), 'Build Matrix Query');
const closeDataset = () => nodeCode(loadFrom(OUT, 'manage-periods.json'), 'Build Close Dataset Query');
const closeCompute = () => nodeCode(loadFrom(OUT, 'manage-periods.json'), 'Compute Close Results');

// The CTE body, without its comment, so drift between the two workflows is a
// test failure rather than a money discrepancy nobody notices until close.
const cteBody = (sql) => {
  const start = sql.indexOf('c_level_direct_scores AS (');
  assert.ok(start > 0, 'the c_level_direct_scores CTE exists');
  const end = sql.indexOf('GROUP BY e.subject_id, es.criteria_id', start);
  assert.ok(end > start, 'the CTE groups by (subject, criterion)');
  return sql.slice(start, end + 'GROUP BY e.subject_id, es.criteria_id'.length);
};

// ── item 1: the write path never overwrites ────────────────────────────────

test('item 1: submit conflicts on (subject, evaluator, source, period) — a second C-level gets a row of their own', () => {
  const submit = nodeCode(loadFrom(OUT, 'submit-evaluation.json'), 'Build Insert SQL');
  assert.match(submit, /ON CONFLICT \(subject_id, evaluator_id, evaluation_source, period_id\)/);
  // The evaluator is part of the key, so nothing a second C-level writes can
  // land on the first one's row.
  assert.doesNotMatch(submit, /ON CONFLICT \(subject_id, evaluation_source, period_id\)/);
  // And the "does an evaluation of mine already exist" probe is per-evaluator.
  const validate = nodeCode(loadFrom(OUT, 'submit-evaluation.json'), 'Validate Evaluation');
  assert.match(validate, /dup\.evaluator_id = \$\{actorId\}/);
});

test('item 1: self-review is one row per (subject, period), refused by the database', () => {
  const self = nodeCode(loadFrom(OUT, 'self-review-submit.json'), 'Build Self Review Insert');
  assert.match(self, /ON CONFLICT \(subject_id, period_id\) WHERE is_self_evaluation = true DO NOTHING/);
  const format = nodeCode(loadFrom(OUT, 'self-review-submit.json'), 'Format Response');
  assert.match(format, /DUPLICATE_SELF_REVIEW/);
});

// ── item 2: the two SQL surfaces ───────────────────────────────────────────

test('item 2: the c_level_direct channel is averaged in the matrix, with a count', () => {
  const sql = matrixQuery();
  assert.match(sql, /'c_level_score', \(\s*SELECT ROUND\(cds\.avg_c_level_score::numeric, 2\)/);
  assert.match(sql, /'c_level_count', \(\s*SELECT cds\.c_level_count::integer/);
  assert.match(sql, /AVG\(es\.score_value\) as avg_c_level_score/);
  assert.match(sql, /COUNT\(\*\) as c_level_count/);
});

test('item 2: the close dataset is averaged the same way, with a count', () => {
  const sql = closeDataset();
  assert.match(sql, /'c_level_score', \(\s*SELECT ROUND\(cds\.avg_c_level_score::numeric, 2\)/);
  assert.match(sql, /'c_level_count', \(\s*SELECT cds\.c_level_count::integer/);
});

test('item 2: the CTE is character-for-character the same in both workflows', () => {
  assert.equal(cteBody(matrixQuery()), cteBody(closeDataset()));
});

test('item 2: no reader of the C-level channel picks one row by updated_at any more', () => {
  for (const sql of [matrixQuery(), closeDataset()]) {
    // The channel's cell no longer carries a latest-wins ORDER BY. The manager
    // and self channels still do, deliberately — this brief does not touch
    // them, and the pin below says so.
    const cell = sql.slice(sql.indexOf("'c_level_score'"), sql.indexOf("'mid_level_correction'"));
    assert.doesNotMatch(cell, /ORDER BY e\.updated_at DESC/);
    assert.match(cell, /c_level_direct_scores cds/);
  }
});

test('item 2: the manager and self channels are untouched — still latest-by-updated_at', () => {
  const sql = matrixQuery();
  const manager = sql.slice(sql.indexOf("'manager_score'"), sql.indexOf("'c_level_score'"));
  assert.match(manager, /ORDER BY e\.updated_at DESC\s*\n\s*LIMIT 1/);
  const self = sql.slice(sql.indexOf("'self_score'"), sql.indexOf("'manager_score'"));
  assert.match(self, /ORDER BY e\.updated_at DESC\s*\n\s*LIMIT 1/);
});

test('item 2: the close still reads the mean through c_level_score, and freezes no count', () => {
  const compute = closeCompute();
  assert.match(compute, /if \(crit\.c_level_only\) \{\s*\n\s*return crit\.c_level_score != null \? Number\(crit\.c_level_score\) : null;/);
  // period_results stores one row per person; a count is a property of one
  // cell, so no column was added and none is written.
  assert.doesNotMatch(compute, /c_level_count/i.test(compute) ? /c_level_count[^\n]*numLit/ : /^\b$/);
  assert.doesNotMatch(compute, /INSERT INTO performance_db\.period_results[\s\S]*c_level_count/);
});

// ── item 2: the client helpers ─────────────────────────────────────────────

test('item 2: two C-level evaluators, 4 and 8 — the channel reads 6 and the count reads 2', () => {
  // What the server sends for that cell after this change.
  const cell = { criteria_id: 1, c_level_only: true, c_level_score: 6.00, c_level_count: 2 };
  const channel = getCLevelChannel(cell);
  assert.equal(channel.score, 6);
  assert.equal(channel.count, 2);
  assert.equal(channel.averaged, true);
  assert.equal(getCriterionFinalScore(cell), 6);
  assert.equal(formatScoreCompact(channel.score), '6');
  assert.equal(formatCLevelChannel(cell), 'C-level: 6 (среднее по 2 оценкам)');
});

test('item 2: one C-level evaluator is identical to the old behaviour, to the digit', () => {
  const before = { criteria_id: 1, c_level_only: true, c_level_score: 8 };
  const after = { criteria_id: 1, c_level_only: true, c_level_score: 8, c_level_count: 1 };
  assert.equal(getCriterionFinalScore(before), getCriterionFinalScore(after));
  assert.equal(getCriterionFinalScore(after), 8);
  assert.equal(getCLevelChannel(after).averaged, false);
  assert.equal(formatCLevelChannel(after), 'C-level: 8');
});

test('item 2: an unscored C-level cell arrives null/null and reads as zero evaluators', () => {
  // Measured against live on 2026-08-26 after the deploy: with no evaluations
  // the CTE has no row for that cell, so BOTH the score and the count come back
  // null — the same shape `subordinate_count` has always had on the upward
  // channel. It must never read as a score of zero.
  const cell = { criteria_id: 10, c_level_only: true, c_level_score: null, c_level_count: null };
  assert.equal(getCriterionFinalScore(cell), null);
  assert.deepEqual(getCLevelChannel(cell), { score: null, count: 0, averaged: false });
  assert.equal(formatCLevelChannel(cell), null);
  // An explicit zero, if it ever arrives, means the same thing.
  assert.equal(getCLevelChannel({ c_level_score: null, c_level_count: 0 }).count, 0);
});

test('item 2: a payload without c_level_count behaves exactly as before D-0826-1', () => {
  assert.deepEqual(getCLevelChannel({ c_level_score: 7 }), { score: 7, count: 1, averaged: false });
  assert.deepEqual(getCLevelChannel({ c_level_score: null }), { score: null, count: 0, averaged: false });
});

test('item 2: a numeric arriving as a string is still a number to the calculation', () => {
  // ROUND(...)::numeric inside json_build_object serialises as a JSON number,
  // but a cached payload or a driver that stringifies numerics must not turn
  // the money cell into a concatenation.
  const cell = { c_level_only: true, c_level_score: '5.50', c_level_count: 2 };
  assert.equal(getCriterionFinalScore(cell), 5.5);
  assert.equal(typeof getCriterionFinalScore(cell), 'number');
  assert.equal(formatScoreCompact(getCriterionFinalScore(cell)), '5.5');
});

test('item 2: three evaluators 4, 5, 7 round to two decimals, not to one', () => {
  // The server sends ROUND(16/3, 2) = 5.33. One decimal would cost money:
  // 5.3 × coef × weight is not 5.33 × coef × weight.
  const cell = { c_level_only: true, c_level_score: 5.33, c_level_count: 3 };
  assert.equal(getCriterionFinalScore(cell), 5.33);
  assert.equal(formatScoreCompact(5.33), '5.33');
  // The level coefficient is picked by round(), so 5.33 and 5.3 agree there.
  assert.equal(Math.max(0, Math.min(10, Math.round(5.33))), 5);
});

test('item 2: the hand-computed index of an averaged cell', () => {
  // Criterion 1, weight 5.00, live level curve; two C-level evaluators, 4 and 8.
  const weight = 5.0;
  const curve = { 1: 0.30, 2: 0.40, 3: 0.60, 4: 0.70, 5: 1.00, 6: 1.20, 7: 1.60, 8: 2.80, 9: 4.00, 10: 6.00 };
  const weighted = (raw) => raw * curve[Math.max(0, Math.min(10, Math.round(raw)))] * weight;
  assert.equal(weighted(6), 36);        // averaged: 6 × 1.20 × 5.00
  assert.equal(weighted(4), 14);        // old behaviour if the 4 was written last
  assert.equal(weighted(8), 112);       // old behaviour if the 8 was written last
  // The whole point: the two old answers are 8× apart on this one cell.
  assert.ok(weighted(8) / weighted(4) === 8);
});

// ── item 2: the tooltip carries the count ──────────────────────────────────

test('item 2: the tooltip on a C-level cell says the score is a mean and of how many', () => {
  const tip = formatCorrectionTooltip({ c_level_only: true, c_level_score: 6, c_level_count: 2 });
  assert.match(tip, /C-level: 6 \(среднее по 2 оценкам\)/);
});

test('item 2: the manager-path tooltip is unchanged', () => {
  const tip = formatCorrectionTooltip({
    c_level_only: false, manager_score: 9, mid_level_correction: 5, c_level_correction: 4,
  });
  assert.equal(tip, 'Менеджер: 9, Mid-level: 5, C-level: 4, Итого: 6.0');
});

// ── item 3: corrections on a C-level criterion, surfaced not resolved ──────

test('item 3: a c_level correction still does not enter a c_level_only cell', () => {
  const cell = { c_level_only: true, c_level_score: 6, c_level_count: 2, c_level_correction: 3 };
  // Unchanged behaviour: the mean is the cell, the correction is ignored.
  assert.equal(getCriterionFinalScore(cell), 6);
  // …and the same in the close, by the same branch.
  assert.match(closeCompute(), /if \(crit\.c_level_only\) \{\s*\n\s*return crit\.c_level_score/);
});

test('item 3: the tooltip says the stored correction is not counted', () => {
  const tip = formatCorrectionTooltip({ c_level_only: true, c_level_score: 6, c_level_count: 2, c_level_correction: 3 });
  assert.match(tip, /Коррекция C-level: 3 \(не входит в расчёт C-level критерия\)/);
});

test('item 3: the correction route still accepts any criterion id, including c_level_only', () => {
  // Not a change — the evidence for the question put to the owner. The route
  // validates the project dimension and the range, and nothing about
  // c_level_only, so a correction on criterion 1 or 10 is stored and then
  // never read.
  const decide = nodeCode(loadFrom(OUT_DEFERRED, 'score-correction.json'), 'Decide Level');
  assert.match(decide, /CRITERIA_NOT_APPLICABLE/);
  assert.doesNotMatch(decide, /c_level_only/);
  assert.match(decide, /ON CONFLICT \(subject_id, criteria_id, correction_level, period_id\)/);
});

// ── the C-level channel and the upward channel now have the same shape ─────

test('the upward channel is unchanged and still the model this copies', () => {
  const sql = matrixQuery();
  assert.match(sql, /AVG\(es\.score_value\) as avg_subordinate_score/);
  assert.match(sql, /COUNT\(es\.score_value\) as subordinate_count/);
  assert.match(sql, /'subordinate_avg_score', \(/);
  assert.match(sql, /'subordinate_count', \(/);
});
