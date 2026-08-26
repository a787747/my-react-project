/**
 * Static analysis for generated deferred route-guard workflows.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import { readFileSync, readdirSync, existsSync, mkdtempSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const SCRIPT = join(REPO_ROOT, "scripts", "build_route_guard_deferred.py");
const OUT_DIR = mkdtempSync(join(tmpdir(), "rg-deferred-"));

execSync(`python3 "${SCRIPT}" --output-directory "${OUT_DIR}" 2>&1`, {
  cwd: REPO_ROOT,
});

function load(filename) {
  return JSON.parse(readFileSync(join(OUT_DIR, filename), "utf8"));
}

const EXPECTED_FILES = [
  "evaluations-matrix.json",
  "all-evaluations.json",
  "evaluation-details-by-user.json",
  "analytics.json",
  "get-admin-data.json",
  "manager-subordinates-matrix.json",
  "employee-self-review.json",
  "score-correction.json",
  "manage-criteria.json",
  "update-admin-data.json",
];

const EXPECTED_NAMES = {
  "evaluations-matrix.json": "API: evaluations-matrix",
  "all-evaluations.json": "API: All-evaluation",
  "evaluation-details-by-user.json": "API: evaluation-details-by-user",
  "analytics.json": "API: Analytics Dashboard - Optimized",
  "get-admin-data.json": "API: Get Admin Data Fixed",
  "manager-subordinates-matrix.json": "API: Manager Subordinates Matrix",
  "employee-self-review.json": "API: Get Employee Self Review",
  "score-correction.json": "API: Score Correction",
  "manage-criteria.json": "API: Manage Criteria Admin V7",
  "update-admin-data.json": "API: Update Admin Data",
};

function allNodes(wf) {
  return wf.nodes || [];
}

function codeNodes(wf) {
  return allNodes(wf).filter((n) => n.type === "n8n-nodes-base.code");
}

function webhookNodes(wf) {
  return allNodes(wf).filter((n) => n.type === "n8n-nodes-base.webhook");
}

function guardCallNodes(wf) {
  return allNodes(wf).filter((n) => n.type === "n8n-nodes-base.executeWorkflow");
}

function allJsCode(wf) {
  return codeNodes(wf)
    .map((n) => n.parameters?.jsCode || "")
    .join("\n");
}

function webhookPaths(wf) {
  return webhookNodes(wf).map((n) => ({
    method: n.parameters?.httpMethod || "GET",
    path: n.parameters?.path,
  }));
}

test("all expected deferred workflow files are generated", () => {
  for (const f of EXPECTED_FILES) {
    assert.ok(existsSync(join(OUT_DIR, f)), `${f} should be generated`);
  }
});

test("EPE: Auth Guard is not generated", () => {
  for (const f of readdirSync(OUT_DIR)) {
    assert.notEqual(load(f).name, "EPE: Auth Guard");
  }
});

test("each file contains the correct n8n workflow name", () => {
  for (const [file, expectedName] of Object.entries(EXPECTED_NAMES)) {
    assert.equal(load(file).name, expectedName);
  }
});

test("webhook paths and methods match the live deferred routes", () => {
  const expected = [
    ["evaluations-matrix.json", "GET", "api/admin/evaluations-matrix"],
    ["all-evaluations.json", "GET", "api/admin/all-evaluations"],
    ["evaluation-details-by-user.json", "GET", "api/admin/evaluation-details-by-user"],
    ["analytics.json", "GET", "api/analytics"],
    ["get-admin-data.json", "GET", "get-admin-data"],
    ["manager-subordinates-matrix.json", "GET", "api/manager-subordinates-matrix"],
    ["employee-self-review.json", "GET", "api/employee-self-review"],
    ["score-correction.json", "POST", "api/admin/score-correction"],
    ["manage-criteria.json", "POST", "manage-criteria"],
    ["update-admin-data.json", "POST", "update-admin-data"],
  ];
  for (const [file, method, path] of expected) {
    const paths = webhookPaths(load(file));
    assert.ok(
      paths.some((w) => w.method === method && w.path === path),
      `${file}: missing ${method} ${path}`
    );
  }
});

test("manager-subordinates-matrix keeps an OPTIONS twin without the guard", () => {
  const wf = load("manager-subordinates-matrix.json");
  assert.ok(
    webhookPaths(wf).some(
      (w) => w.method === "OPTIONS" && w.path === "api/manager-subordinates-matrix"
    )
  );
});

test("every generated workflow calls the auth guard", () => {
  for (const filename of EXPECTED_FILES) {
    assert.ok(guardCallNodes(load(filename)).length >= 1, filename);
  }
});

test("execution-data persistence is disabled", () => {
  for (const filename of EXPECTED_FILES) {
    const s = load(filename).settings || {};
    assert.equal(s.saveDataErrorExecution, "none");
    assert.equal(s.saveDataSuccessExecution, "none");
    assert.equal(s.saveManualExecutions, false);
  }
});

test("company-wide reporting routes require admin and c_level", () => {
  for (const file of [
    "evaluations-matrix.json",
    "all-evaluations.json",
    "evaluation-details-by-user.json",
    "analytics.json",
    "get-admin-data.json",
  ]) {
    const js = allJsCode(load(file));
    assert.ok(js.includes('"admin"') && js.includes('"c_level"'), file);
    assert.ok(!js.includes('"hr"'), `${file} must not admit HR`);
  }
});

test("manager-subordinates-matrix admits admin, c_level, manager and uses actor id", () => {
  const js = allJsCode(load("manager-subordinates-matrix.json"));
  assert.ok(js.includes('"admin"') && js.includes('"c_level"') && js.includes('"manager"'));
  assert.ok(js.includes("guard.identity.id"));
  assert.ok(js.includes("Client manager_id is ignored") || js.includes("manager_id is ignored"));
});

test("score-correction uses guard.identity.id and ignores client evaluator_id", () => {
  const js = allJsCode(load("score-correction.json"));
  assert.ok(js.includes("guard.identity.id"));
  assert.ok(!js.includes("body.evaluator_id"));
  assert.ok(js.includes("ON CONFLICT (subject_id, criteria_id, correction_level, period_id)"));
  assert.ok(js.includes("correctionLevel = 'c_level'"));
  assert.ok(js.includes("correctionLevel = 'mid_level'"));
});

test("score-correction refuses role c_level at the guard (ROLE_ACCESS_HR_CLEVEL)", () => {
  // Owner's brief, 2026-08-26: C-level is a reader; no write route accepts
  // c_level or hr. This narrows the writer half of D-0820-7 — c_level-level
  // corrections are stored by admin alone; the mid_level path (skip-level
  // manager) and the can_evaluate capability check are unchanged.
  const js = allJsCode(load("score-correction.json"));
  assert.ok(
    js.includes('required_roles: ["admin", "manager"]'),
    'score-correction: required_roles must be exactly ["admin", "manager"]'
  );
  assert.ok(
    js.includes('required_capability: "can_evaluate"'),
    "score-correction: the can_evaluate capability check must stay"
  );
  assert.equal(
    js.includes("prev.role === 'admin' || prev.role === 'c_level'"),
    false,
    "score-correction: the c_level branch of Decide Level must be gone"
  );
});

test("employee-self-review ignores client subject_id and uses the actor", () => {
  const js = allJsCode(load("employee-self-review.json"));
  assert.ok(js.includes("guard.identity.id"));
  assert.ok(!js.includes("query.subject_id"));
});

test("update-admin-data stays admin-only — exactly", () => {
  const js = allJsCode(load("update-admin-data.json"));
  assert.ok(
    js.includes('required_roles: ["admin"]'),
    'update-admin-data: required_roles must be exactly ["admin"] — the money WRITE never widens'
  );
});

test("manage-criteria admits admin + c_level, and refuses every non-admin write by role", () => {
  // ROLE_ACCESS_HR_CLEVEL (2026-08-26): C-level reads the criteria admin page
  // through action 'get'; 'save'/'delete' answer 403 ROLE_FORBIDDEN for any
  // non-admin BEFORE the freeze check and before any SQL. HR is not admitted
  // at all — the owner granted HR the employees roster only.
  const js = allJsCode(load("manage-criteria.json"));
  assert.ok(
    js.includes('required_roles: ["admin", "c_level"]'),
    'manage-criteria: required_roles must be exactly ["admin", "c_level"]'
  );
  assert.ok(
    js.includes("action !== 'get' && String(guard.identity.role || '') !== 'admin'"),
    "manage-criteria: writes must be refused by role for every non-admin"
  );
  assert.ok(
    js.includes("Изменение критериев доступно только администратору"),
    "manage-criteria: the write refusal must say why"
  );
  const routeJs = allJsCode(load("manage-criteria.json"));
  const refusalAt = routeJs.indexOf("ROLE_FORBIDDEN");
  const freezeAt = routeJs.indexOf("EVALUATION_STARTED");
  assert.ok(refusalAt !== -1 && freezeAt !== -1 && refusalAt < freezeAt,
    "manage-criteria: the role refusal must sit before the freeze check");
});

// D-0822-1: the catalogue freezes when the evaluation STARTS, not when the
// period is activated. Draft and the preparation window are both editable.
test("manage-criteria write freezes on evaluation_started_at, not on activation", () => {
  const js = allJsCode(load("manage-criteria.json"));
  assert.ok(
    js.includes("evaluation_started_at IS NOT NULL"),
    "manage-criteria: write freeze must key on evaluation_started_at"
  );
  assert.equal(
    js.includes("is_active = true OR status = 'active'"),
    false,
    "manage-criteria: the activation-wide freeze predicate must be gone"
  );
  assert.ok(js.includes("EVALUATION_STARTED"), "manage-criteria: freeze error code");
  assert.ok(js.includes("409"), "manage-criteria: freeze must be 409");
});

// D-0822-2: grade coefficients are editable until close. The 409 is gone and
// the write is validated instead (BUG-029: zero rejected, not defaulted to 1.0).
test("update-admin-data has no period freeze and validates grade coefficients", () => {
  const js = allJsCode(load("update-admin-data.json"));
  assert.equal(js.includes("ACTIVE_PERIOD_EXISTS"), false,
    "update-admin-data: the ACTIVE_PERIOD_EXISTS 409 must be removed entirely");
  assert.equal(js.includes("is_active = true OR status = 'active'"), false,
    "update-admin-data: the freeze SELECT must be gone");
  assert.ok(js.includes("INVALID_GRADE_COEFFICIENT"), "update-admin-data: coefficient validation");
  assert.ok(js.includes("coefficient <= 0"), "update-admin-data: zero must be rejected (BUG-029)");
  assert.ok(js.includes("INVALID_SETTING_KEY"), "update-admin-data: setting_key must be validated");
  assert.ok(js.includes("INVALID_SETTING_VALUE"), "update-admin-data: setting_value must be numeric");
});

// The freeze workflow must not carry a dead period SELECT any more.
test("update-admin-data no longer has a freeze-check node", () => {
  const wf = load("update-admin-data.json");
  const names = allNodes(wf).map((n) => n.name);
  assert.equal(names.includes("Check Freeze"), false);
  assert.equal(names.includes("Load Active Period"), false);
});

test("every webhook can reach a respondToWebhook node", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const names = new Set(allNodes(wf).map((n) => n.name));
    const respondNames = new Set(
      allNodes(wf)
        .filter((n) => n.type === "n8n-nodes-base.respondToWebhook")
        .map((n) => n.name)
    );
    const conns = wf.connections || {};
    function reachable(start) {
      const seen = new Set();
      const queue = [start];
      while (queue.length) {
        const cur = queue.shift();
        if (seen.has(cur)) continue;
        seen.add(cur);
        for (const outputs of conns[cur]?.main || []) {
          for (const edge of outputs || []) {
            if (edge?.node) queue.push(edge.node);
          }
        }
      }
      return seen;
    }
    for (const hook of webhookNodes(wf)) {
      const seen = reachable(hook.name);
      assert.ok(
        [...respondNames].some((name) => seen.has(name)),
        `${filename} webhook ${hook.name} cannot reach a Respond node`
      );
    }
  }
});

test("postgres query expressions keep the n8n ={{ }} wrapper", () => {
  for (const filename of EXPECTED_FILES) {
    for (const node of allNodes(load(filename))) {
      if (node.type !== "n8n-nodes-base.postgres") continue;
      const query = node.parameters?.query || "";
      if (query.includes("$json") || query.includes("$('")) {
        assert.ok(
          query.startsWith("={{"),
          `${filename} ${node.name}: expected ={{ expression, got ${query.slice(0, 40)}`
        );
      }
    }
  }
});

test("write routes do not use request-body identity as actor", () => {
  const js = allJsCode(load("score-correction.json"));
  assert.ok(js.includes("actor_id: actorId") || js.includes("actorId"));
  assert.match(js, /evaluator_id, \$\{prev\.actor_id\}|evaluator_id = EXCLUDED\.evaluator_id/);
});

test("evaluations-matrix binds cells to one period and manager_score to evaluation_source", () => {
  const js = allJsCode(load("evaluations-matrix.json"));
  assert.ok(js.includes("evaluation_source = 'manager'"));
  assert.ok(js.includes("evaluation_source = 'c_level_direct'"));
  assert.ok(js.includes("e.period_id = ${periodId}") || js.includes("period_id = ${periodId}"));
  assert.ok(js.includes("campaign_active"));
  assert.ok(js.includes("actor_c_level_evaluation_id"));
  assert.ok(js.includes("is_in_scope"));
  assert.equal(js.includes("evaluator.role IN ('manager'"), false);
  assert.equal(js.includes("evaluator.role IN ('admin', 'c_level')"), false);
});

test("score-correction binds writes to the active period only", () => {
  const js = allJsCode(load("score-correction.json"));
  assert.ok(js.includes("p.is_active = true AND p.status = 'active'"));
  assert.ok(js.includes("NO_ACTIVE_PERIOD"));
  assert.equal(js.includes("p.status <> 'closed'"), false);
  assert.equal(js.includes("ORDER BY p.id DESC"), false);
});

test("all-evaluations binds to one period and deduplicates manager_evaluations_given", () => {
  const js = allJsCode(load("all-evaluations.json"));
  assert.ok(js.includes("e.period_id = ${periodId}"));
  assert.ok(js.includes("DISTINCT ON (e.evaluator_id)"));
  assert.ok(js.includes("campaign_active"));
  assert.ok(js.includes("evaluation_source = 'manager'"));
});

test("analytics binds aggregates to one named period", () => {
  const js = allJsCode(load("analytics.json"));
  assert.ok(js.includes("e.period_id = ${periodId}") || js.includes("period_id = ${periodId}"));
  assert.ok(js.includes("campaign_active"));
  assert.ok(js.includes("no_period"));
  assert.ok(js.includes("function uniqueBy"));
  assert.ok(js.includes("uniqueBy($('Get Period Trends').all(), 'period_name')"));
});

test("details-by-user uses detail_type in SQL and binds the period", () => {
  const js = allJsCode(load("evaluation-details-by-user.json"));
  assert.ok(js.includes("received_from_manager"));
  assert.ok(js.includes("from_subordinates"));
  assert.ok(js.includes("gave_to_manager"));
  assert.ok(js.includes("gave_to_subordinates"));
  assert.ok(js.includes("e.period_id"));
  assert.ok(js.includes("INVALID_QUERY"));
  assert.ok(js.includes("campaign_active"));
});

test("manager-subordinates-matrix binds period and manager_score to evaluation_source", () => {
  const js = allJsCode(load("manager-subordinates-matrix.json"));
  assert.ok(js.includes("evaluation_source = 'manager'"));
  assert.ok(js.includes("e.period_id = ${periodId}"));
  assert.ok(js.includes("campaign_active"));
  assert.equal(js.includes("evaluator.role IN ('manager'"), false);
});

test("manage-criteria GET names the active period without emptying the catalogue", () => {
  const js = allJsCode(load("manage-criteria.json"));
  assert.ok(js.includes("_period"));
  assert.ok(js.includes("FROM performance_db.criteria"));
  // The GET branch reports both gates so the admin screen can say which one holds.
  assert.ok(js.includes("campaign_active"));
  assert.ok(js.includes("evaluation_started"));
});

// D-0822-1: corrections are a campaign action — the period must be active AND started.
test("score-correction binds to a started campaign period", () => {
  const js = allJsCode(load("score-correction.json"));
  assert.ok(js.includes("p.evaluation_started_at IS NOT NULL"),
    "score-correction: period lookup must require evaluation_started_at");
  assert.ok(js.includes("NO_ACTIVE_PERIOD"));
});

// Admin/reporting reads stay keyed on active, not on started.
test("reporting reads stay keyed on the active period only", () => {
  for (const file of ["evaluations-matrix.json", "all-evaluations.json", "analytics.json",
                      "evaluation-details-by-user.json", "manager-subordinates-matrix.json"]) {
    const js = allJsCode(load(file));
    assert.equal(js.includes("evaluation_started_at"), false,
      `${file}: reporting must not key on the start gate`);
  }
});

// ── Reclassification (D-0822-3) and leaf-only period resolution (BUG-043) ────

test("the matrix emits project-criterion cells only for current project participants", () => {
  const js = allJsCode(load("evaluations-matrix.json"));
  assert.ok(
    js.includes("c.target_audience <> 'project_participants' OR u.is_project_participant = true"),
    "matrix: a cell for a project criterion exists only for a current project participant"
  );
  // the emission filter must sit in the row-source WHERE, next to is_active
  assert.ok(
    /CROSS JOIN performance_db\.criteria c[\s\S]*?c\.is_active = true[\s\S]*?project_participants/.test(js),
    "matrix: the filter belongs to the CROSS JOIN row source, not to a sub-select"
  );
});

test("score-correction binds to an active started LEAF period only", () => {
  const js = allJsCode(load("score-correction.json"));
  assert.ok(js.includes("period_type <> 'annual'") && js.includes("parent_period_id"),
    "score-correction: a container or annual period can never be the campaign period");
});

// ── Finalization batch (2026-08-24): corrections applicability + BUG-046 ─────

test("score-correction refuses a project criterion for a currently-general subject", () => {
  const js = allJsCode(load("score-correction.json"));
  assert.ok(js.includes("CRITERIA_NOT_APPLICABLE"),
    "score-correction: the write must share the D-0822-3 applicability refusal");
  // the same shared predicate inputs as submit/additive/update/self-review
  assert.ok(js.includes("subject_is_project"),
    "score-correction: the lookup must read the subject's CURRENT classification");
  assert.ok(js.includes("target_audience = 'project_participants'"),
    "score-correction: the project-criteria set comes from the shared predicate");
  assert.ok(js.includes("project_criteria_ids"),
    "score-correction: the criteria list must reach the decide step");
});

test("manager-subordinates-matrix emits project cells only for current project participants (BUG-046)", () => {
  const js = allJsCode(load("manager-subordinates-matrix.json"));
  assert.ok(
    js.includes("c.target_audience <> 'project_participants' OR u.is_project_participant = true"),
    "manager matrix: a cell for a project criterion exists only for a current project participant"
  );
  // the emission filter must sit in the row-source WHERE, next to is_active
  assert.ok(
    /CROSS JOIN performance_db\.criteria c[\s\S]*?c\.is_active = true[\s\S]*?project_participants/.test(js),
    "manager matrix: the filter belongs to the CROSS JOIN row source, not to a sub-select"
  );
});
