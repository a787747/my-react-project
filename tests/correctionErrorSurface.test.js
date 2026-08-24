/**
 * correctionErrorSurface.test.js
 *
 * Browser walkthrough 2026-08-24: a score-correction refusal (422
 * CRITERIA_NOT_APPLICABLE, 409) reached the admin as the hardcoded alert
 * «Ошибка при сохранении корректировки» while the server had sent a readable
 * Russian reason («Критерий 8 — проектный, а сотрудник сейчас не участник
 * проекта»). The fix threads the server message through both correction
 * surfaces; these assertions pin the plumbing.
 *
 * React sources, so the assertions are made against the source text — the
 * same approach moneyScreenGuards.test.js uses.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');

const modal = read('src/components/admin/ScoreDetailModal.jsx');
const matrixHook = read('src/hooks/useEvaluationsMatrix.js');
const teamMatrix = read('src/pages/ManagerSubordinatesMatrix.jsx');

test('ScoreDetailModal alerts the thrown message, not a hardcoded literal', () => {
  assert.ok(
    !modal.includes("alert('Ошибка при сохранении корректировки')"),
    'the alert must not discard the error it caught',
  );
  assert.match(
    modal,
    /alert\(error\?\.message \|\| 'Ошибка при сохранении корректировки'\)/,
    'the alert falls back to the generic text only when the error carries no message',
  );
});

test('useEvaluationsMatrix.submitScoreCorrection surfaces the server message', () => {
  assert.match(
    matrixHook,
    /error:\s*error\.userMessage\s*\|\|\s*'Ошибка при сохранении корректировки'/,
    'the c_level correction path must return apiClient userMessage (server 409/422 text)',
  );
});

test('mid_level correction path keeps preserving the server message', () => {
  assert.match(
    teamMatrix,
    /err\.response\?\.data\?\.message \|\| 'Ошибка при сохранении корректировки'/,
    'ManagerSubordinatesMatrix already threaded the server message — keep it',
  );
});
