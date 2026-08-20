import test from "node:test";
import assert from "node:assert/strict";
import {
  getCriterionFinalScore,
  canReceiveCLevel,
  cLevelWritePath,
  formatCorrectionTooltip,
} from "../src/utils/matrixUtils.js";

const activePeriod = { id: 2, name: "H1-2026", status: "active", is_active: true };

test("final cell averages manager + mid_level + c_level when all present", () => {
  const score = getCriterionFinalScore({
    manager_score: 6,
    mid_level_correction: 8,
    c_level_correction: 10,
  });
  assert.equal(score, 8);
});

test("final cell averages manager + mid_level when c_level is absent", () => {
  const score = getCriterionFinalScore({
    manager_score: 6,
    mid_level_correction: 8,
  });
  assert.equal(score, 7);
});

test("final cell ignores mid_level when manager is missing", () => {
  assert.equal(
    getCriterionFinalScore({
      mid_level_correction: 8,
      c_level_correction: 10,
    }),
    null
  );
});

test("c_level_only criteria use c_level_score as-is", () => {
  assert.equal(
    getCriterionFinalScore({
      c_level_only: true,
      c_level_score: 4,
      manager_score: 9,
    }),
    4
  );
});

test("stars only on in-scope evaluable non-c-level subjects of the active period", () => {
  const subject = {
    is_in_scope: true,
    can_be_evaluated: true,
    role: "employee",
  };
  assert.equal(canReceiveCLevel(subject, activePeriod), true);
  assert.equal(canReceiveCLevel({ ...subject, role: "c_level" }, activePeriod), false);
  assert.equal(canReceiveCLevel({ ...subject, can_be_evaluated: false }, activePeriod), false);
  assert.equal(canReceiveCLevel({ ...subject, is_in_scope: false }, activePeriod), false);
  assert.equal(
    canReceiveCLevel(subject, { ...activePeriod, status: "draft", is_active: false }),
    false
  );
});

test("existing actor row uses update-evaluation, otherwise submit", () => {
  assert.equal(cLevelWritePath(44), "update");
  assert.equal(cLevelWritePath(null), "submit");
});

test("correction tooltip names mid_level in the displayed average", () => {
  const tip = formatCorrectionTooltip({
    manager_score: 6,
    mid_level_correction: 8,
    c_level_correction: 10,
  });
  assert.match(tip, /Mid-level: 8/);
  assert.match(tip, /Итого: 8.0/);
});
