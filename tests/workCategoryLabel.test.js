import test from 'node:test';
import assert from 'node:assert/strict';
import { getWorkCategoryLabel } from '../src/config/constants.js';

test('maps work_category enum to Russian labels', () => {
  assert.equal(getWorkCategoryLabel('general'), 'общие');
  assert.equal(getWorkCategoryLabel('project'), 'проектные');
  assert.equal(getWorkCategoryLabel('PROJECT'), 'проектные');
  assert.equal(getWorkCategoryLabel('tender'), 'tender');
  assert.equal(getWorkCategoryLabel(''), '');
});
