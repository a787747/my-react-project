/**
 * EVALUATION_FORM_READABILITY — descriptions are not clamped on the
 * evaluator forms; an untouched criterion is a dash, not a 1; submit
 * stays blocked until every visible criterion has been touched.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const read = (p) => readFileSync(join(REPO_ROOT, p), "utf8");

const slider = read("src/components/CriterionSlider.jsx");
const selfModal = read("src/components/self-review/SelfReviewModal.jsx");
const evalModal = read("src/components/EvaluationModal.jsx");
const upward = read("src/pages/ManagerEvaluation.jsx");
const selfHook = read("src/hooks/useSelfReview.js");
const clevel = read("src/components/admin/CLevelEvaluationModal.jsx");
const toggle = read("src/components/CriterionScaleToggle.jsx");
const submitBuilder = read("scripts/build_route_guard_workflows.py");
const catalogue = read("docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md");

const CRIT3_DESCRIPTION = "Оценивается: качество работы и соблюдение стандартов и требований";

test("criterion 3 catalogue text is unchanged in the dated snapshot this brief quotes against", () => {
  assert.match(catalogue, /### Criterion 3 «Личная результативность и эффективность»/);
  assert.match(catalogue, new RegExp(CRIT3_DESCRIPTION.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});

test("no form file rewords criterion 3 — they render the payload description as-is", () => {
  for (const [name, src] of [
    ["CriterionSlider", slider],
    ["SelfReviewModal", selfModal],
    ["CLevelEvaluationModal", clevel],
  ]) {
    assert.doesNotMatch(src, /качество работы и соблюдение…/, name);
    assert.doesNotMatch(src, /line-clamp-2/, `${name} must not clamp the description`);
  }
  assert.match(slider, /\{criterion\.description\}/);
  assert.match(selfModal, /\{criterion\.description\}/);
  assert.match(clevel, /\{criterion\.criteria_description\}/);
});

test("untouched slider: dash in the corner, zone only after a touch, thumb may rest at 1", () => {
  assert.match(slider, /isCriterionTouched\(value\)/);
  assert.match(slider, /isSelected \? currentScore : '—'/);
  assert.match(slider, /isSelected \? getScoreZone/);
  assert.match(slider, /currentScore \?\? 1/);
  assert.match(selfModal, /isSelected \? currentScore : '—'/);
  assert.match(selfModal, /currentScore \?\? 1/);
  assert.match(selfModal, /isSelected \? getScoreZone/);
});

test("submit stays blocked while any visible criterion is untouched", () => {
  assert.match(evalModal, /disabled=\{submitting \|\| !allCriteriaEvaluated\}/);
  assert.match(evalModal, /untouchedCriterionIds\(evaluations, visibleCriteria\)/);
  assert.match(evalModal, /gradesPayloadFromState\(evaluations, visibleCriteria\)/);
  assert.match(selfModal, /disabled=\{submitting \|\| !allCriteriaEvaluated\}/);
  assert.match(selfHook, /untouchedCriterionIds\(grades, targetCriteria\)/);
  assert.match(selfHook, /gradesPayloadFromState\(grades, targetCriteria\)/);
  assert.match(upward, /untouchedCriterionIds\(evaluations, criteria\)/);
  assert.match(upward, /gradesPayloadFromState\(evaluations, criteria\)/);
  assert.match(upward, /disabled=\{!isFormValid \|\| submitting\}/);
  assert.match(clevel, /disabled=\{submitting \|\| !allCriteriaEvaluated\}/);
  assert.match(clevel, /untouchedCriterionIds\(grades, visibleCriteria\)/);
  assert.match(clevel, /gradesPayloadFromState\(grades, visibleCriteria\)/);
});

test("C-level modal does not invent a 5 and shows a dash until touched", () => {
  assert.doesNotMatch(clevel, /actor_c_level_score\s*\|\|\s*5/);
  assert.match(clevel, /isCriterionTouched\(raw\)/);
  assert.match(clevel, /isSelected \? currentScore : '—'/);
  assert.match(clevel, /currentScore \?\? 1/);
  assert.match(clevel, /isSelected \? getScoreZone/);
});

test("the ten-level scale opens from the form without cluttering it", () => {
  assert.match(toggle, /Показать шкалу \(1–10\)/);
  assert.match(toggle, /<CriteriaReadout criterion=\{criterion\} showDescription=\{false\} \/>/);
  assert.match(toggle, /useState\(false\)/);
  assert.match(slider, /<CriterionScaleToggle criterion=\{criterion\} \/>/);
  assert.match(selfModal, /<CriterionScaleToggle criterion=\{criterion\} \/>/);
});

test("submit-evaluation and self-review-submit write only the keys in grades — they never default a missing criterion to 1", () => {
  const entries = submitBuilder.match(/Object\.entries\(grades\)/g) || [];
  assert.ok(entries.length >= 2, `expected grades Object.entries on both write paths, found ${entries.length}`);
  assert.match(submitBuilder, /error: 'NO_GRADES'/);
  assert.doesNotMatch(submitBuilder, /scoreValue\s*=\s*1\b/);
  assert.doesNotMatch(submitBuilder, /parseInt\(sv, 10\)\s*\|\|\s*1/);
});

test("additive submit writes only the submitted score_rows — a missing id stays missing", () => {
  const additive = submitBuilder.slice(
    submitBuilder.indexOf("mode: 'additive'"),
    submitBuilder.indexOf("mode: 'insert'")
  );
  assert.match(additive, /INSERT INTO performance_db\.evaluation_scores/);
  assert.match(additive, /CROSS JOIN score_rows sr/);
  assert.doesNotMatch(additive, /COALESCE\(.*1\)/);
  assert.doesNotMatch(additive, /generate_series/);
});
