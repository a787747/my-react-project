/**
 * routeGuardWorkflows.test.js
 *
 * Static analysis test suite for generated route-guard workflow payloads.
 * Runs the Python generator, loads produced JSONs, and asserts:
 *  - every workflow/method/path matches spec
 *  - every protected endpoint calls EPE: Auth Guard
 *  - actor identity always comes from guard output (never from request body)
 *  - execution-data persistence is disabled
 *  - key business-logic and security invariants are present in code nodes
 */
import test from "node:test";
import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import { readFileSync, readdirSync, existsSync, mkdtempSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Generator setup ────────────────────────────────────────────────────────

const REPO_ROOT = resolve(__dirname, "..");
const SCRIPT = join(REPO_ROOT, "scripts", "build_route_guard_workflows.py");
const OUT_DIR = mkdtempSync(join(tmpdir(), "rg-wf-test-"));

execSync(
  `python3 "${SCRIPT}" --output-directory "${OUT_DIR}" 2>&1`,
  { cwd: REPO_ROOT }
);

/** @param {string} filename */
function load(filename) {
  return JSON.parse(readFileSync(join(OUT_DIR, filename), "utf8"));
}

const EXPECTED_FILES = [
  "criteria.json",
  "get-my-manager.json",
  "my-profile.json",
  "check-evaluated.json",
  "check-self-review.json",
  "submit-evaluation.json",
  "update-evaluation.json",
  "self-review-submit.json",
  "evaluation-details.json",
  "evaluation-history.json",
  "hr-evaluation-status.json",
  "score-coefficients.json",
  "save-score-coefficients.json",
  "create-invite.json",
  "admin-users-data.json",
  "save-user.json",
  "manage-periods.json",
];

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

function allNodeNames(wf) {
  return allNodes(wf).map((n) => n.name);
}

function webhookPaths(wf) {
  return webhookNodes(wf).map((n) => ({
    method: n.parameters?.httpMethod || "GET",
    path: n.parameters?.path,
  }));
}

// ── 1. File completeness ───────────────────────────────────────────────────

test("all expected workflow files are generated", () => {
  for (const f of EXPECTED_FILES) {
    assert.ok(
      existsSync(join(OUT_DIR, f)),
      `${f} should be generated`
    );
  }
});

test("EPE: Auth Guard is not generated or modified", () => {
  const outputFiles = readdirSync(OUT_DIR);
  for (const f of outputFiles) {
    const wf = load(f);
    assert.notEqual(
      wf.name,
      "EPE: Auth Guard",
      `${f} must not be the auth guard workflow`
    );
  }
});

// ── 2. Correct workflow names ─────────────────────────────────────────────

const EXPECTED_NAMES = {
  "criteria.json": "API: Get Criteria With Levels",
  "get-my-manager.json": "API: Get My Manager",
  "my-profile.json": "API: My Profile V5 (Fixed Empty)",
  "check-evaluated.json": "API: Check Evaluated V2",
  "check-self-review.json": "API: Check Self Review",
  "submit-evaluation.json": "API: Submit Evaluation",
  "update-evaluation.json": "API: Update Evaluation WITH PERIOD",
  "self-review-submit.json": "API: Submit Self Review",
  "evaluation-details.json": "API: Get Evaluation Details FIXED",
  "evaluation-history.json": "API: My Evaluation History (Received)",
  "hr-evaluation-status.json": "API: HR Evaluation Status",
  "score-coefficients.json": "API: Get Score Coefficients",
  "save-score-coefficients.json": "API: Save Score Coefficients",
  "create-invite.json": "API: Create Invite",
  "admin-users-data.json": "API: Admin Get Users Data",
  "save-user.json": "API: Admin Save User (GUI Mode)",
  "manage-periods.json": "API: Manage Periods",
};

test("each file contains the correct n8n workflow name", () => {
  for (const [file, expectedName] of Object.entries(EXPECTED_NAMES)) {
    const wf = load(file);
    assert.equal(
      wf.name,
      expectedName,
      `${file}: name should be "${expectedName}"`
    );
  }
});

// ── 3. Webhook paths and methods ─────────────────────────────────────────

test("GET webhooks have correct paths", () => {
  const getMap = {
    "criteria.json": "api/criteria",
    "get-my-manager.json": "api/get-my-manager",
    "my-profile.json": "api/my-profile",
    "check-evaluated.json": "api/check-evaluated",
    "check-self-review.json": "api/check-self-review",
    "evaluation-details.json": "api/evaluation-details",
    "evaluation-history.json": "api/evaluation-history",
    "hr-evaluation-status.json": "api/hr/evaluation-status",
    "score-coefficients.json": "api/score-coefficients",
    "admin-users-data.json": "api/admin-users-data",
  };
  for (const [file, expectedPath] of Object.entries(getMap)) {
    const wf = load(file);
    const getWebhooks = webhookPaths(wf).filter((w) => w.method === "GET");
    assert.ok(
      getWebhooks.some((w) => w.path === expectedPath),
      `${file}: expected GET webhook at path "${expectedPath}"`
    );
  }
});

test("POST webhooks have correct paths", () => {
  const postMap = {
    "submit-evaluation.json": "api/submit-evaluation",
    "update-evaluation.json": "api/update-evaluation",
    "self-review-submit.json": "api/self-review-submit",
    "save-score-coefficients.json": "api/score-coefficients",
    "create-invite.json": "api/admin/create-invite",
    "save-user.json": "admin/save-user",
  };
  for (const [file, expectedPath] of Object.entries(postMap)) {
    const wf = load(file);
    const postWebhooks = webhookPaths(wf).filter((w) => w.method === "POST");
    assert.ok(
      postWebhooks.some((w) => w.path === expectedPath),
      `${file}: expected POST webhook at path "${expectedPath}"`
    );
  }
});

test("update-evaluation includes an OPTIONS webhook", () => {
  const wf = load("update-evaluation.json");
  const optionsWebhooks = webhookPaths(wf).filter(
    (w) => w.method === "OPTIONS"
  );
  assert.ok(
    optionsWebhooks.length >= 1,
    "update-evaluation should have an OPTIONS webhook"
  );
});

test("manage-periods exposes GET /api/periods, POST /api/periods/create and POST /api/periods/activate", () => {
  const wf = load("manage-periods.json");
  const paths = webhookPaths(wf);
  assert.ok(
    paths.some((w) => w.method === "GET" && w.path === "api/periods"),
    "manage-periods: missing GET api/periods"
  );
  assert.ok(
    paths.some((w) => w.method === "POST" && w.path === "api/periods/create"),
    "manage-periods: missing POST api/periods/create"
  );
  assert.ok(
    paths.some(
      (w) => w.method === "POST" && w.path === "api/periods/activate"
    ),
    "manage-periods: missing POST api/periods/activate"
  );
});

// ── 4. Guard calls ────────────────────────────────────────────────────────

test("every generated workflow calls EPE: Auth Guard at least once", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const guards = guardCallNodes(wf);
    assert.ok(
      guards.length >= 1,
      `${filename}: must have at least one executeWorkflow (guard) node`
    );
  }
});

test("guard input code node sets authorization from headers", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const js = allJsCode(wf);
    assert.ok(
      js.includes("authorization") && js.includes("headers"),
      `${filename}: guard input must pass authorization header`
    );
  }
});

// ── 5. Identity comes from guard, never from request body ──────────────────

test("actor identity uses guard.identity.id, not request body evaluator_id/admin_id", () => {
  // These files must reference guard.identity.id for actor
  const protectedWriteFiles = [
    "submit-evaluation.json",
    "update-evaluation.json",
    "self-review-submit.json",
    "create-invite.json",
    "save-user.json",
  ];
  for (const filename of protectedWriteFiles) {
    const wf = load(filename);
    const js = allJsCode(wf);
    assert.ok(
      js.includes("guard.identity.id"),
      `${filename}: actor identity must come from guard.identity.id`
    );
  }
});

test("request-body evaluator_id is never used as actor for SQL in submit-evaluation", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  // actorId must not be derived from body.evaluator_id
  assert.ok(
    !js.includes("body.evaluator_id") || js.includes("// Ignore body.evaluator_id"),
    "submit-evaluation: body.evaluator_id must not be used as actor"
  );
});

// ── 6. Execution-data persistence disabled ─────────────────────────────────

test("every generated workflow disables execution-data persistence", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const s = wf.settings || {};
    assert.equal(
      s.saveDataErrorExecution,
      "none",
      `${filename}: saveDataErrorExecution must be "none"`
    );
    assert.equal(
      s.saveDataSuccessExecution,
      "none",
      `${filename}: saveDataSuccessExecution must be "none"`
    );
    assert.equal(
      s.saveManualExecutions,
      false,
      `${filename}: saveManualExecutions must be false`
    );
  }
});

// ── 7. Role restrictions ─────────────────────────────────────────────────

test("hr-evaluation-status restricts to hr, admin, c_level", () => {
  const wf = load("hr-evaluation-status.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes('"hr"') && js.includes('"admin"') && js.includes('"c_level"'),
    "hr-evaluation-status: required_roles must include hr, admin, c_level"
  );
});

test("save-score-coefficients restricts to admin", () => {
  const wf = load("save-score-coefficients.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes('"admin"'),
    'save-score-coefficients: required_roles must include "admin"'
  );
});

test("admin-users-data restricts to admin", () => {
  const wf = load("admin-users-data.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes('"admin"'),
    'admin-users-data: required_roles must include "admin"'
  );
});

test("save-user restricts to admin", () => {
  const wf = load("save-user.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes('"admin"'),
    'save-user: required_roles must include "admin"'
  );
});

test("create-invite restricts to admin", () => {
  const wf = load("create-invite.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes('"admin"'),
    'create-invite: required_roles must include "admin"'
  );
});

test("manage-periods GET is restricted to admin, hr, c_level", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes('"hr"') && js.includes('"admin"') && js.includes('"c_level"'),
    "manage-periods: GET guard must include hr, admin, c_level"
  );
});

test("self-review guard allows employee, manager, hr — not admin or c_level", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  // Must include employee, manager, hr
  assert.ok(
    js.includes('"employee"') && js.includes('"manager"') && js.includes('"hr"'),
    "self-review: guard roles must include employee, manager, hr"
  );
  // Must NOT include admin or c_level in the roles array (admin/c_level blocked by guard)
  // The roles array is the first code node (guard input); check it doesn't add them
  const guardInputNode = allNodes(wf).find((n) =>
    n.name.includes("Prepare Guard Input")
  );
  const guardJs = guardInputNode?.parameters?.jsCode || "";
  assert.ok(
    !guardJs.includes('"admin"') && !guardJs.includes('"c_level"'),
    "self-review: guard input must NOT include admin or c_level in required_roles"
  );
});

// ── 8. Guard capability requirement for write operations ─────────────────

test("submit-evaluation requires can_evaluate capability in guard input", () => {
  const wf = load("submit-evaluation.json");
  const guardInputNode = allNodes(wf).find(
    (n) => n.name.includes("Prepare Guard Input") && !n.name.includes("OPTIONS")
  );
  const js = guardInputNode?.parameters?.jsCode || "";
  assert.ok(
    js.includes("can_evaluate"),
    "submit-evaluation: guard input must set required_capability = can_evaluate"
  );
});

test("submit-evaluation accepts c_level_direct for admin or c_level only", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  assert.equal(
    js.includes("SOURCE_NOT_SUPPORTED"),
    false,
    "submit-evaluation: c_level_direct must no longer be rejected as SOURCE_NOT_SUPPORTED"
  );
  assert.ok(
    js.includes("source === 'c_level_direct'")
      && js.includes("actorRole !== 'c_level'")
      && js.includes("actorRole !== 'admin'"),
    "submit-evaluation: c_level_direct must require c_level or admin"
  );
  assert.ok(
    js.includes("cem@sedamedical.com")
      && js.includes("hemra@sedamedical.com")
      && js.includes("mekan@sedamedical.com"),
    "submit-evaluation: c_level_direct must exclude the three read-only emails"
  );
  assert.ok(
    js.includes("Ignore body.evaluator_id"),
    "submit-evaluation: evaluator must be the token actor"
  );
  assert.ok(
    js.includes("AVG(score_val::numeric)"),
    "submit-evaluation: c_level_direct must keep the same AVG formula"
  );
});

test("update-evaluation requires can_evaluate capability in guard input", () => {
  const wf = load("update-evaluation.json");
  const guardInputNode = allNodes(wf).find(
    (n) =>
      n.name.includes("Prepare Guard Input") &&
      !n.name.includes("OPTIONS")
  );
  const js = guardInputNode?.parameters?.jsCode || "";
  assert.ok(
    js.includes("can_evaluate"),
    "update-evaluation: guard input must set required_capability = can_evaluate"
  );
});

// ── 9. Period check uses BOTH is_active=true AND status='active' ──────────

const BOTH_FLAGS_FILES = [
  "submit-evaluation.json",
  "self-review-submit.json",
  "hr-evaluation-status.json",
];

test("write paths use BOTH is_active=true AND status=active for period check", () => {
  for (const filename of BOTH_FLAGS_FILES) {
    const wf = load(filename);
    const js = allJsCode(wf);
    assert.ok(
      js.includes("is_active = true") && js.includes("status = 'active'"),
      `${filename}: period check must use BOTH is_active=true AND status='active'`
    );
  }
});

test("check-evaluated uses BOTH active flags for period join", () => {
  const wf = load("check-evaluated.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("is_active = true") && js.includes("status = 'active'"),
    "check-evaluated: must use BOTH active flags"
  );
});

// ── 10. Migration 012: four-column non-self uniqueness ─────────────────────

test("migration 012 uses four-column non-self uniqueness key", () => {
  const migrationPath = join(
    REPO_ROOT,
    "migrations",
    "012_reconcile_evaluation_period_constraints.sql"
  );
  assert.ok(existsSync(migrationPath), "migration 012 must exist");
  const sql = readFileSync(migrationPath, "utf8");
  // Must reference all four columns for non-self index
  assert.ok(
    sql.includes("evaluation_source") && sql.includes("period_id"),
    "migration 012: non-self index must include evaluation_source and period_id"
  );
  assert.ok(
    sql.includes("subject_id") && sql.includes("evaluator_id"),
    "migration 012: non-self index must include subject_id and evaluator_id"
  );
  // Index name
  assert.ok(
    sql.includes("idx_evaluations_unique_non_self_period"),
    "migration 012: must create idx_evaluations_unique_non_self_period"
  );
  assert.ok(
    sql.includes("idx_evaluations_unique_self_period"),
    "migration 012: must create idx_evaluations_unique_self_period"
  );
});

test("migration 012 drops all known obsolete indexes", () => {
  const sql = readFileSync(
    join(
      REPO_ROOT,
      "migrations",
      "012_reconcile_evaluation_period_constraints.sql"
    ),
    "utf8"
  );
  const obsolete = [
    "idx_evaluations_unique_pair",
    "idx_evaluations_unique_pair_with_source",
    "idx_evaluations_unique_pair_source",
    "idx_evaluations_self_unique",
  ];
  for (const name of obsolete) {
    assert.ok(
      sql.includes(name),
      `migration 012: must reference ${name} for removal`
    );
  }
});

test("migration 012 sets period_id and evaluation_source NOT NULL", () => {
  const sql = readFileSync(
    join(
      REPO_ROOT,
      "migrations",
      "012_reconcile_evaluation_period_constraints.sql"
    ),
    "utf8"
  );
  assert.ok(
    sql.includes("SET NOT NULL"),
    "migration 012: must set NOT NULL on period_id and evaluation_source"
  );
  assert.ok(
    sql.includes("period_id") && sql.includes("evaluation_source"),
    "migration 012: must reference both period_id and evaluation_source for NOT NULL"
  );
});

test("migration 012 validates four-column non-self duplicates before DDL", () => {
  const sql = readFileSync(
    join(
      REPO_ROOT,
      "migrations",
      "012_reconcile_evaluation_period_constraints.sql"
    ),
    "utf8"
  );
  // Duplicate check for non-self must include all four columns
  assert.ok(
    sql.includes("subject_id, evaluator_id, evaluation_source, period_id"),
    "migration 012: duplicate validation must GROUP BY all four columns"
  );
});

test("migration 012 is wrapped in a transaction", () => {
  const sql = readFileSync(
    join(
      REPO_ROOT,
      "migrations",
      "012_reconcile_evaluation_period_constraints.sql"
    ),
    "utf8"
  );
  assert.ok(sql.includes("BEGIN;"), "migration 012 must contain BEGIN;");
  assert.ok(sql.trimEnd().endsWith("COMMIT;"), "migration 012 must end with COMMIT;");
});

test("migration 012 conditionally recreates index if wrong definition", () => {
  const sql = readFileSync(
    join(
      REPO_ROOT,
      "migrations",
      "012_reconcile_evaluation_period_constraints.sql"
    ),
    "utf8"
  );
  // Should check existing index definition before creating
  assert.ok(
    sql.includes("pg_indexes"),
    "migration 012: must check pg_indexes to verify existing index definition"
  );
});

// ── 11. Duplicate evaluation returns 409, not 500 ─────────────────────────

test("submit-evaluation includes ON CONFLICT for the four-column non-self key", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("ON CONFLICT") &&
    js.includes("evaluation_source") &&
    js.includes("period_id"),
    "submit-evaluation: ON CONFLICT must include evaluation_source and period_id"
  );
  assert.ok(
    js.includes("409") || js.includes("DUPLICATE_EVALUATION"),
    "submit-evaluation: must return 409 for duplicate evaluations"
  );
});

test("self-review-submit includes ON CONFLICT for self-review key", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("ON CONFLICT") && js.includes("is_self_evaluation = true"),
    "self-review-submit: must handle duplicate via ON CONFLICT"
  );
  assert.ok(
    js.includes("409") || js.includes("DUPLICATE_SELF_REVIEW"),
    "self-review-submit: must return 409 for duplicate self-review"
  );
});

// ── 12. HTTP 200 for valid success on write endpoints ─────────────────────

test("submit-evaluation format node returns http_status 200 on success", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  // Should have "http_status: 200" alongside success: true
  assert.ok(
    js.includes("http_status: 200") || js.includes('"http_status": 200'),
    "submit-evaluation: success response must have http_status 200"
  );
});

test("self-review-submit format node returns http_status 200 on success", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("http_status: 200") || js.includes('"http_status": 200'),
    "self-review-submit: success response must have http_status 200"
  );
});

test("create-invite format node returns http_status 200 on success", () => {
  const wf = load("create-invite.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("http_status: 200"),
    "create-invite: success response must have http_status 200"
  );
});

// ── 13. Response-contract shape assertions ────────────────────────────────

test("get-my-manager returns {success, has_manager, manager} shape", () => {
  const wf = load("get-my-manager.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("has_manager"),
    "get-my-manager: response must include has_manager"
  );
  assert.ok(
    js.includes("has_evaluated_manager"),
    "get-my-manager: manager object must include has_evaluated_manager"
  );
  assert.ok(
    js.includes("grade_code") && js.includes("grade_coefficient"),
    "get-my-manager: manager must include grade_code and grade_coefficient"
  );
  assert.ok(
    js.includes("previous_scores"),
    "get-my-manager: manager must include previous_scores"
  );
});

test("my-profile returns {success, has_evaluations, evaluations, stats} shape", () => {
  const wf = load("my-profile.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("has_evaluations"),
    "my-profile: must include has_evaluations"
  );
  assert.ok(
    js.includes("total_evaluations") && js.includes("average_score"),
    "my-profile: stats must include total_evaluations and average_score"
  );
  assert.ok(
    js.includes("latest_score") && js.includes("latest_period"),
    "my-profile: stats must include latest_score and latest_period"
  );
});

test("my-profile redacts evaluator identity for subordinate source", () => {
  const wf = load("my-profile.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("subordinate") && js.includes("evaluator_name"),
    "my-profile: must redact evaluator_name for subordinate source"
  );
  assert.ok(
    js.includes("evaluator_title"),
    "my-profile: must redact evaluator_title for subordinate source"
  );
});

test("check-evaluated returns {success, details:[...]} shape", () => {
  const wf = load("check-evaluated.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("details"),
    "check-evaluated: must return details array"
  );
  assert.ok(
    js.includes("subject_id") && js.includes("latest_evaluation_id"),
    "check-evaluated: details must include subject_id and latest_evaluation_id"
  );
  assert.ok(
    js.includes("last_score") && js.includes("updated_at"),
    "check-evaluated: details must include last_score and updated_at"
  );
});

test("check-self-review returns {has_self_review, evaluation_id, score, date, evaluated_criteria_ids, grades, comments}", () => {
  const wf = load("check-self-review.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("has_self_review"),
    "check-self-review: must return has_self_review"
  );
  assert.ok(
    js.includes("evaluation_id") && js.includes("score"),
    "check-self-review: must return evaluation_id and score"
  );
  assert.ok(
    js.includes("evaluated_criteria_ids"),
    "check-self-review: must return evaluated_criteria_ids"
  );
  assert.ok(
    js.includes("grades") && js.includes("comments"),
    "check-self-review: must return grades and comments"
  );
});

test("evaluation-details returns {status:'success', evaluation, scores} shape", () => {
  const wf = load("evaluation-details.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("status: 'success'") || js.includes("status: \"success\""),
    "evaluation-details: must use status:'success' top-level key"
  );
  assert.ok(
    js.includes("evaluation") && js.includes("scores"),
    "evaluation-details: must return evaluation and scores"
  );
  // Must NOT wrap in success/data envelope
  assert.ok(
    !js.includes("success: true,\n    body: { status"),
    "evaluation-details: must not double-wrap in success/data and status"
  );
});

test("evaluation-details applies correct redactions", () => {
  const wf = load("evaluation-details.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("private_comment"),
    "evaluation-details: private_comment field must be handled"
  );
  assert.ok(
    js.includes("evaluator_id") && js.includes("evaluator_name"),
    "evaluation-details: evaluator identity fields must be conditionally set"
  );
  assert.ok(
    js.includes("isPrivileged") || js.includes("is_privileged"),
    "evaluation-details: must distinguish privileged viewers"
  );
  assert.ok(
    js.includes("subordinate"),
    "evaluation-details: must handle subordinate source redaction"
  );
});

test("evaluation-history returns {success:true, data:[{evaluatee_name, evaluation_date, evaluation_source}]}", () => {
  const wf = load("evaluation-history.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("success: true") && js.includes("data"),
    "evaluation-history: must return {success:true, data}"
  );
  assert.ok(
    js.includes("evaluatee_name"),
    "evaluation-history: SQL must return evaluatee_name"
  );
  assert.ok(
    js.includes("evaluation_source"),
    "evaluation-history: SQL must return evaluation_source"
  );
  assert.ok(
    js.includes("evaluation_date") || js.includes("updated_at AS evaluation_date"),
    "evaluation-history: must return evaluation_date"
  );
});

test("evaluation-history actor is the evaluator (not subject) in SQL", () => {
  const wf = load("evaluation-history.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("evaluator_id = ${actorId}") ||
    js.includes("evaluator_id ="),
    "evaluation-history: SQL WHERE clause must filter by evaluator_id"
  );
  // The query is for given evaluations, not received
  assert.ok(
    js.includes("is_self_evaluation = false"),
    "evaluation-history: must exclude self-evaluations"
  );
});

test("score-coefficients GET returns score_coefficients map keyed 1-10", () => {
  const wf = load("score-coefficients.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("score_coefficients"),
    "score-coefficients GET: must return score_coefficients"
  );
  assert.ok(
    js.includes("coeffMap") || js.includes("coefficientsMap"),
    "score-coefficients GET: must build map keyed by score level"
  );
  assert.ok(
    js.includes("is_active") && js.includes("weight"),
    "score-coefficients GET: criteria must include is_active and weight"
  );
});

test("save-score-coefficients accepts {criteria:[{id,weight,score_coefficients}]} body", () => {
  const wf = load("save-score-coefficients.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("criteria") && js.includes("score_coefficients"),
    "save-score-coefficients: must accept criteria[] with score_coefficients"
  );
  assert.ok(
    js.includes("weight"),
    "save-score-coefficients: must update criterion weight"
  );
});

// D-0822-2: weights and level coefficients stay editable until the period is
// closed. The activation freeze is removed entirely and replaced by validation.
test("save-score-coefficients has no period freeze at all", () => {
  const wf = load("save-score-coefficients.json");
  const js = allJsCode(wf);
  assert.equal(
    js.includes("ACTIVE_PERIOD_EXISTS"), false,
    "save-score-coefficients: the ACTIVE_PERIOD_EXISTS 409 must be removed entirely"
  );
  assert.equal(
    js.includes("is_active = true OR status = 'active'"), false,
    "save-score-coefficients: the freeze SELECT must be gone"
  );
  const names = allNodes(wf).map((n) => n.name);
  assert.equal(names.includes("Validate No Active Period"), false);
  assert.equal(names.includes("Check Active Period"), false);
});

// BUG-029: a zero weight or a zero coefficient is read back as 1.0 by every
// default-guarded consumer. The write path rejects them instead. The weight
// floor is 0.1 (D-0822-2 as amended, approved 2026-08-22), mirroring the
// client input min="0.1"; level coefficients stay on the plain > 0 rule.
test("save-score-coefficients enforces the 0.1 weight floor and rejects zero coefficients", () => {
  const js = allJsCode(load("save-score-coefficients.json"));
  assert.ok(js.includes("MIN_WEIGHT = 0.1"),
    "save-score-coefficients: the decided floor is the MIN_WEIGHT constant 0.1");
  assert.ok(js.includes("weight < MIN_WEIGHT"),
    "save-score-coefficients: weights below the floor must be rejected");
  assert.equal(js.includes("weight <= 0"), false,
    "save-score-coefficients: the old bare > 0 rule was replaced by the floor");
  assert.ok(js.includes("is_active"),
    "save-score-coefficients: the rejection message must point at is_active as the way to disable a criterion");
  assert.ok(js.includes("coef <= 0"), "save-score-coefficients: zero coefficient must be rejected");
  assert.ok(js.includes("Number.isFinite(weight)"));
  assert.ok(js.includes("Number.isFinite(coef)"));
  assert.ok(js.includes("INVALID_COEFFICIENT_LEVEL"),
    "save-score-coefficients: levels outside 1..10 must be rejected");
  assert.ok(js.includes("INVALID_WEIGHT") && js.includes("INVALID_COEFFICIENT"));
});

test("save-score-coefficients returns structured 422 errors for invalid rows", () => {
  const wf = load("save-score-coefficients.json");
  const buildNode = allNodes(wf).find((n) => n.name === "Build Coefficients Update");
  const js = buildNode?.parameters?.jsCode || "";
  assert.doesNotMatch(js, /throw new Error/);
  for (const errorCode of [
    "INVALID_CRITERIA_ID",
    "INVALID_WEIGHT",
    "INVALID_COEFFICIENT",
  ]) {
    assert.ok(
      js.includes(errorCode),
      `save-score-coefficients: must return ${errorCode} as a structured 422 response`
    );
  }
});

test("admin-users-data returns {users, options:{departments, grades, managers}} shape", () => {
  const wf = load("admin-users-data.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("departments") && js.includes("grades") && js.includes("managers"),
    "admin-users-data: options must include departments, grades, and managers"
  );
  assert.ok(
    js.includes("users"),
    "admin-users-data: must return users array"
  );
});

test("admin-users-data includes both work_category and is_project_participant", () => {
  const wf = load("admin-users-data.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("work_category"),
    "admin-users-data: users must include work_category"
  );
  assert.ok(
    js.includes("is_project_participant"),
    "admin-users-data: users must include is_project_participant"
  );
});

test("save-user returns {success:true, user:<row>} shape", () => {
  const wf = load("save-user.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("success: true") && js.includes("user: row"),
    "save-user: must return {success:true, user: row}"
  );
});

test("save-user allows only 'general' and 'project' work_category (H1 restriction)", () => {
  const wf = load("save-user.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("general") && js.includes("project"),
    "save-user: valid categories must include general and project"
  );
  assert.ok(
    js.includes("VALID_WORK_CATEGORIES") || js.includes("work_category"),
    "save-user: must validate work_category"
  );
  // Must NOT include hybrid or tender as valid
  assert.ok(
    !js.includes("'hybrid'") && !js.includes("'tender'"),
    "save-user: hybrid and tender must NOT be allowed (H1 restriction)"
  );
});

test("save-user atomically sets is_project_participant from work_category", () => {
  const wf = load("save-user.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("is_project_participant") && js.includes("work_category"),
    "save-user: is_project_participant must be set based on work_category"
  );
});

test("update-evaluation response includes {status:success, evaluation_id, final_score, scores_saved}", () => {
  const wf = load("update-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("status: 'success'") || js.includes('status: "success"'),
    "update-evaluation: must return status:'success'"
  );
  assert.ok(
    js.includes("evaluation_id") && js.includes("final_score") && js.includes("scores_saved"),
    "update-evaluation: response must include evaluation_id, final_score, scores_saved"
  );
  assert.ok(
    js.includes("'Evaluation updated'") || js.includes('"Evaluation updated"'),
    "update-evaluation: message must be 'Evaluation updated'"
  );
});

test("update-evaluation uses CTE with upsert+delete (not delete-first) for atomic score replacement", () => {
  const wf = load("update-evaluation.json");
  const js = allJsCode(wf);
  // Must use ON CONFLICT DO UPDATE (upsert)
  assert.ok(
    js.includes("ON CONFLICT") && js.includes("DO UPDATE"),
    "update-evaluation: must use ON CONFLICT DO UPDATE for score upsert"
  );
  // Must delete orphan scores
  assert.ok(
    js.includes("DELETE FROM performance_db.evaluation_scores"),
    "update-evaluation: must delete orphan scores not in submitted list"
  );
  // Both upsert and delete must be in a CTE (WITH clause)
  assert.ok(
    js.includes("WITH "),
    "update-evaluation: upsert+delete must be in one CTE statement"
  );
});

// ── 14. Period management contract ────────────────────────────────────────

test("manage-periods GET response shape is {status:'success', data:[]}", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("status: 'success'") || js.includes('status: "success"'),
    "manage-periods: GET response must use status:'success'"
  );
});

test("manage-periods create always starts as draft/inactive", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("'draft'") && js.includes("false"),
    "manage-periods create: period must always start as status='draft' and is_active=false"
  );
  // Must ignore client status
  assert.ok(
    js.includes("ignore client") || js.includes("always start draft") || js.includes("ignore"),
    "manage-periods create: must comment/note that client status is ignored"
  );
});

test("manage-periods create limits period_type to half_year and annual", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("half_year") && js.includes("annual"),
    "manage-periods: period_type must be limited to half_year and annual"
  );
  assert.ok(
    js.includes("VALID_TYPES") || js.includes("half_year.*annual"),
    "manage-periods: must validate period_type"
  );
});

test("manage-periods create uses atomic CTE for period + participants", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("WITH ") && js.includes("participants"),
    "manage-periods create: must use CTE with participants to ensure atomicity"
  );
  assert.ok(
    js.includes("evaluation_period_participants"),
    "manage-periods create: must create participant rows in same transaction"
  );
});

test("manage-periods activate rejects switch when active period has evaluations (409)", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("has_evaluations"),
    "manage-periods activate: must check has_evaluations on current active period"
  );
  assert.ok(
    js.includes("409") || js.includes("ACTIVE_PERIOD_HAS_EVALUATIONS"),
    "manage-periods activate: must return 409 if active period has evaluations"
  );
});

test("manage-periods activate sets both is_active and status consistently", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("is_active = true") && js.includes("status = 'active'"),
    "manage-periods activate: must set both is_active=true and status='active'"
  );
  assert.ok(
    js.includes("is_active = false") && js.includes("status = 'draft'"),
    "manage-periods activate: must set deactivated periods to is_active=false and status='draft'"
  );
});

test("manage-periods activate rejects closed target periods", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("status != 'closed'") || js.includes("status <> 'closed'"),
    "manage-periods activate: must reject closed target periods in WHERE clause"
  );
});

// ── 15. Input validation: numeric IDs and scores ─────────────────────────

test("submit-evaluation validates numeric IDs and scores with isFinite", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("Number.isFinite") || js.includes("isFinite"),
    "submit-evaluation: must use isFinite to validate numeric values"
  );
  // Must NOT use parseFloat(...) || 0 pattern
  assert.ok(
    !js.match(/parseFloat\([^)]+\)\s*\|\|\s*0/),
    "submit-evaluation: must not use parseFloat(...) || 0 fallback"
  );
});

test("update-evaluation validates numeric IDs and scores with isFinite", () => {
  const wf = load("update-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("Number.isFinite") || js.includes("isFinite"),
    "update-evaluation: must use isFinite to validate numeric values"
  );
  assert.ok(
    !js.match(/parseFloat\([^)]+\)\s*\|\|\s*0/),
    "update-evaluation: must not use parseFloat(...) || 0 fallback"
  );
});

test("self-review validates final_score with isFinite", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("Number.isFinite") || js.includes("isFinite"),
    "self-review: must validate final_score with isFinite"
  );
});

// ── 16. Create-invite uses cryptographically random token and HTTPS ────────

test("create-invite uses Node crypto module for random token", () => {
  const wf = load("create-invite.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("require('crypto')") || js.includes('require("crypto")'),
    "create-invite: must use Node crypto module"
  );
  assert.ok(
    js.includes("randomBytes") || js.includes("random"),
    "create-invite: must use randomBytes for token generation"
  );
});

test("create-invite uses EPE_FRONTEND_URL env var and validates HTTPS", () => {
  const wf = load("create-invite.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("EPE_FRONTEND_URL"),
    "create-invite: must use $env.EPE_FRONTEND_URL"
  );
  assert.ok(
    js.includes("https"),
    "create-invite: must enforce HTTPS in the registration link"
  );
});

// ── 17. admin-users-data runtime wiring ──────────────────────────────────────

test("admin-users-data MERGE reads from Query nodes, not relay Code nodes", () => {
  const wf = load("admin-users-data.json");
  const mergeNode = allNodes(wf).find((n) => n.name === "Merge and Format");
  assert.ok(mergeNode, "admin-users-data: must have a 'Merge and Format' node");
  const js = mergeNode.parameters?.jsCode || "";
  assert.ok(
    js.includes("$('Query Users')"),
    "admin-users-data Merge: must read $('Query Users') (Postgres result), not $('Load Users')"
  );
  assert.ok(
    js.includes("$('Query Depts')"),
    "admin-users-data Merge: must read $('Query Depts') (Postgres result), not $('Load Depts')"
  );
  assert.ok(
    js.includes("$('Query Grades')"),
    "admin-users-data Merge: must read $('Query Grades') (Postgres result), not $('Load Grades')"
  );
  // Ensure relay nodes are NOT referenced in the merge node
  assert.ok(
    !js.includes("$('Load Users')") &&
    !js.includes("$('Load Depts')") &&
    !js.includes("$('Load Grades')"),
    "admin-users-data Merge: must NOT reference relay Code nodes Load Users/Depts/Grades"
  );
});

test("admin-users-data options.managers derives from deduped users array", () => {
  const wf = load("admin-users-data.json");
  const mergeNode = allNodes(wf).find((n) => n.name === "Merge and Format");
  const js = mergeNode?.parameters?.jsCode || "";
  assert.ok(
    js.includes("managers") && js.includes("u.role !== 'employee'"),
    "admin-users-data: managers must filter from users array by role !== employee"
  );
  assert.ok(
    js.includes("u.full_name"),
    "admin-users-data: manager entries must use full_name"
  );
});

test("admin-users-data fan-out relay and merge nodes run once for all items", () => {
  const wf = load("admin-users-data.json");
  for (const name of ["Load Depts", "Load Grades", "Merge and Format"]) {
    const codeNode = allNodes(wf).find((n) => n.name === name);
    assert.equal(
      codeNode?.parameters?.mode,
      "runOnceForAllItems",
      `admin-users-data ${name}: must not execute once per upstream row`
    );
  }
});

// ── 18. Score range 1–10 ─────────────────────────────────────────────────────

test("submit-evaluation stores AVG of score rows, not client final_score", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("AVG(score_val::numeric)"),
    "submit-evaluation: must compute calculated_score as AVG of stored score rows"
  );
  assert.ok(
    !/VALUES \(\$\{subjectId\}, \$\{actorId\}, \$\{periodId\}, \$\{finalScore\}/.test(js),
    "submit-evaluation: must not insert client final_score into calculated_score"
  );
});

test("update-evaluation stores AVG of score rows, not client final_score", () => {
  const wf = load("update-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("AVG(score_val::numeric)"),
    "update-evaluation: must compute calculated_score as AVG of stored score rows"
  );
  assert.ok(
    !js.includes("SET calculated_score = ${finalScore}"),
    "update-evaluation: must not write client final_score into calculated_score"
  );
});

test("HR evaluation-status denominators use in-scope participants only", () => {
  const wf = load("hr-evaluation-status.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("evaluation_period_participants") && js.includes("is_in_scope"),
    "hr-evaluation-status: must join period participants and filter is_in_scope"
  );
  assert.ok(
    js.includes("in_scope_count"),
    "hr-evaluation-status: must expose the in-scope count"
  );
});

test("periods GET exposes participant and in-scope counts", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("in_scope_count") && js.includes("participant_count"),
    "manage-periods GET: must return participant_count and in_scope_count"
  );
});

test("admin-users-data exposes is_registered without password_hash", () => {
  const wf = load("admin-users-data.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("is_registered") && js.includes("password_hash IS NOT NULL"),
    "admin-users-data: must flag registered users from password_hash presence"
  );
  assert.ok(
    !/u\.password_hash(?!\s+IS\s+NOT\s+NULL)/.test(js),
    "admin-users-data: must not select password_hash itself"
  );
});

test("self-review enforces final_score 1-10 inclusive", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("SCORE_OUT_OF_RANGE") || (js.includes("< 1") && js.includes("> 10")),
    "self-review: must reject final_score outside 1-10 range"
  );
});

// D-0822-2: weighted_score is computed on the server from the subject's real
// grade coefficient. The client no longer sends it and no longer can — the
// coefficient catalogue is admin-only.
test("self-review computes weighted_score on the server, ignoring the client value", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  assert.equal(
    js.includes("body.weighted_score"), false,
    "self-review: the client-supplied weighted_score must not be read"
  );
  assert.equal(
    js.includes("INVALID_WEIGHTED_SCORE"), false,
    "self-review: the client weighted_score validation branch must be gone"
  );
  assert.ok(js.includes("grade_coefficient"), "self-review: must read the real grade coefficient");
  assert.ok(js.includes("NO_GRADE_COEFFICIENT"),
    "self-review: a subject without a grade coefficient must be refused, not defaulted to 1.0");
  assert.ok(js.includes("score_coefficients"), "self-review: must read the level coefficients");
  assert.ok(js.includes("weightedSum") && js.includes("totalWeight"),
    "self-review: must apply formula #2 (weighted sum / sum of weights)");
  assert.ok(js.includes("weighted_score: weightedScore"),
    "self-review: the computed value must be the one stored");
});

test("grade scores are validated 1-10 with 422 return (not throw) in submit-evaluation", () => {
  const wf = load("submit-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("GRADE_OUT_OF_RANGE"),
    "submit-evaluation: must return 422 GRADE_OUT_OF_RANGE for invalid grade scores"
  );
  // Must not use throw for grade validation
  assert.ok(
    !js.includes("throw new Error") || !js.includes("Invalid grade"),
    "submit-evaluation: must not throw for grade validation — use 422 return"
  );
});

test("grade scores are validated 1-10 with 422 return (not throw) in update-evaluation", () => {
  const wf = load("update-evaluation.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("GRADE_OUT_OF_RANGE"),
    "update-evaluation: must return 422 GRADE_OUT_OF_RANGE for invalid grade scores"
  );
});

test("grade scores are validated 1-10 with 422 return in self-review", () => {
  const wf = load("self-review-submit.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("GRADE_OUT_OF_RANGE"),
    "self-review: must return 422 GRADE_OUT_OF_RANGE for invalid grade scores"
  );
});

// ── 19. check-self-review uses BOTH active flags ──────────────────────────────

test("check-self-review period join requires BOTH is_active=true AND status=active", () => {
  const wf = load("check-self-review.json");
  const js = allJsCode(wf);
  assert.ok(
    js.includes("is_active = true") && js.includes("status = 'active'"),
    "check-self-review: period join must require BOTH is_active=true AND status='active'"
  );
});

// ── 20. Migration 012 period-table invariants ─────────────────────────────────

test("migration 012 validates at most one is_active=true in evaluation_periods", () => {
  const sql = readFileSync(
    join(REPO_ROOT, "migrations", "012_reconcile_evaluation_period_constraints.sql"),
    "utf8"
  );
  assert.ok(
    sql.includes("idx_evaluation_periods_single_active"),
    "migration 012: must create idx_evaluation_periods_single_active index"
  );
  assert.ok(
    sql.includes("WHERE is_active = true"),
    "migration 012: single-active index must use WHERE is_active = true predicate"
  );
});

test("migration 012 validates is_active ↔ status consistency", () => {
  const sql = readFileSync(
    join(REPO_ROOT, "migrations", "012_reconcile_evaluation_period_constraints.sql"),
    "utf8"
  );
  assert.ok(
    sql.includes("chk_evaluation_periods_active_status_consistent"),
    "migration 012: must create CHECK constraint chk_evaluation_periods_active_status_consistent"
  );
  assert.ok(
    sql.includes("(is_active = true) = (status = 'active')"),
    "migration 012: CHECK constraint must enforce is_active = (status='active')"
  );
});

test("migration 012 checks for multiple active periods in validation DO block", () => {
  const sql = readFileSync(
    join(REPO_ROOT, "migrations", "012_reconcile_evaluation_period_constraints.sql"),
    "utf8"
  );
  assert.ok(
    sql.includes("evaluation_periods") && sql.includes("active_count"),
    "migration 012: must validate active period count in evaluation_periods table"
  );
});

test("migration 012 constraint creation is idempotent (guarded by IF NOT EXISTS)", () => {
  const sql = readFileSync(
    join(REPO_ROOT, "migrations", "012_reconcile_evaluation_period_constraints.sql"),
    "utf8"
  );
  // The two new DDL items (index + constraint) must each be guarded by IF NOT EXISTS.
  // Existing index blocks use IF EXISTS with a definition check for conditional recreation.
  const ifNotExistsCount = (sql.match(/IF NOT EXISTS/g) || []).length;
  assert.ok(
    ifNotExistsCount >= 2,
    `migration 012: must have IF NOT EXISTS guards for the new index and constraint (found ${ifNotExistsCount})`
  );
});

// ── 21. Classification is editable during a running campaign (D-0822-3) ──────

test("save-user has no classification freeze — the 409 and its probe are gone", () => {
  const wf = load("save-user.json");
  const js = allJsCode(wf);
  assert.equal(js.includes("CLASSIFICATION_FROZEN"), false,
    "save-user: D-0822-3 removed the classification 409");
  assert.equal(js.includes("period_has_any_evaluation"), false,
    "save-user: the global any-evaluation probe must be gone with the freeze");
  assert.equal(js.includes("old_category"), false,
    "save-user: nothing may branch on the previous category any more");
  const names = allNodes(wf).map((n) => n.name);
  assert.equal(names.includes("Check Classification"), false,
    "save-user: the freeze probe node must be removed, not merely bypassed");
  // work_category itself is still validated and still drives is_project_participant.
  assert.ok(js.includes("INVALID_WORK_CATEGORY"));
  assert.ok(js.includes("workCategory === 'project'"));
});

// ── 22. update-evaluation CTE mutation reassertion ────────────────────────────

test("update-evaluation CTE reasserts evaluator_id=actor and period not closed inline", () => {
  const wf = load("update-evaluation.json");
  const js = allJsCode(wf);
  // The final UPDATE WHERE must include evaluator_id = actorId
  assert.ok(
    js.includes("evaluator_id = ${actorId}"),
    "update-evaluation: CTE UPDATE must reassert evaluator_id = actorId in WHERE clause"
  );
  // The inline reassertion now demands a running campaign, not merely "not closed"
  assert.ok(
    js.includes("p.status = 'active'")
      && js.includes("p.is_active = true")
      && js.includes("p.evaluation_started_at IS NOT NULL"),
    "update-evaluation: CTE UPDATE must reassert active AND started inline"
  );
  // BUG-041: the DELETE branch must not run when the reassertion selected no rows
  assert.ok(
    js.includes("AND EXISTS (SELECT 1 FROM updated_header)"),
    "update-evaluation: removed_scores must be gated on updated_header"
  );
  // 403 when reassertion fails (no rows)
  assert.ok(
    js.includes("403"),
    "update-evaluation: must return 403 when CTE reassertion fails (race condition)"
  );
});

test("update-evaluation Build Update SQL declares actorId in its own Code-node scope", () => {
  const wf = load("update-evaluation.json");
  const buildNode = allNodes(wf).find((n) => n.name === "Build Update SQL");
  const js = buildNode?.parameters?.jsCode || "";
  assert.ok(
    js.includes("const actorId = Number(prev.actor_id)"),
    "update-evaluation: Build Update SQL must declare actorId locally because n8n Code-node scopes are isolated"
  );
  assert.ok(
    js.indexOf("const actorId = Number(prev.actor_id)") < js.indexOf("evaluator_id = ${actorId}"),
    "update-evaluation: actorId must be declared before it is interpolated into SQL"
  );
});

// ── 23. get-my-manager last_evaluation_score scoped to active period ──────────

test("get-my-manager last_evaluation_score is scoped to the active period", () => {
  const wf = load("get-my-manager.json");
  const js = allJsCode(wf);
  // The last_evaluation_score subquery must join evaluation_periods with both flags
  assert.ok(
    js.includes("last_evaluation_score") &&
    js.includes("is_active = true") &&
    js.includes("status = 'active'"),
    "get-my-manager: last_evaluation_score subquery must scope to active period (both flags)"
  );
});

// ── 24. period create returns HTTP 200 ────────────────────────────────────────

test("manage-periods create returns http_status 200 (not 201)", () => {
  const wf = load("manage-periods.json");
  const js = allJsCode(wf);
  // Must have 200 for create success
  assert.ok(
    js.includes("http_status: 200"),
    "manage-periods create: success response must use http_status 200, not 201"
  );
  // Must NOT have 201
  assert.ok(
    !js.includes("http_status: 201"),
    "manage-periods create: must not use http_status 201"
  );
});

// ── 25. JS syntax: every Code-node jsCode compiles without SyntaxError ────────
// new Function(code) parses the code at construction time — SyntaxErrors are thrown
// immediately, while ReferenceErrors (e.g. undefined $) are deferred to call time,
// so this check is pure syntax without requiring an n8n runtime.

test("every Code-node jsCode compiles without SyntaxError", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    for (const n of codeNodes(wf)) {
      const code = n.parameters?.jsCode ?? "";
      if (!code) continue;
      let syntaxErr = null;
      try {
        // eslint-disable-next-line no-new-func
        new Function(code);
      } catch (e) {
        if (e instanceof SyntaxError) syntaxErr = e.message;
        // ReferenceError / TypeError at parse time would also be a problem
        else syntaxErr = `${e.constructor.name}: ${e.message}`;
      }
      assert.equal(
        syntaxErr,
        null,
        `${filename} / "${n.name}": jsCode fails to compile — ${syntaxErr}`
      );
    }
  }
});

// ── 26. Connection integrity: every source and target must name a real node ───

test("every connection source names an existing node", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const names = new Set(allNodeNames(wf));
    for (const src of Object.keys(wf.connections ?? {})) {
      assert.ok(
        names.has(src),
        `${filename}: connection source "${src}" does not match any node in this workflow`
      );
    }
  }
});

test("every connection target names an existing node", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const names = new Set(allNodeNames(wf));
    for (const [src, tdict] of Object.entries(wf.connections ?? {})) {
      for (const items of tdict.main ?? []) {
        for (const t of items) {
          assert.ok(
            names.has(t.node),
            `${filename}: connection from "${src}" targets missing node "${t.node}"`
          );
        }
      }
    }
  }
});

// ── 27. Every webhook node must have a path to a respondToWebhook node ────────
// Verifies that every HTTP trigger has a Respond outlet — catches missing branches
// introduced when new methods are added without a corresponding Respond node.

test("every webhook can reach a respondToWebhook node via connections", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const respondNames = new Set(
      allNodes(wf)
        .filter((n) => n.type === "n8n-nodes-base.respondToWebhook")
        .map((n) => n.name)
    );
    // Build forward adjacency map
    const adj = {};
    for (const [src, tdict] of Object.entries(wf.connections ?? {})) {
      for (const items of tdict.main ?? []) {
        for (const t of items) {
          (adj[src] ??= []).push(t.node);
        }
      }
    }
    // BFS from each webhook
    for (const wh of webhookNodes(wf)) {
      const visited = new Set();
      const queue = [wh.name];
      let reached = false;
      while (queue.length) {
        const cur = queue.shift();
        if (visited.has(cur)) continue;
        visited.add(cur);
        if (respondNames.has(cur)) { reached = true; break; }
        for (const nxt of adj[cur] ?? []) queue.push(nxt);
      }
      assert.ok(
        reached,
        `${filename}: webhook "${wh.name}" (${wh.parameters?.httpMethod} ${wh.parameters?.path}) has no path to any respondToWebhook node`
      );
    }
  }
});

// ── 28. No duplicate node names within a workflow ─────────────────────────────
// n8n's $('Name') selector is name-based; duplicate names make the reference
// non-deterministic and will silently read the wrong node's output at runtime.

test("no workflow contains duplicate node names", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const seen = new Set();
    for (const name of allNodeNames(wf)) {
      assert.ok(
        !seen.has(name),
        `${filename}: duplicate node name "${name}" — $('${name}') references would be ambiguous`
      );
      seen.add(name);
    }
  }
});

// ── 29. $('nodeName') cross-references resolve to real nodes ─────────────────
// Statically extract every $('…') call from jsCode and verify the referenced name
// exists in the same workflow. Catches renames/typos in the generator before they
// reach n8n and produce silent empty-data bugs.

test("every $('nodeName') in jsCode resolves to an existing node in the same workflow", () => {
  const REF = /\$\('([^']+)'\)/g;
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    const names = new Set(allNodeNames(wf));
    for (const n of codeNodes(wf)) {
      const code = n.parameters?.jsCode ?? "";
      for (const [, ref] of code.matchAll(REF)) {
        assert.ok(
          names.has(ref),
          `${filename} / "${n.name}": $('${ref}') references a node that does not exist in this workflow`
        );
      }
    }
  }
});

// ── 30. Auth Guard must not appear as a workflow trigger or definition ─────────
// executeWorkflowTrigger makes a workflow a sub-workflow callee; if present it
// would mean the generated workflow IS the Auth Guard, not a consumer of it.
// The settings check ensures data persistence remains disabled (no saveExecution* drift).

test("no generated workflow uses executeWorkflowTrigger node type", () => {
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    for (const n of allNodes(wf)) {
      assert.notEqual(
        n.type,
        "n8n-nodes-base.executeWorkflowTrigger",
        `${filename} / "${n.name}": executeWorkflowTrigger found — workflow must not be triggered by Auth Guard`
      );
    }
  }
});

test("settings object contains only the expected keys (no extra persistence flags)", () => {
  const EXPECTED_KEYS = new Set([
    "executionOrder",
    "saveDataErrorExecution",
    "saveDataSuccessExecution",
    "saveManualExecutions",
  ]);
  for (const filename of EXPECTED_FILES) {
    const wf = load(filename);
    for (const key of Object.keys(wf.settings ?? {})) {
      assert.ok(
        EXPECTED_KEYS.has(key),
        `${filename}: unexpected settings key "${key}" — may re-enable execution-data persistence`
      );
    }
  }
});

// ── 25. Reclassification (D-0822-3): applicability, additive path, soft exclusion ──

test("every write path rejects a project criterion for a currently-general subject", () => {
  for (const filename of ["submit-evaluation.json", "update-evaluation.json", "self-review-submit.json"]) {
    const js = allJsCode(load(filename));
    assert.ok(js.includes("CRITERIA_NOT_APPLICABLE"),
      `${filename}: the classification-dimension applicability 422 must exist`);
    assert.ok(js.includes("target_audience = 'project_participants'"),
      `${filename}: the predicate is target_audience='project_participants' vs the CURRENT participant flag`);
    assert.ok(js.includes("is_project_participant"),
      `${filename}: the subject's current classification must be read from the database`);
  }
});

test("submit-evaluation carries the additive path instead of a blanket duplicate 409", () => {
  const js = allJsCode(load("submit-evaluation.json"));
  assert.ok(js.includes("existing_evaluation_id"),
    "submit: the scope check must surface the existing evaluation, not merely a boolean duplicate flag");
  assert.ok(js.includes("existing_criteria_ids"),
    "submit: the already-scored criteria set is what separates additive from duplicate");
  assert.ok(js.includes("mode: 'additive'"),
    "submit: an existing evaluation with missing criteria takes the additive branch");
  assert.ok(js.includes("CRITERIA_ALREADY_SCORED"),
    "submit: any overlap with already-scored criteria is refused explicitly by name");
  assert.ok(js.includes("DUPLICATE_EVALUATION"),
    "submit: the concurrent-create race path keeps its explicit 409");
  assert.ok(js.includes("ADDITIVE_CONFLICT"),
    "submit: a raced additive maps zero DML rows to an explicit 409, never a silent success");
});

test("the additive statement gates every branch on target_eval and recomputes the score server-side", () => {
  const js = allJsCode(load("submit-evaluation.json"));
  assert.ok(js.includes("FROM target_eval te"),
    "additive: the INSERT must select from the gated target, not the raw evaluation id");
  assert.ok(js.includes("WHERE e.id IN (SELECT id FROM target_eval)"),
    "additive: the recompute UPDATE must share the same gate (the BUG-041 rule)");
  assert.ok(js.includes("FOR UPDATE OF e"),
    "additive: concurrent additives serialize on the evaluation row");
  // the recompute counts pre-existing applicable rows UNION the new values —
  // a client-sent total is never read
  assert.ok(js.includes("UNION ALL"),
    "additive: calculated_score = AVG over surviving counting rows plus the new rows");
  assert.equal(js.includes("body.final_score"), false,
    "additive: the client-sent total must never be read");
});

test("update-evaluation deletes only actively-removed applicable criteria — classification exclusion is soft", () => {
  const js = allJsCode(load("update-evaluation.json"));
  // BUG-041 gate stays
  assert.ok(js.includes("AND EXISTS (SELECT 1 FROM updated_header)"),
    "update: the destructive CTE stays gated on updated_header (BUG-041)");
  // the DELETE must skip rows excluded by the CURRENT classification
  assert.ok(/removed_scores AS \([\s\S]*?NOT EXISTS \([\s\S]*?target_audience = 'project_participants'[\s\S]*?is_project_participant = false[\s\S]*?RETURNING/.test(js),
    "update: rows for project criteria of a currently-general subject must survive an ordinary edit");
});

test("campaign-surface period resolutions accept leaf periods only (BUG-043)", () => {
  for (const filename of ["submit-evaluation.json", "self-review-submit.json",
                          "check-self-review.json", "check-evaluated.json", "get-my-manager.json"]) {
    const js = allJsCode(load(filename));
    assert.ok(js.includes("period_type <> 'annual'"),
      `${filename}: an annual period can never be the campaign period`);
    assert.ok(js.includes("parent_period_id"),
      `${filename}: a container (period with children) can never be the campaign period`);
  }
});

test("the close dataset emits project-criterion cells only for current project participants", () => {
  const js = allJsCode(load("manage-periods.json"));
  assert.ok(js.includes("cd.target_audience <> 'project_participants'")
    && js.includes("u.is_project_participant = true"),
    "close dataset: same emission predicate as the matrix, so period_results inherit it");
  assert.ok(js.includes("c.target_audience") && js.includes("criteria_data"),
    "close dataset: criteria_data must carry target_audience for the filter");
});
