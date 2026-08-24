/**
 * evaluationStartGate.test.js
 *
 * The two-gate period lifecycle and coefficient privacy (brief 2026-08-22,
 * D-0822-1 / D-0822-2). Three layers:
 *  1. Static assertions on the generated manage-periods workflow: the new
 *     start-evaluation route, its guard, its preconditions and its
 *     irreversibility (no route clears evaluation_started_at).
 *  2. Static assertions that the campaign surface keys on "active AND started"
 *     while admin/reporting reads stay keyed on "active".
 *  3. Behavioral: the self-review Build node is executed with fixture rows
 *     (mocked n8n $ / $input) and the weighted_score it computes is compared
 *     against an independent implementation of formula #2 (HANDOVER §4).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import { readFileSync, mkdtempSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const H1_SCRIPT = join(REPO_ROOT, "scripts", "build_route_guard_workflows.py");
const AUTH_SCRIPT = join(REPO_ROOT, "scripts", "build_auth_workflows.py");
const H1_DIR = mkdtempSync(join(tmpdir(), "start-gate-h1-"));
const AUTH_DIR = mkdtempSync(join(tmpdir(), "start-gate-auth-"));

execSync(`python3 "${H1_SCRIPT}" --output-directory "${H1_DIR}" 2>&1`, { cwd: REPO_ROOT });
execSync(`python3 "${AUTH_SCRIPT}" --output-directory "${AUTH_DIR}" 2>&1`, { cwd: REPO_ROOT });

const loadH1 = (f) => JSON.parse(readFileSync(join(H1_DIR, f), "utf8"));
const loadAuth = (f) => JSON.parse(readFileSync(join(AUTH_DIR, f), "utf8"));
const allJs = (wf) => (wf.nodes || []).map((n) => n.parameters?.jsCode || "").join("\n");
const jsOf = (wf, name) => {
  const n = (wf.nodes || []).find((x) => x.name === name);
  assert.ok(n, `node "${name}" must exist`);
  return n.parameters?.jsCode || "";
};

const periods = loadH1("manage-periods.json");

// ── 1. The second gate exists and is admin-only ──────────────────────────────

test("manage-periods serves POST api/periods/start-evaluation", () => {
  const hooks = (periods.nodes || [])
    .filter((n) => n.type === "n8n-nodes-base.webhook")
    .map((n) => `${n.parameters.httpMethod} ${n.parameters.path}`);
  assert.ok(hooks.includes("POST api/periods/start-evaluation"), hooks.join(", "));
});

test("the start route is admin-only", () => {
  assert.ok(jsOf(periods, "Prepare Guard Input START").includes('required_roles: ["admin"]'));
});

test("the start route reaches a respond node through its own chain", () => {
  const chain = [
    "Webhook START", "Prepare Guard Input START", "Run Auth Guard START",
    "Validate Period Start", "Load Start Target", "Build Start SQL",
    "Execute Start", "Format Start Response", "Respond START",
  ];
  for (let i = 0; i < chain.length - 1; i += 1) {
    const targets = (periods.connections[chain[i]]?.main?.[0] || []).map((t) => t.node);
    assert.deepEqual(targets, [chain[i + 1]], `${chain[i]} -> ${chain[i + 1]}`);
  }
});

// ── 2. Preconditions ─────────────────────────────────────────────────────────

test("start refuses containers, annual periods, closed and non-active periods", () => {
  const js = jsOf(periods, "Build Start SQL");
  assert.ok(js.includes("CONTAINER_NOT_STARTABLE"), "container");
  assert.ok(js.includes("ANNUAL_PERIOD_NOT_STARTABLE"), "annual");
  assert.ok(js.includes("PERIOD_CLOSED"), "closed");
  assert.ok(js.includes("PERIOD_NOT_ACTIVE"), "not active");
  assert.ok(js.includes("PERIOD_NOT_FOUND"), "not found");
});

test("a second start is an explicit no-op, not an error and not a write", () => {
  const js = jsOf(periods, "Build Start SQL");
  assert.ok(js.includes("already_started: true"));
  assert.ok(js.includes("http_status: 200"));
  // The already-started branch returns before any `ok: true` SQL is built.
  const idx = js.indexOf("already_started: true");
  const sqlIdx = js.indexOf("UPDATE performance_db.evaluation_periods");
  assert.ok(idx > 0 && sqlIdx > idx, "already-started must return before the UPDATE is built");
});

test("the start UPDATE re-asserts every precondition inline", () => {
  const js = jsOf(periods, "Build Start SQL");
  assert.ok(js.includes("AND status = 'active'"));
  assert.ok(js.includes("AND is_active = true"));
  assert.ok(js.includes("AND period_type != 'annual'"));
  assert.ok(js.includes("AND evaluation_started_at IS NULL"));
  assert.ok(js.includes("c.parent_period_id = ${periodId}"));
  assert.ok(js.includes("FOR UPDATE"));
  assert.ok(jsOf(periods, "Format Start Response").includes("START_CONFLICT"),
    "a lost race must answer 409, not silently succeed");
});

test("activation does not start the evaluation", () => {
  const js = jsOf(periods, "Build Activation SQL");
  assert.equal(js.includes("evaluation_started_at ="), false,
    "the activate route must never write the start mark");
});

test("no route clears evaluation_started_at — the mark is irreversible", () => {
  const js = allJs(periods);
  assert.equal(/evaluation_started_at\s*=\s*NULL/i.test(js), false);
  const writes = js.match(/evaluation_started_at\s*=\s*[^\s]+/g) || [];
  assert.deepEqual(writes, ["evaluation_started_at = now(),"],
    `the only write must be the start itself, found: ${writes.join(" | ")}`);
});

test("GET api/periods exposes the third state", () => {
  const js = jsOf(periods, "Build Periods Query");
  assert.ok(js.includes("evaluation_started_at"));
  assert.ok(js.includes("(evaluation_started_at IS NOT NULL) AS evaluation_started"));
});

// ── 3. The campaign surface keys on started ──────────────────────────────────

const CAMPAIGN_SURFACE = [
  "submit-evaluation.json",
  "self-review-submit.json",
  "update-evaluation.json",
  "check-self-review.json",
  "check-evaluated.json",
  "get-my-manager.json",
];

test("every campaign-surface workflow requires evaluation_started_at", () => {
  for (const file of CAMPAIGN_SURFACE) {
    const js = allJs(loadH1(file));
    assert.ok(
      js.includes("evaluation_started_at IS NOT NULL"),
      `${file}: campaign period must be active AND started`
    );
  }
});

test("the two submit routes answer PERIOD_NOT_STARTED, not a scope error", () => {
  for (const file of ["submit-evaluation.json", "self-review-submit.json", "update-evaluation.json"]) {
    const js = allJs(loadH1(file));
    assert.ok(js.includes("PERIOD_NOT_STARTED"), file);
  }
});

test("the employees route keys campaign_active on started and reports preparation", () => {
  const js = allJs(loadAuth("protected-employees.json"));
  assert.ok(js.includes("evaluation_started_at IS NOT NULL"),
    "active_period must require the start mark");
  assert.ok(js.includes("period_in_preparation"),
    "the client must be able to tell 'no period' from 'period in preparation'");
  // actor_is_in_scope stays computed from current_period, which still includes
  // an active-but-unstarted period — scope is a fact about the period, not the
  // campaign, and the out-of-scope notice must keep working in the window.
  assert.ok(js.includes("actor_is_in_scope"));
});

test("admin and reporting reads stay keyed on active, not on started", () => {
  for (const file of ["hr-evaluation-status.json", "admin-users-data.json", "my-profile.json",
                      "evaluation-history.json", "evaluation-details.json", "save-user.json"]) {
    const js = allJs(loadH1(file));
    assert.equal(js.includes("evaluation_started_at"), false,
      `${file}: admin/reporting reads must not key on the start gate`);
  }
});

test("the classification freeze is GONE — classification stays editable during a campaign (D-0822-3)", () => {
  const js = allJs(loadH1("save-user.json"));
  assert.equal(js.includes("CLASSIFICATION_FROZEN"), false,
    "save-user: the classification 409 was removed by D-0822-3");
  assert.equal(js.includes("period_has_any_evaluation"), false,
    "save-user: the global any-evaluation freeze probe must be gone with it");
});

// ── 4. Coefficient privacy ───────────────────────────────────────────────────

test("GET api/score-coefficients is admin-only", () => {
  const wf = loadH1("score-coefficients.json");
  assert.ok(jsOf(wf, "Prepare Guard Input").includes('required_roles: ["admin"]'));
});

test("GET api/criteria strips weight for every non-admin role", () => {
  const js = jsOf(loadH1("criteria.json"), "Format Response");
  assert.ok(js.includes("const canSeeWeight = role === 'admin';"));
  assert.ok(js.includes("delete criterion.weight"));
  // the existing c_level_only level-text stripping must stay intact
  assert.ok(js.includes("canSeeCLevelTexts"));
  assert.ok(js.includes("levelTextFields.forEach"));
});

// ── 5. Behavioral: weighted_score is formula #2, computed server-side ────────

/** Independent implementation of formula #2 (HANDOVER §4). */
function formulaTwo(grades, catalogue, gradeCoefficient) {
  let weightedSum = 0;
  let totalWeight = 0;
  for (const [id, score] of Object.entries(grades)) {
    const c = catalogue.find((x) => x.id === Number(id));
    const weight = c ? Number(c.weight) : 1.0;
    const level = Math.max(0, Math.min(10, Math.round(score)));
    const coef = c ? (c.levels[level] ?? 1.0) : 1.0;
    weightedSum += score * coef * weight;
    totalWeight += weight;
  }
  return Number(((weightedSum / totalWeight) * gradeCoefficient).toFixed(2));
}

function runSelfReviewBuild({ grades, catalogue, gradeCoefficient, started = true, duplicate = false }) {
  const js = jsOf(loadH1("self-review-submit.json"), "Build Self Review Insert");
  const check = {
    period_id: 2,
    period_started: started,
    is_duplicate: duplicate,
    grade_coefficient: gradeCoefficient === null ? null : String(gradeCoefficient),
    coefficients: JSON.stringify(
      catalogue.map((c) => ({
        id: c.id,
        weight: String(c.weight),
        score_coefficients: Object.fromEntries(
          Object.entries(c.levels).map(([k, v]) => [String(k), String(v)])
        ),
      }))
    ),
  };
  const prev = { actor_id: 7, final_score: 5 };
  const guard = { request: { body: { grades, comments: {}, general_comment: "", weighted_score: 999 } } };
  const $ = (name) => ({ first: () => ({ json: name === "Validate Self Review" ? prev : guard }) });
  const $input = { first: () => ({ json: check }) };
  return new Function("$", "$input", js)($, $input);
}

const CATALOGUE = [
  { id: 3, weight: 3.0, levels: { 1: 0.4, 2: 0.5, 3: 0.6, 4: 0.7, 5: 0.9, 6: 1.1, 7: 1.3, 8: 1.6, 9: 2.0, 10: 2.3 } },
  { id: 4, weight: 1.5, levels: { 1: 0.4, 2: 0.6, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.5, 9: 2.0, 10: 2.5 } },
  { id: 12, weight: 1.0, levels: { 1: 0.5, 2: 0.7, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.3, 8: 1.5, 9: 1.8, 10: 2.0 } },
];

test("weighted_score equals formula #2 for two different grade coefficients", () => {
  const grades = { 3: 8, 4: 6, 12: 9 };
  for (const gc of [0.6, 2.2]) {
    const out = runSelfReviewBuild({ grades, catalogue: CATALOGUE, gradeCoefficient: gc });
    assert.equal(out.json.weighted_score, formulaTwo(grades, CATALOGUE, gc), `grade coefficient ${gc}`);
    assert.ok(
      out.json.sql.includes(`${out.json.weighted_score},`),
      "the computed value must be the one written into the INSERT"
    );
  }
});

test("the client-supplied weighted_score has no effect", () => {
  const grades = { 3: 5 };
  const out = runSelfReviewBuild({ grades, catalogue: CATALOGUE, gradeCoefficient: 1.1 });
  assert.notEqual(out.json.weighted_score, 999);
  assert.equal(out.json.weighted_score, formulaTwo(grades, CATALOGUE, 1.1));
});

test("a subject with no grade coefficient is refused, never defaulted to 1.0", () => {
  const out = runSelfReviewBuild({ grades: { 3: 5 }, catalogue: CATALOGUE, gradeCoefficient: null });
  assert.equal(out.json.http_status, 422);
  assert.equal(out.json.body.error, "NO_GRADE_COEFFICIENT");
});

test("an unstarted period refuses the self-review before any SQL is built", () => {
  const out = runSelfReviewBuild({
    grades: { 3: 5 }, catalogue: CATALOGUE, gradeCoefficient: 1.1, started: false,
  });
  assert.equal(out.json.http_status, 409);
  assert.equal(out.json.body.error, "PERIOD_NOT_STARTED");
  assert.equal(out.json.sql, undefined);
});

test("a duplicate self-review still 409s ahead of the computation", () => {
  const out = runSelfReviewBuild({
    grades: { 3: 5 }, catalogue: CATALOGUE, gradeCoefficient: 1.1, duplicate: true,
  });
  assert.equal(out.json.http_status, 409);
  assert.equal(out.json.body.error, "DUPLICATE_SELF_REVIEW");
});
