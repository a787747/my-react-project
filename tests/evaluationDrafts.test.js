import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clearEvaluationDraft,
  getEvaluationDraftKey,
  loadEvaluationDraft,
  saveEvaluationDraft,
} from '../src/utils/evaluationDrafts.js';

const createStorage = () => {
  const data = new Map();
  return {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
    data,
  };
};

test('builds a draft key only for complete identities', () => {
  assert.equal(getEvaluationDraftKey(10, 20), 'epe:evaluation-draft:10:20');
  assert.equal(getEvaluationDraftKey(null, 20), null);
  assert.equal(getEvaluationDraftKey(10, undefined), null);
});

test('self-review and upward keys do not collide with a manager-to-subordinate key', () => {
  const managerId = 1;
  const employeeId = 3;
  assert.equal(getEvaluationDraftKey(managerId, employeeId), 'epe:evaluation-draft:1:3');
  assert.equal(getEvaluationDraftKey(employeeId, employeeId), 'epe:evaluation-draft:3:3');
  assert.equal(getEvaluationDraftKey(employeeId, managerId), 'epe:evaluation-draft:3:1');
});

test('round-trips and clears an evaluation draft', () => {
  const storage = createStorage();
  const key = getEvaluationDraftKey(10, 20);

  saveEvaluationDraft(key, { 1: 8 }, { 1: 'Good work' }, storage);
  assert.deepEqual(loadEvaluationDraft(key, storage), {
    evaluations: { 1: 8 },
    comments: { 1: 'Good work' },
    savedAt: JSON.parse(storage.getItem(key)).savedAt,
  });

  clearEvaluationDraft(key, storage);
  assert.equal(loadEvaluationDraft(key, storage), null);
});

test('removes malformed and expired drafts', () => {
  const storage = createStorage();
  const key = getEvaluationDraftKey(10, 20);

  storage.setItem(key, '{not-json');
  assert.equal(loadEvaluationDraft(key, storage), null);
  assert.equal(storage.getItem(key), null);

  storage.setItem(key, JSON.stringify({
    version: 1,
    savedAt: '2020-01-01T00:00:00.000Z',
    evaluations: { 1: 5 },
    comments: {},
  }));
  assert.equal(loadEvaluationDraft(key, storage), null);
  assert.equal(storage.getItem(key), null);
});
