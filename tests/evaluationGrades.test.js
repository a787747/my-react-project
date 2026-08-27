/**
 * Untouched criteria must not become a 1 in the submit payload.
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  gradesPayloadFromState,
  isCriterionTouched,
  untouchedCriterionIds,
} from "../src/utils/evaluationGrades.js";

const visible = [{ id: 3 }, { id: 4 }, { id: 12 }];

test("an empty form yields an empty grades object — no invented 1", () => {
  assert.deepEqual(gradesPayloadFromState({}, visible), {});
  assert.deepEqual(untouchedCriterionIds({}, visible), [3, 4, 12]);
});

test("a partial form omits the untouched key rather than sending 1", () => {
  const state = { 3: 7, 4: 6 };
  assert.deepEqual(gradesPayloadFromState(state, visible), {
    "3": 7,
    "4": 6,
  });
  assert.ok(!Object.prototype.hasOwnProperty.call(
    gradesPayloadFromState(state, visible),
    "12"
  ));
  assert.deepEqual(untouchedCriterionIds(state, visible), [12]);
});

test("null / empty-string stay untouched; only a real number is a choice", () => {
  assert.equal(isCriterionTouched(undefined), false);
  assert.equal(isCriterionTouched(null), false);
  assert.equal(isCriterionTouched(""), false);
  assert.equal(isCriterionTouched(1), true);
  assert.equal(isCriterionTouched("1"), true);
  assert.deepEqual(
    gradesPayloadFromState({ 3: null, 4: "", 12: 5 }, visible),
    { "12": 5 }
  );
});
