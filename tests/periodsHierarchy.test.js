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

// ── M7: period_type = 'annual' is load-bearing on activate and close ──────
// "Container" was a derived state (child_count > 0). Detaching the last child
// turned a full-year period into an ordinary activatable, closable period.

test("activation refuses an annual period regardless of child count", () => {
  const js = jsOf("Build Activation SQL");
  assert.ok(js.includes("ANNUAL_PERIOD_NOT_ACTIVATABLE"), "must carry the annual refusal code");
  assert.match(
    js,
    /http_status: 422[\s\S]{0,200}ANNUAL_PERIOD_NOT_ACTIVATABLE/,
    "annual refusal must ride a 422"
  );
  assert.ok(
    js.includes("Годовой период — контейнер отчётности"),
    "message must name the annual period as a reporting container"
  );
  assert.ok(
    js.includes("period_type != 'annual'"),
    "the activatable CTE must re-assert the type inside the UPDATE"
  );
  assert.ok(
    jsOf("Validate Period Activate").includes("t.period_type AS target_period_type"),
    "the precondition query must read the target's period_type"
  );
});

test("close refuses an annual period regardless of child count", () => {
  const build = jsOf("Build Close Dataset Query");
  assert.ok(build.includes("ANNUAL_PERIOD_NOT_CLOSABLE"), "must carry the annual refusal code");
  assert.match(
    build,
    /http_status: 422[\s\S]{0,200}ANNUAL_PERIOD_NOT_CLOSABLE/,
    "annual refusal must ride a 422"
  );
  assert.ok(build.includes("Годовой период — контейнер отчётности"), "message must be the agreed one");
  assert.ok(
    jsOf("Validate Period Close").includes("t.period_type AS target_period_type"),
    "the precondition query must read the target's period_type"
  );
  assert.ok(
    jsOf("Compute Close Results").includes("period_type != 'annual'"),
    "the close target CTE must re-assert the type inside the atomic statement"
  );
});

// ── M4: overlapping siblings double-count in the annual SUM ──────────────

test("create and reparent reject a child overlapping an existing sibling", () => {
  for (const name of ["Build Create SQL", "Build Reparent SQL"]) {
    const js = jsOf(name);
    assert.ok(js.includes("SIBLING_DATES_OVERLAP"), `${name}: overlap must be refused`);
    assert.match(
      js,
      /http_status: 422[\s\S]{0,200}SIBLING_DATES_OVERLAP/,
      `${name}: overlap refusal must ride a 422`
    );
    assert.ok(
      /NOT EXISTS \(\s*\n?\s*SELECT 1 FROM performance_db\.evaluation_periods sib/.test(js),
      `${name}: the write must re-assert non-overlap`
    );
  }
  assert.ok(
    jsOf("Validate Period Create").includes("AS sibling_overlap_count"),
    "create precondition query must count overlapping siblings"
  );
  assert.ok(
    jsOf("Validate Period Reparent").includes("AS sibling_overlap_count"),
    "reparent precondition query must count overlapping siblings"
  );
});

// ── Behavioral: execute the refusal nodes with fixtures ──────────────────

/** Run a Code node that reads one named upstream node plus $input rows. */
function runNode(nodeName, upstreamName, prevJson, inputRows) {
  const js = jsOf(nodeName);
  const $ = (name) => {
    assert.equal(name, upstreamName, `${nodeName} must read ${upstreamName}`);
    return { first: () => ({ json: prevJson }) };
  };
  const $input = { all: () => inputRows.map((r) => ({ json: r })) };
  return new Function("$", "$input", js)($, $input).json;
}

test("annual period: activate 422s with zero children, half_year passes the type gate", () => {
  const prev = { ok: true, target_period_id: 5 };
  const annualLeaf = {
    target_id: 5, target_status: "draft", target_period_type: "annual",
    target_child_count: 0, current_active_id: null, current_active_name: null,
    has_evaluations: false,
  };
  const refused = runNode("Build Activation SQL", "Validate Period Activate", prev, [annualLeaf]);
  assert.equal(refused.http_status, 422);
  assert.equal(refused.body.error, "ANNUAL_PERIOD_NOT_ACTIVATABLE");

  // the same shape with period_type half_year builds SQL instead of refusing
  const allowed = runNode("Build Activation SQL", "Validate Period Activate", prev,
    [{ ...annualLeaf, target_period_type: "half_year" }]);
  assert.equal(allowed.http_status, undefined, `half_year must not be refused: ${JSON.stringify(allowed.body)}`);
  assert.ok(allowed.sql.includes("period_type != 'annual'"), "the UPDATE still re-asserts the type");
});

test("annual period: close 422s with zero children, half_year reaches the dataset step", () => {
  const prev = { ok: true, period_id: 5, actor_id: 2 };
  const annualActive = {
    target_id: 5, target_name: "Annual 2026", target_status: "active", target_is_active: true,
    target_period_type: "annual", child_count: 0, evaluation_count: 0, has_results: false,
    participant_count: 89,
  };
  const refused = runNode("Build Close Dataset Query", "Validate Period Close", prev, [annualActive]);
  assert.equal(refused.http_status, 422);
  assert.equal(refused.body.error, "ANNUAL_PERIOD_NOT_CLOSABLE");

  const allowed = runNode("Build Close Dataset Query", "Validate Period Close", prev,
    [{ ...annualActive, target_period_type: "half_year" }]);
  assert.equal(allowed.http_status, undefined, `half_year must not be refused: ${JSON.stringify(allowed.body)}`);
  assert.equal(allowed.ok, true);
});

test("sibling overlap: create refuses an overlapping child, the H1/H2 split passes", () => {
  const parent = {
    name_taken: false, parent_id: 5, parent_start: "2026-01-01", parent_end: "2026-12-31",
    parent_status: "draft", parent_parent_id: null, parent_has_evaluations: false,
    // Postgres decides whether the child fits: dates that cross the n8n node
    // arrive shifted by the timezone offset, so JS must not compare them.
    child_inside_parent: true,
  };
  const prevH2 = {
    ok: true, name: "H2-2026", start_date: "2026-07-01", end_date: "2026-12-31",
    period_type: "half_year", parent_id: 5,
  };
  // H1 (01.01–30.06) already attached: the canonical H2 does not overlap it
  const ok = runNode("Build Create SQL", "Validate Period Create", prevH2,
    [{ ...parent, sibling_overlap_count: 0 }]);
  assert.equal(ok.http_status, undefined, `canonical H1+H2 split must pass: ${JSON.stringify(ok.body)}`);
  assert.ok(ok.sql.includes("sib.parent_period_id = 5"), "the INSERT must re-assert non-overlap");

  // a child that does overlap the existing sibling is refused
  const clash = runNode("Build Create SQL", "Validate Period Create",
    { ...prevH2, name: "H2 overlapping", start_date: "2026-06-01" },
    [{ ...parent, sibling_overlap_count: 1 }]);
  assert.equal(clash.http_status, 422);
  assert.equal(clash.body.error, "SIBLING_DATES_OVERLAP");
});

test("sibling overlap: reparent refuses an overlapping child", () => {
  const prev = { ok: true, period_id: 7, parent_id: 5 };
  const base = {
    child_id: 7, child_start: "2026-06-01", child_end: "2026-12-31", child_child_count: 0,
    parent_id: 5, parent_start: "2026-01-01", parent_end: "2026-12-31",
    parent_status: "draft", parent_parent_id: null, parent_has_evaluations: false,
    child_inside_parent: true,
  };
  const clash = runNode("Build Reparent SQL", "Validate Period Reparent", prev,
    [{ ...base, sibling_overlap_count: 1 }]);
  assert.equal(clash.http_status, 422);
  assert.equal(clash.body.error, "SIBLING_DATES_OVERLAP");

  const ok = runNode("Build Reparent SQL", "Validate Period Reparent", prev,
    [{ ...base, child_start: "2026-07-01", sibling_overlap_count: 0 }]);
  assert.equal(ok.http_status, undefined, `non-overlapping attach must pass: ${JSON.stringify(ok.body)}`);
  assert.ok(ok.sql.includes("sib.parent_period_id = 5"), "the UPDATE must re-assert non-overlap");
});

test("detach stays unconditional — it is the only escape from a wrong container", () => {
  const detached = runNode("Build Reparent SQL", "Validate Period Reparent",
    { ok: true, period_id: 7, parent_id: null },
    [{ child_id: 7, child_start: "2026-07-01", child_end: "2026-12-31", child_child_count: 0,
       parent_id: null, sibling_overlap_count: 0 }]);
  assert.equal(detached.http_status, undefined);
  assert.ok(detached.sql.includes("SET parent_period_id = NULL"), "detach must still work");
});

// ── Parent-date containment is decided by Postgres, not by JS ─────────────
// The n8n Postgres node returns `date` columns as JS Dates serialised in UTC,
// so a date read out of the database is one calendar day early in Moscow time.
// Comparing a client-supplied 'YYYY-MM-DD' against that string refused a child
// ending on the parent's own last day — i.e. the canonical H2 01.07–31.12.

test("child-inside-parent is computed in SQL and only an explicit true passes", () => {
  for (const [validate, build] of [
    ["Validate Period Create", "Build Create SQL"],
    ["Validate Period Reparent", "Build Reparent SQL"],
  ]) {
    assert.ok(
      jsOf(validate).includes("AS child_inside_parent"),
      `${validate}: containment must be decided by Postgres`
    );
    const js = jsOf(build);
    assert.ok(
      js.includes("check.child_inside_parent === true"),
      `${build}: must read the SQL verdict`
    );
    assert.ok(
      !js.includes("String(value ?? '').slice(0, 10)"),
      `${build}: must not slice timezone-shifted dates in JS`
    );
    assert.ok(js.includes("CHILD_DATES_OUTSIDE_PARENT"), `${build}: keeps the refusal`);
  }
});

test("a child ending on the parent's last day is accepted, an unknown verdict is not", () => {
  const prev = {
    ok: true, name: "H2-2026", start_date: "2026-07-01", end_date: "2026-12-31",
    period_type: "half_year", parent_id: 5,
  };
  const parent = {
    name_taken: false, parent_id: 5, parent_start: "2026-01-01", parent_end: "2026-12-31",
    parent_status: "draft", parent_parent_id: null, parent_has_evaluations: false,
    sibling_overlap_count: 0,
  };
  const accepted = runNode("Build Create SQL", "Validate Period Create", prev,
    [{ ...parent, child_inside_parent: true }]);
  assert.equal(accepted.http_status, undefined,
    `H2 ending on the container's last day must be accepted: ${JSON.stringify(accepted.body)}`);

  for (const verdict of [false, null, undefined]) {
    const refused = runNode("Build Create SQL", "Validate Period Create", prev,
      [{ ...parent, child_inside_parent: verdict }]);
    assert.equal(refused.http_status, 422, `verdict ${verdict} must refuse`);
    assert.equal(refused.body.error, "CHILD_DATES_OUTSIDE_PARENT");
  }
});
