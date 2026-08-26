/**
 * roleAccessHrClevel.test.js — ROLE_ACCESS_HR_CLEVEL (2026-08-26)
 *
 * C-level gains READ access to the seven admin surfaces, HR gains read access
 * to the employees roster; neither gains any write capability. These pins hold
 * the frontend half of that decision:
 *  - route gating: read-only money screens admit admin + c_level, the money
 *    WRITE screens stay admin-only;
 *  - read-only rendering: the roster and the criteria page draw no edit
 *    affordance for a non-admin;
 *  - refusal surfaces: a failed read names its reason instead of rendering an
 *    empty list (the swallowed-403 pattern of /team, BUG-012).
 * The server half is pinned in routeGuardWorkflows.test.js /
 * routeGuardDeferred.test.js / evaluationStartGate.test.js.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const read = (p) => readFileSync(join(REPO_ROOT, p), "utf8");

const app = read("src/App.jsx");
const sidebar = read("src/components/Sidebar.jsx");
const adminUsers = read("src/pages/AdminUsers.jsx");
const adminSettings = read("src/pages/AdminSettings.jsx");
const criteriaTable = read("src/components/admin/CriteriaTable.jsx");
const scoreDetailModal = read("src/components/admin/ScoreDetailModal.jsx");
const useUsers = read("src/hooks/useUsers.js");
const useCriteria = read("src/hooks/useCriteria.js");
const useScoreCalculation = read("src/hooks/useScoreCalculation.js");
const useAllEvaluations = read("src/hooks/useAllEvaluations.js");
const useEvaluationsMatrix = read("src/hooks/useEvaluationsMatrix.js");

// ── 1. Route gating ─────────────────────────────────────────────────────────

const routeElement = (path) => {
  const at = app.indexOf(`path="${path}"`);
  assert.ok(at !== -1, `route ${path} must exist`);
  // Routes are <Route path=... element={<Guard>...</Guard>} /> blocks; a fixed
  // window past the path attribute always contains the guard component.
  return app.slice(at, at + 400);
};

test("read-only money screens admit admin + c_level (ReportingRoute)", () => {
  for (const path of ["/admin/final-scores", "/admin/score-calculator"]) {
    assert.match(routeElement(path), /<ReportingRoute /, `${path} must use ReportingRoute`);
  }
});

test("money WRITE screens stay admin-only (CoefficientRoute)", () => {
  for (const path of ["/admin/scoring", "/admin/bonus-calculation"]) {
    assert.match(routeElement(path), /<CoefficientRoute /, `${path} must stay CoefficientRoute`);
  }
});

test("/admin (criteria) admits admin + c_level and redirects HR (closes the HR half of BUG-013)", () => {
  assert.match(routeElement("/admin"), /<ReportingRoute /);
});

test("/admin/users stays open to admin, c_level and hr at the route level", () => {
  assert.match(routeElement("/admin/users"), /<AdminRoute /);
});

// ── 2. No edit affordance for a non-admin ───────────────────────────────────

test("the roster's edit switch is admin-only, not 'full access'", () => {
  assert.match(adminUsers, /const canEdit = isAdminUser;/,
    "AdminUsers: canEdit must be the admin check, not the read-access check");
});

test("the criteria page draws its write controls only for admin", () => {
  assert.match(adminSettings, /const canEdit = user\?\.role === 'admin';/);
  assert.match(adminSettings, /\{canEdit && \([\s\S]{0,400}Добавить критерий/,
    "the add button must sit behind canEdit");
  assert.match(adminSettings, /canEdit=\{canEdit\}/,
    "CriteriaTable must receive canEdit");
  assert.match(criteriaTable, /\{canEdit && <th[^>]*>Действия<\/th>\}/,
    "the actions column header must be conditional");
});

test("the correction affordance includes role c_level (owner's correction to D-0826-6; D-0820-7 stands)", () => {
  // The brief's first cut removed the c_level correction control; the owner
  // corrected that before deployment: c_level keeps its corrections, so the
  // modal keeps the admin-or-c_level affordance (server still gates on
  // can_evaluate and refuses c_level_only criteria — D-0826-3).
  assert.match(scoreDetailModal, /ADMIN_ROLES\.includes\(user\.role\)/,
    "canCorrect: the admin-or-c_level check must be present");
  assert.match(scoreDetailModal, /isCLevel \|\| user\.has_manager_subordinates/,
    "canCorrect: admin/c_level or skip-level manager");
});

// ── 3. A refused or failed read says why ────────────────────────────────────

test("the roster surfaces its load error with the server's reason and a retry", () => {
  assert.match(useUsers, /setError\(err\.userMessage \|\|/,
    "useUsers: the error state must carry the server's message");
  assert.match(adminUsers, /^\s*error,$/m, "AdminUsers must consume the error");
  assert.match(adminUsers, /if \(error\) \{[\s\S]{0,1200}onClick=\{\(\) => fetchData\(\)\}/,
    "AdminUsers: the error branch must offer a retry");
});

test("the criteria page surfaces its load error instead of an empty catalogue", () => {
  assert.match(useCriteria, /setError\(err\.userMessage \|\|/);
  assert.match(adminSettings, /if \(error\) \{[\s\S]{0,1200}onClick=\{\(\) => fetchCriteria\(\)\}/);
});

test("all-evaluations and the matrix no longer swallow a failed read", () => {
  assert.match(useAllEvaluations, /setError\(err\.userMessage \|\|/);
  assert.match(useEvaluationsMatrix, /setError\(err\.userMessage \|\|/);
});

test("the score calculator no longer substitutes an empty coefficient set (BUG-042)", () => {
  assert.doesNotMatch(useScoreCalculation, /SCORE_COEFFICIENTS\)\s*\.catch\(/,
    "a failed coefficients call must not fall back to an empty list");
  assert.doesNotMatch(useScoreCalculation, /ADMIN_USERS_DATA\)\s*\.catch\(/,
    "a failed grades call must not fall back to an empty grade list");
  assert.match(useScoreCalculation, /Promise\.allSettled\(\[/);
  assert.match(useScoreCalculation, /setError\(failures\.join/);
});

// ── 4. Navigation offers the granted pages and hides the write screens ──────

test("sidebar: final-scores and score-calculator are offered to the analytics audience", () => {
  const analyticsBlock = sidebar.slice(
    sidebar.indexOf('groupId="analytics"'),
    sidebar.indexOf('groupId="admin"')
  );
  const finalScores = analyticsBlock.indexOf('to="/admin/final-scores"');
  assert.ok(finalScores !== -1, "final-scores must be in the analytics group");
  assert.equal(
    analyticsBlock.slice(0, finalScores).includes("safeUser.role === 'admin' && ("),
    false,
    "final-scores must not sit inside the admin-only fragment"
  );
  assert.match(analyticsBlock, /to="\/admin\/score-calculator"/);
  // The budget screen spends money and stays behind the admin check.
  const bonusAt = analyticsBlock.indexOf('to="/admin/bonus-calculation"');
  const adminGateAt = analyticsBlock.indexOf("safeUser.role === 'admin'");
  assert.ok(adminGateAt !== -1 && adminGateAt < bonusAt,
    "bonus-calculation must stay admin-gated");
});

test("sidebar: Критерии is offered to c_level; Периоды and Коэффициенты stay admin-only", () => {
  const adminBlock = sidebar.slice(sidebar.indexOf('groupId="admin"'));
  const criteria = adminBlock.indexOf('to="/admin" icon={Settings}');
  assert.ok(criteria !== -1, "the criteria item must exist");
  for (const adminOnly of ['to="/admin/periods"', 'to="/admin/scoring"']) {
    const at = adminBlock.indexOf(adminOnly);
    assert.ok(at !== -1, `${adminOnly} must exist`);
    const before = adminBlock.slice(0, at);
    const gate = before.lastIndexOf("safeUser.role === 'admin'");
    const criteriaBefore = before.lastIndexOf('to="/admin" icon={Settings}');
    assert.ok(gate !== -1 && gate > criteriaBefore,
      `${adminOnly} must sit behind its own admin gate`);
  }
});
