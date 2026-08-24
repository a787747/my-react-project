import test from "node:test";
import assert from "node:assert/strict";
import {
  getCriterionFinalScore,
  canReceiveCLevel,
  cLevelWritePath,
  formatCorrectionTooltip,
  buildSharedCriteriaGroups,
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

// BUG-051: the matrix header must be the union of every row's criteria, not
// employees[0]'s — the server emits only the criteria applicable to each
// subject (D-0822-3), so a general subject carries no project criteria.
const critAll = (id, extra = {}) => ({
  criteria_id: id,
  criteria_title: `crit ${id}`,
  target_audience: "all",
  selfassesment: false,
  c_level_only: false,
  ...extra,
});

const generalRow = {
  id: 1,
  criteria: [
    critAll(3, { selfassesment: true }),
    critAll(14),
    critAll(2, { target_audience: "managers_only" }),
    critAll(1, { c_level_only: true }),
  ],
};
const projectRow = {
  id: 2,
  criteria: [
    critAll(3, { selfassesment: true }),
    critAll(14),
    critAll(8, { target_audience: "project_participants" }),
    critAll(13, { target_audience: "project_participants" }),
    critAll(2, { target_audience: "managers_only" }),
    critAll(1, { c_level_only: true }),
  ],
};

test("shared header groups are the union across all rows (general row first)", () => {
  const groups = buildSharedCriteriaGroups([generalRow, projectRow]);
  assert.deepEqual(groups.self.map(c => c.criteria_id), [3]);
  assert.deepEqual(groups.general.map(c => c.criteria_id), [14]);
  assert.deepEqual(groups.project.map(c => c.criteria_id), [8, 13]);
  assert.deepEqual(groups.management.map(c => c.criteria_id), [2]);
  assert.deepEqual(groups.c_level.map(c => c.criteria_id), [1]);
});

test("shared header groups keep first-seen order and dedupe by criteria_id", () => {
  const groups = buildSharedCriteriaGroups([projectRow, generalRow, projectRow]);
  assert.deepEqual(groups.project.map(c => c.criteria_id), [8, 13]);
  const total =
    groups.self.length + groups.general.length + groups.project.length +
    groups.management.length + groups.c_level.length;
  assert.equal(total, 6);
});

test("shared header groups tolerate empty input and rows without criteria", () => {
  const empty = buildSharedCriteriaGroups([]);
  assert.deepEqual(empty, { self: [], general: [], project: [], management: [], c_level: [] });
  const partial = buildSharedCriteriaGroups([{ id: 9 }, generalRow]);
  assert.equal(partial.general.length, 1);
});
