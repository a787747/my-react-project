/**
 * periodsHierarchy.test.js
 *
 * Containers, rename, reparent, close-time result persistence, annual roll-up
 * (brief 2026-08-21). Two layers:
 *  1. Static assertions on the generated manage-periods workflow: routes,
 *     guards, container-activation refusal, immutability of period_results,
 *     no-zero-fill roll-up SQL.
 *  2. Behavioral: the close-compute Code node is executed with fixture rows
 *     (mocked n8n $ / $input) and the SQL it emits is inspected — a no-data
 *     participant must produce NULLs, never zeros; formulas must replicate
 *     the client pipeline (matrixUtils / useFinalScoresMatrix).
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
const SCRIPT = join(REPO_ROOT, "scripts", "build_route_guard_workflows.py");
const OUT_DIR = mkdtempSync(join(tmpdir(), "periods-hier-test-"));

execSync(`python3 "${SCRIPT}" --output-directory "${OUT_DIR}" 2>&1`, { cwd: REPO_ROOT });

const wf = JSON.parse(readFileSync(join(OUT_DIR, "manage-periods.json"), "utf8"));

function nodeByName(name) {
  const n = (wf.nodes || []).find((x) => x.name === name);
  assert.ok(n, `node "${name}" must exist`);
  return n;
}

function jsOf(name) {
  return nodeByName(name).parameters?.jsCode || "";
}

function webhookPaths() {
  return (wf.nodes || [])
    .filter((n) => n.type === "n8n-nodes-base.webhook")
    .map((n) => ({ method: n.parameters?.httpMethod || "GET", path: n.parameters?.path }));
}

// ── Routes ────────────────────────────────────────────────────────────────

test("manage-periods exposes rename, reparent, close and annual-rollup routes", () => {
  const paths = webhookPaths();
  for (const [method, path] of [
    ["POST", "api/periods/rename"],
    ["POST", "api/periods/reparent"],
    ["POST", "api/periods/close"],
    ["GET", "api/periods/annual-rollup"],
  ]) {
    assert.ok(
      paths.some((w) => w.method === method && w.path === path),
      `missing ${method} ${path}`
    );
  }
});

// ── Guards ────────────────────────────────────────────────────────────────

test("write routes are admin-only; rollup is admin + c_level without hr", () => {
  for (const name of [
    "Prepare Guard Input CREATE",
    "Prepare Guard Input ACTIVATE",
    "Prepare Guard Input RENAME",
    "Prepare Guard Input REPARENT",
    "Prepare Guard Input CLOSE",
  ]) {
    const js = jsOf(name);
    assert.ok(js.includes('required_roles: ["admin"]'), `${name}: must be admin-only`);
  }
  const rollup = jsOf("Prepare Guard Input ROLLUP");
  assert.ok(
    rollup.includes('required_roles: ["admin", "c_level"]'),
    "ROLLUP guard must be admin + c_level"
  );
  assert.ok(!rollup.includes('"hr"'), "ROLLUP guard must not include hr (D-0820-11)");
});

// ── Container activation refusal (D-0821-1) ──────────────────────────────

test("activation refuses containers with 422 and re-asserts in the UPDATE", () => {
  const js = jsOf("Build Activation SQL");
  assert.ok(js.includes("CONTAINER_NOT_ACTIVATABLE"), "must carry the 422 error code");
  assert.match(js, /http_status: 422[\s\S]{0,200}CONTAINER_NOT_ACTIVATABLE/, "code must ride a 422");
  assert.ok(
    js.includes("parent_period_id = ${periodId}"),
    "UPDATE must re-assert the target has no children"
  );
  // deactivation must be gated on the target being activatable (no orphan deactivate)
  assert.ok(
    js.includes("EXISTS (SELECT 1 FROM activatable)"),
    "deactivation must not fire when the target cannot be activated"
  );
});

// ── Close: leaf-only, active-only, atomic, idempotent ─────────────────────

test("close refuses containers and non-active periods; second close is a zero-write", () => {
  const build = jsOf("Build Close Dataset Query");
  assert.ok(build.includes("CONTAINER_NOT_CLOSABLE"), "containers must not close");
  assert.ok(build.includes("PERIOD_NOT_ACTIVE"), "only the active period closes");
  assert.ok(build.includes("already_closed"), "second close must answer idempotently");
  const compute = jsOf("Compute Close Results");
  assert.ok(
    compute.includes("NOT EXISTS (SELECT 1 FROM performance_db.period_results"),
    "insert must be gated on no existing results (second close changes zero rows)"
  );
  assert.ok(
    compute.includes("status = 'active' AND is_active = true"),
    "close write must re-assert the period is still active"
  );
  assert.ok(
    compute.includes("FOR UPDATE"),
    "close must lock the period row"
  );
});

test("period_results is insert-only across every generated workflow", () => {
  const files = execSync(`ls "${OUT_DIR}"`).toString().trim().split("\n");
  for (const f of files) {
    const w = JSON.parse(readFileSync(join(OUT_DIR, f), "utf8"));
    const allJs = (w.nodes || []).map((n) => n.parameters?.jsCode || "").join("\n");
    assert.ok(
      !/UPDATE\s+performance_db\.period_results/i.test(allJs),
      `${f}: period_results must never be UPDATEd`
    );
    assert.ok(
      !/DELETE\s+FROM\s+performance_db\.period_results/i.test(allJs),
      `${f}: period_results must never be DELETEd`
    );
  }
});

// ── Close formulas replicate the client pipeline ──────────────────────────

test("close compute replicates matrix final cell and money-screen index formulas", () => {
  const js = jsOf("Compute Close Results");
  // matrixUtils.getCriterionFinalScore: mean(manager, mid?, c_level?)
  assert.ok(js.includes("scores.push(Number(crit.mid_level_correction))"), "mid_level counts (D-0820-12)");
  assert.ok(js.includes("scores.push(Number(crit.c_level_correction))"), "c_level correction counts");
  // useFinalScoresMatrix.calculateCriterionScore: score × coef(round(clamp)) × weight
  assert.ok(js.includes("Math.max(0, Math.min(10, Math.round(raw)))"), "coefficient level = round(clamp(score))");
  assert.ok(js.includes("raw * coefficient * weight"), "weighted term shape");
  // formula #3: weighted sum WITHOUT dividing by sum of weights, × grade coefficient
  assert.ok(js.includes("weightedSum * gradeCoefficient"), "index = weighted sum × grade coefficient");
  assert.ok(!js.includes("weightedSum /"), "index must NOT divide by sum of weights (HANDOVER §4)");
});

// ── Roll-up: persisted-only, no zero-fill, index is a sum ─────────────────

test("rollup reads period_results only and never joins live evaluation inputs", () => {
  const js = jsOf("Build Rollup Query");
  assert.ok(js.includes("performance_db.period_results"), "must read period_results");
  for (const forbidden of [
    "performance_db.evaluations",
    "performance_db.evaluation_scores",
    "performance_db.score_corrections",
    "performance_db.score_coefficients",
    "performance_db.criteria",
  ]) {
    assert.ok(
      !js.includes(forbidden),
      `rollup must not live-join ${forbidden} (invariant D-0821-2)`
    );
  }
});

test("annual rating excludes out-of-scope and no-data rows; index is a plain SUM", () => {
  const js = jsOf("Build Rollup Query");
  assert.match(
    js,
    /AVG\(pr\.final_rating\)[\s\S]{0,400}pr\.is_in_scope = true[\s\S]{0,100}pr\.final_rating IS NOT NULL/,
    "mean must run over in-scope periods with data only"
  );
  assert.match(
    js,
    /SUM\(pr\.bonus_index\)[\s\S]{0,400}pr\.is_in_scope = true/,
    "index must be a sum over in-scope periods"
  );
  assert.ok(!/COALESCE\(\s*pr\.final_rating\s*,\s*0/.test(js), "no zero-fill of missing finals");
  assert.ok(!/COALESCE\(\s*pr\.bonus_index\s*,\s*0/.test(js), "no zero-fill of missing indices");
});

// ── Reparent / create container rules ─────────────────────────────────────

test("a period with evaluations can never become a container; child dates stay inside", () => {
  for (const name of ["Build Reparent SQL", "Build Create SQL"]) {
    const js = jsOf(name);
    assert.ok(js.includes("PARENT_HAS_EVALUATIONS"), `${name}: evaluations block container-hood`);
    assert.ok(js.includes("CHILD_DATES_OUTSIDE_PARENT"), `${name}: child dates must lie within parent`);
    assert.ok(js.includes("PARENT_IS_CHILD"), `${name}: no nested containers`);
    assert.ok(js.includes("PARENT_ACTIVE"), `${name}: the active period cannot be a container`);
  }
  const reparent = jsOf("Build Reparent SQL");
  assert.ok(reparent.includes("CHILD_IS_CONTAINER"), "a container cannot be attached as a child");
});

test("GET periods carries hierarchy metadata", () => {
  const js = jsOf("Build Periods Query");
  for (const col of ["child_count", "has_evaluations", "has_results", "parent_period_id"]) {
    assert.ok(js.includes(col), `GET periods must expose ${col}`);
  }
});

// ── Behavioral: execute the compute node with fixtures ────────────────────

function runComputeNode(prevJson, datasetRows) {
  const js = jsOf("Compute Close Results");
  const $ = (name) => {
    assert.equal(name, "Build Close Dataset Query");
    return { first: () => ({ json: prevJson }) };
  };
  const $input = { all: () => datasetRows.map((r) => ({ json: r })) };
  const fn = new Function("$", "$input", js);
  return fn($, $input);
}

const CRIT = (id, manager, opts = {}) => ({
  criteria_id: id,
  c_level_only: opts.cLevelOnly || false,
  weight: opts.weight ?? "1.00",
  score_coefficients: opts.coefficients || {},
  manager_score: manager,
  c_level_score: opts.cLevelScore ?? null,
  mid_level_correction: opts.mid ?? null,
  c_level_correction: opts.corr ?? null,
});

test("compute node: evaluated person gets exact final and index; no-data person gets NULLs", () => {
  const prev = { ok: true, period_id: 101, actor_id: 1, evaluation_count: 3 };
  const rows = [
    {
      user_id: 1002,
      is_in_scope: true,
      has_data: true,
      grade_coefficient: "1.50",
      rating_manager: "6.00",
      rating_upward: null,
      rating_c_level_direct: null,
      rating_self: "7.00",
      criteria: [CRIT(3, 6), CRIT(4, 6, { weight: "2.00" })],
    },
    {
      // in scope, never evaluated → explicit no-data marker, not zeros
      user_id: 1003,
      is_in_scope: true,
      has_data: false,
      grade_coefficient: "1.00",
      rating_manager: null,
      rating_upward: null,
      rating_c_level_direct: null,
      rating_self: null,
      criteria: [CRIT(3, null), CRIT(4, null)],
    },
    {
      // out of scope → no numbers at all
      user_id: 1005,
      is_in_scope: false,
      has_data: true,
      grade_coefficient: "1.00",
      rating_manager: "9.00",
      rating_upward: null,
      rating_c_level_direct: null,
      rating_self: null,
      criteria: [CRIT(3, 9)],
    },
  ];
  const out = runComputeNode(prev, rows).json;
  assert.equal(out.ok, true);
  assert.equal(out.in_scope_count, 2);
  assert.equal(out.no_data_count, 1);
  const sql = out.sql;
  // person 1002: final = mean(6,6) = 6; index = (6×1 + 6×2) × 1.5 = 27
  assert.ok(sql.includes("(1002, true, true, 6.00, NULL, NULL, 7.00, 6.0000, 27.0000)"),
    `evaluated row must persist exact numbers, got: ${sql.match(/\(1002[^)]*\)/)?.[0]}`);
  // person 1003: no data — NULLs everywhere, no zeros
  assert.ok(sql.includes("(1003, true, false, NULL, NULL, NULL, NULL, NULL, NULL)"),
    `no-data row must be NULLs, got: ${sql.match(/\(1003[^)]*\)/)?.[0]}`);
  // person 1005: out of scope — numbers dropped even if present in the dataset
  assert.ok(sql.includes("(1005, false, false, NULL, NULL, NULL, NULL, NULL, NULL)"),
    `out-of-scope row must carry no numbers, got: ${sql.match(/\(1005[^)]*\)/)?.[0]}`);
});

test("compute node: corrections average into the final cell; coefficients apply by rounded level", () => {
  const prev = { ok: true, period_id: 102, actor_id: 1, evaluation_count: 1 };
  const rows = [
    {
      user_id: 1002,
      is_in_scope: true,
      has_data: true,
      grade_coefficient: null, // missing grade → 1.0 like the client
      rating_manager: "6.00",
      rating_upward: null,
      rating_c_level_direct: null,
      rating_self: null,
      // final cell = mean(6, 8) = 7; level-7 coefficient 1.2, weight 2 → 7×1.2×2 = 16.8
      criteria: [CRIT(3, 6, { corr: 8, weight: "2.00", coefficients: { 7: "1.20" } })],
    },
  ];
  const out = runComputeNode(prev, rows).json;
  assert.ok(out.sql.includes("(1002, true, true, 6.00, NULL, NULL, NULL, 7.0000, 16.8000)"),
    `corrected row mismatch: ${out.sql.match(/\(1002[^)]*\)/)?.[0]}`);
});
