#!/usr/bin/env python3
"""
Generate inactive n8n payloads for the deferred (September) EPE API routes.

Wraps the legacy SQL/response contracts with EPE: Auth Guard. Does not
regenerate or modify the 25 launch workflows or EPE: Auth Guard itself.

Usage:
    python3 scripts/build_route_guard_deferred.py \
        --postgres-credential-id VNbfkY8IKbEzn88B \
        --guard-workflow-id L0Zr7nVa8O5YWXd3 \
        --output-directory n8n_workflows/route_guard_deferred
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from build_route_guard_workflows import (  # noqa: E402
    GUARD_WORKFLOW_PLACEHOLDER,
    POSTGRES_CREDENTIAL_PLACEHOLDER,
    connect,
    guard_input_js,
    node,
    postgres_credentials,
    respond_node,
    run_guard_node,
    workflow,
)

LEGACY_DIR = REPO / "n8n_workflows"
DUMMY_SQL = "SELECT NULL::integer AS id WHERE false"


def n8n_query(expression: str) -> str:
    """Wrap a Postgres query expression. Must not pass through an f-string `={{ }}`."""
    return "={{ " + expression + " }}"


def dummy_if(condition: str, sql_field: str = "$json.sql") -> str:
    return n8n_query(f"{condition} ? {sql_field} : '{DUMMY_SQL}'")


def legacy_node(filename: str, node_name: str) -> dict[str, Any]:
    payload = json.loads((LEGACY_DIR / filename).read_text())
    for item in payload["nodes"]:
        if item["name"] == node_name:
            return item
    raise KeyError(f"{filename}: node {node_name!r} not found")


def legacy_query(filename: str, node_name: str) -> str:
    return legacy_node(filename, node_name)["parameters"]["query"]


def guard_reject_js() -> str:
    return """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
""".strip()


# ── Shared SQL (loaded from legacy exports; not rewritten) ───────────────────

ALL_EVAL_BUILD_JS = legacy_node("API_ All-evaluation.json", "Build SQL")["parameters"]["jsCode"]
DETAILS_EXTRACT_JS = legacy_node("API_ evaluation-details-by-user.json", "Extract Params")["parameters"]["jsCode"]
DETAILS_BUILD_JS = legacy_node("API_ evaluation-details-by-user.json", "Build SQL")["parameters"]["jsCode"]
DETAILS_FORMAT_JS = legacy_node("API_ evaluation-details-by-user.json", "Format Response")["parameters"]["jsCode"]
ANALYTICS_OVERALL = legacy_query("API_ Analytics Dashboard - Optimized.json", "Get Overall Stats")
ANALYTICS_DEPT = legacy_query("API_ Analytics Dashboard - Optimized.json", "Get Department Stats")
ANALYTICS_TOP = legacy_query("API_ Analytics Dashboard - Optimized.json", "Get Top Performers")
ANALYTICS_LOW = legacy_query("API_ Analytics Dashboard - Optimized.json", "Get Low Performers")
ANALYTICS_TRENDS = legacy_query("API_ Analytics Dashboard - Optimized.json", "Get Period Trends")
ANALYTICS_FORMAT = legacy_node("API_ Analytics Dashboard - Optimized.json", "Build Response")["parameters"]["jsCode"]
MANAGER_MATRIX_SQL = legacy_query(
    "API_ Manager Subordinates Matrix.json", "Get Subordinates Matrix"
)
CRITERIA_PREP_JS = legacy_node("API_ Manage Criteria Admin V7.json", "Prep SQL")["parameters"]["jsCode"]
UPDATE_ADMIN_BUILD_JS = legacy_node("API_ Update Admin Data.json", "Build SQL")["parameters"]["jsCode"]


def js_sql_literal(sql: str) -> str:
    return json.dumps(sql)


# ── 1. GET api/admin/evaluations-matrix ──────────────────────────────────────
# One explicitly identified period per response. Default = the single period
# that is is_active AND status='active'. Optional query period_id selects a
# specific period (read-only). Writes stay on the active period only.

MATRIX_PERIOD_BUILD = f"""
{guard_reject_js()}
const request = guard.request || {{}};
const query = request.query || {{}};
const rawPeriod = query.period_id ?? query.periodId;
const requested = parseInt(rawPeriod, 10);
const hasRequested = Number.isFinite(requested) && requested > 0;
return {{
  json: {{
    ok: true,
    requested_period_id: hasRequested ? requested : null,
    sql: hasRequested
      ? `SELECT id, name, status, is_active, period_type, start_date, end_date
         FROM performance_db.evaluation_periods
         WHERE id = ${{requested}}
         LIMIT 1`
      : `SELECT id, name, status, is_active, period_type, start_date, end_date
         FROM performance_db.evaluation_periods
         WHERE is_active = true AND status = 'active'
         LIMIT 1`,
  }},
}};
""".strip()

# JS template: ${periodId} and ${actorId} are interpolated by the Code node.
MATRIX_INNER_SQL = """
WITH
manager_scores_from_subordinates AS (
  SELECT
    e.subject_id as manager_id,
    es.criteria_id,
    AVG(es.score_value) as avg_subordinate_score,
    COUNT(es.score_value) as subordinate_count
  FROM performance_db.evaluations e
  JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
  JOIN performance_db.criteria c ON es.criteria_id = c.id
  WHERE e.evaluation_source = 'subordinate'
    AND c.target_audience = 'managers_only'
    AND c.is_active = true
    AND e.period_id = ${periodId}
  GROUP BY e.subject_id, es.criteria_id
),
manager_scores_from_boss AS (
  SELECT
    e.subject_id as manager_id,
    es.criteria_id,
    es.score_value as boss_score
  FROM performance_db.evaluations e
  JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
  JOIN performance_db.criteria c ON es.criteria_id = c.id
  JOIN performance_db.users subject ON e.subject_id = subject.id
  WHERE e.evaluator_id = subject.manager_id
    AND e.is_self_evaluation = false
    AND e.evaluation_source = 'manager'
    AND c.target_audience = 'managers_only'
    AND c.is_active = true
    AND e.period_id = ${periodId}
)
SELECT
  u.id,
  u.full_name,
  u.job_title,
  u.manager_id,
  u.has_subordinates,
  u.role,
  u.can_be_evaluated,
  COALESCE(epp.is_in_scope, false) AS is_in_scope,
  (
    SELECT e.id
    FROM performance_db.evaluations e
    WHERE e.subject_id = u.id
      AND e.evaluator_id = ${actorId}
      AND e.evaluation_source = 'c_level_direct'
      AND e.period_id = ${periodId}
    LIMIT 1
  ) AS actor_c_level_evaluation_id,
  d.name as department_name,
  g.code as grade_code,
  g.description as grade_description,
  u.is_project_participant,
  json_agg(
    json_build_object(
      'criteria_id', c.id,
      'criteria_title', c.title,
      'criteria_description', c.description,
      'level_0_desc', c.level_0_desc,
      'level_1_desc', c.level_1_desc,
      'level_2_desc', c.level_2_desc,
      'level_3_desc', c.level_3_desc,
      'level_4_desc', c.level_4_desc,
      'level_5_desc', c.level_5_desc,
      'level_6_desc', c.level_6_desc,
      'level_7_desc', c.level_7_desc,
      'level_8_desc', c.level_8_desc,
      'level_9_desc', c.level_9_desc,
      'level_10_desc', c.level_10_desc,
      'selfassesment', c.selfassesment,
      'c_level_only', c.c_level_only,
      'target_audience', c.target_audience,
      'self_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.is_self_evaluation = true
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
      'manager_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.is_self_evaluation = false
          AND e.evaluation_source = 'manager'
          AND c.c_level_only = false
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
      'c_level_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.evaluation_source = 'c_level_direct'
          AND c.c_level_only = true
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
      'actor_c_level_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.evaluator_id = ${actorId}
          AND e.evaluation_source = 'c_level_direct'
          AND c.c_level_only = true
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        LIMIT 1
      ),
      'mid_level_correction', (
        SELECT sc.correction_score
        FROM performance_db.score_corrections sc
        WHERE sc.subject_id = u.id
          AND sc.criteria_id = c.id
          AND sc.correction_level = 'mid_level'
          AND sc.period_id = ${periodId}
        LIMIT 1
      ),
      'c_level_correction', (
        SELECT sc.correction_score
        FROM performance_db.score_corrections sc
        WHERE sc.subject_id = u.id
          AND sc.criteria_id = c.id
          AND sc.correction_level = 'c_level'
          AND sc.period_id = ${periodId}
        LIMIT 1
      ),
      'subordinate_avg_score', (
        SELECT ROUND(msfs.avg_subordinate_score::numeric, 1)
        FROM manager_scores_from_subordinates msfs
        WHERE msfs.manager_id = u.id
          AND msfs.criteria_id = c.id
      ),
      'subordinate_count', (
        SELECT msfs.subordinate_count
        FROM manager_scores_from_subordinates msfs
        WHERE msfs.manager_id = u.id
          AND msfs.criteria_id = c.id
      ),
      'boss_score', (
        SELECT msfb.boss_score
        FROM manager_scores_from_boss msfb
        WHERE msfb.manager_id = u.id
          AND msfb.criteria_id = c.id
      )
    ) ORDER BY
      CASE
        WHEN c.selfassesment THEN 1
        WHEN c.target_audience = 'all' AND NOT c.c_level_only THEN 2
        WHEN c.target_audience = 'project_participants' THEN 3
        WHEN c.target_audience = 'managers_only' THEN 4
        WHEN c.c_level_only THEN 5
      END,
      c.id
  ) as criteria
FROM performance_db.users u
LEFT JOIN performance_db.departments d ON u.department_id = d.id
LEFT JOIN performance_db.grades g ON u.grade_id = g.id
LEFT JOIN performance_db.evaluation_period_participants epp
  ON epp.user_id = u.id AND epp.period_id = ${periodId}
CROSS JOIN performance_db.criteria c
WHERE u.role != 'admin'
  AND c.is_active = true
GROUP BY u.id, u.full_name, u.job_title, u.manager_id, u.has_subordinates,
         u.role, u.can_be_evaluated, epp.is_in_scope,
         d.name, g.code, g.description, u.is_project_participant
ORDER BY u.full_name
""".strip()

MATRIX_QUERY_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const period = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!period) {
  return {
    json: {
      ok: false,
      no_period: true,
      period: null,
    },
  };
}
const periodId = Number(period.id);
const actorId = Number(guard.identity.id);
return {
  json: {
    ok: true,
    no_period: false,
    period,
    sql: `
""" + MATRIX_INNER_SQL + """
    `,
  },
};
""".strip()

MATRIX_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const built = $('Build Matrix Query').first().json;
if (built.http_status) {
  return { json: built };
}
if (built.no_period) {
  return {
    json: {
      http_status: 200,
      body: {
        success: true,
        data: [],
        period: null,
        campaign_active: false,
      },
    },
  };
}
const rows = $input.all().map(item => item.json).filter(item => item.id !== undefined);
const p = built.period;
const isActive = p.is_active === true || p.is_active === 'true';
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      data: rows,
      period: {
        id: Number(p.id),
        name: p.name,
        status: p.status,
        is_active: isActive,
        period_type: p.period_type,
        start_date: p.start_date,
        end_date: p.end_date,
      },
      campaign_active: isActive && p.status === 'active',
    },
  },
};
""".strip()


def build_evaluations_matrix(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("em-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/admin/evaluations-matrix",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="admin-evaluations-matrix"),
        node("em-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("em-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("em-period-build", "Build Period Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": MATRIX_PERIOD_BUILD}),
        node("em-period", "Load Period", "n8n-nodes-base.postgres",
             [220, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("em-build", "Build Matrix Query", "n8n-nodes-base.code",
             [440, 0], {"jsCode": MATRIX_QUERY_BUILD}),
        node("em-query", "Execute Query", "n8n-nodes-base.postgres",
             [660, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("em-format", "Format Response", "n8n-nodes-base.code",
             [880, 0], {"jsCode": MATRIX_FORMAT}),
        respond_node("em-respond", "Respond", [1100, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Period Query"),
        "Build Period Query": connect("Load Period"),
        "Load Period": connect("Build Matrix Query"),
        "Build Matrix Query": connect("Execute Query"),
        "Execute Query": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: evaluations-matrix", nodes_list, connections)


# ── 2. GET api/admin/all-evaluations ─────────────────────────────────────────
# Same period bind as evaluations-matrix. manager_evaluations_given is
# DISTINCT ON (evaluator_id) so a second period cannot multiply rows.

ALL_EVAL_INNER_SQL = """
WITH latest_evaluations AS (
  SELECT DISTINCT ON (e.subject_id, e.is_self_evaluation, e.evaluation_source)
    e.id as evaluation_id,
    e.subject_id,
    e.evaluator_id,
    e.calculated_score,
    e.updated_at,
    e.is_self_evaluation,
    e.evaluation_source
  FROM performance_db.evaluations e
  WHERE e.period_id = ${periodId}
  ORDER BY e.subject_id, e.is_self_evaluation, e.evaluation_source, e.updated_at DESC
),
manager_evaluations_given AS (
  SELECT DISTINCT ON (e.evaluator_id)
    e.evaluator_id,
    e.subject_id as manager_id,
    mgr.full_name as manager_name,
    e.calculated_score,
    e.updated_at,
    e.id as evaluation_id
  FROM performance_db.evaluations e
  JOIN performance_db.users mgr ON e.subject_id = mgr.id
  WHERE e.evaluation_source = 'subordinate'
    AND e.period_id = ${periodId}
  ORDER BY e.evaluator_id, e.updated_at DESC
),
subordinates_rating AS (
  SELECT
    e.subject_id as manager_id,
    ROUND(AVG(e.calculated_score), 2) as avg_score,
    COUNT(*) as ratings_count,
    MAX(e.updated_at) as last_date
  FROM performance_db.evaluations e
  WHERE e.evaluation_source = 'subordinate'
    AND e.is_self_evaluation = false
    AND e.period_id = ${periodId}
  GROUP BY e.subject_id
),
subordinates_evaluated AS (
  SELECT
    e.evaluator_id,
    COUNT(DISTINCT e.subject_id) as evaluated_count
  FROM performance_db.evaluations e
  WHERE e.evaluation_source = 'manager'
    AND e.is_self_evaluation = false
    AND e.period_id = ${periodId}
  GROUP BY e.evaluator_id
),
subordinates_total AS (
  SELECT
    manager_id,
    COUNT(*) as total_count
  FROM performance_db.users
  WHERE manager_id IS NOT NULL
  GROUP BY manager_id
)
SELECT
  u.id,
  u.full_name,
  u.job_title,
  u.role,
  u.is_project_participant,
  u.has_subordinates,
  u.manager_id,
  mgr.full_name as manager_name,
  d.name as department_name,
  le_self.calculated_score as self_score,
  le_self.updated_at as self_date,
  le_self.evaluation_id as self_eval_id,
  le_manager.calculated_score as manager_score,
  le_manager.updated_at as manager_date,
  le_manager.evaluation_id as manager_eval_id,
  meg.calculated_score as gave_to_manager_score,
  meg.updated_at as gave_to_manager_date,
  meg.evaluation_id as gave_to_manager_eval_id,
  meg.manager_name as evaluated_manager_name,
  sr.avg_score as from_subordinates_score,
  sr.ratings_count as from_subordinates_count,
  sr.last_date as from_subordinates_date,
  COALESCE(se.evaluated_count, 0) as subordinates_evaluated,
  COALESCE(st.total_count, 0) as subordinates_total
FROM performance_db.users u
LEFT JOIN performance_db.users mgr ON u.manager_id = mgr.id
LEFT JOIN performance_db.departments d ON u.department_id = d.id
LEFT JOIN latest_evaluations le_self
  ON u.id = le_self.subject_id AND le_self.is_self_evaluation = true
LEFT JOIN latest_evaluations le_manager
  ON u.id = le_manager.subject_id
  AND le_manager.is_self_evaluation = false
  AND le_manager.evaluation_source = 'manager'
LEFT JOIN manager_evaluations_given meg ON u.id = meg.evaluator_id
LEFT JOIN subordinates_rating sr ON u.id = sr.manager_id
LEFT JOIN subordinates_evaluated se ON u.id = se.evaluator_id
LEFT JOIN subordinates_total st ON u.id = st.manager_id
WHERE u.role NOT IN ('c_level', 'admin')
ORDER BY u.full_name
""".strip()

ALL_EVAL_QUERY_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const period = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!period) {
  return { json: { ok: false, no_period: true, period: null } };
}
const periodId = Number(period.id);
return {
  json: {
    ok: true,
    no_period: false,
    period,
    sql: `
""" + ALL_EVAL_INNER_SQL + """
    `,
  },
};
""".strip()

ALL_EVAL_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const built = $('Build SQL').first().json;
if (built.http_status) {
  return { json: built };
}
if (built.no_period) {
  return {
    json: {
      http_status: 200,
      body: { success: true, data: [], period: null, campaign_active: false },
    },
  };
}
const employees = $input.all().map(item => item.json).filter(item => item.id !== undefined);
const p = built.period;
const isActive = p.is_active === true || p.is_active === 'true';
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      data: employees,
      period: {
        id: Number(p.id),
        name: p.name,
        status: p.status,
        is_active: isActive,
        period_type: p.period_type,
        start_date: p.start_date,
        end_date: p.end_date,
      },
      campaign_active: isActive && p.status === 'active',
    },
  },
};
""".strip()


def build_all_evaluations(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("ae-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/admin/all-evaluations",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="admin-all-evaluations-webhook"),
        node("ae-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("ae-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("ae-period-build", "Build Period Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": MATRIX_PERIOD_BUILD}),
        node("ae-period", "Load Period", "n8n-nodes-base.postgres",
             [220, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("ae-build", "Build SQL", "n8n-nodes-base.code",
             [440, 0], {"jsCode": ALL_EVAL_QUERY_BUILD}),
        node("ae-query", "Execute Query", "n8n-nodes-base.postgres",
             [660, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("ae-format", "Format Response", "n8n-nodes-base.code",
             [880, 0], {"jsCode": ALL_EVAL_FORMAT}),
        respond_node("ae-respond", "Respond", [1100, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Period Query"),
        "Build Period Query": connect("Load Period"),
        "Load Period": connect("Build SQL"),
        "Build SQL": connect("Execute Query"),
        "Execute Query": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: All-evaluation", nodes_list, connections)


# ── 3. GET api/admin/evaluation-details-by-user ──────────────────────────────
# user_id is the resource (whose dossier), not the actor.
# detail_type is real: it selects which half of the dossier runs.

DETAILS_ALLOWED = (
    "all",
    "self",
    "received_from_manager",
    "from_subordinates",
    "gave_to_manager",
    "gave_to_subordinates",
)

DETAILS_EXTRACT = f"""
{guard_reject_js()}
const query = guard.request.query || {{}};
const userId = query.user_id;
const detailType = String(query.detail_type || 'all');
const evaluationId = query.evaluation_id;
const rawPeriod = query.period_id ?? query.periodId;
const requested = parseInt(rawPeriod, 10);
const hasRequested = Number.isFinite(requested) && requested > 0;
const allowed = {json.dumps(list(DETAILS_ALLOWED))};
if (!userId) {{
  return {{
    json: {{
      http_status: 422,
      body: {{ success: false, error: 'INVALID_QUERY', message: 'user_id is required' }},
    }},
  }};
}}
if (!allowed.includes(detailType)) {{
  return {{
    json: {{
      http_status: 422,
      body: {{
        success: false,
        error: 'INVALID_QUERY',
        message: 'detail_type must be one of: ' + allowed.join(', '),
      }},
    }},
  }};
}}
return {{
  json: {{
    ok: true,
    user_id: parseInt(userId, 10),
    detail_type: detailType,
    evaluation_id: evaluationId ? parseInt(evaluationId, 10) : null,
    requested_period_id: hasRequested ? requested : null,
    sql: hasRequested
      ? `SELECT id, name, status, is_active, period_type, start_date, end_date
         FROM performance_db.evaluation_periods
         WHERE id = ${{requested}}
         LIMIT 1`
      : `SELECT id, name, status, is_active, period_type, start_date, end_date
         FROM performance_db.evaluation_periods
         WHERE is_active = true AND status = 'active'
         LIMIT 1`,
  }},
}};
""".strip()

DETAILS_BUILD = """
const prev = $('Extract Params').first().json;
if (prev.http_status) {
  return { json: prev };
}
const period = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!period) {
  return { json: { ok: false, no_period: true, period: null, detail_type: prev.detail_type } };
}
const userId = Number(prev.user_id);
const periodId = Number(period.id);
const detailType = prev.detail_type;
const evaluationId = prev.evaluation_id;
const evalFilter = Number.isFinite(evaluationId) && evaluationId > 0
  ? ` AND e.id = ${evaluationId}`
  : '';

const columns = `
    e.id as evaluation_id,
    e.subject_id,
    e.evaluator_id,
    e.calculated_score,
    e.updated_at,
    e.is_self_evaluation,
    e.evaluation_source,
    evaluator.full_name as evaluator_name,
    evaluator.role as evaluator_role,
    subject.full_name as subject_name,
    subject.job_title as subject_job_title,
    c.id as criteria_id,
    c.title as criteria_title,
    c.selfassesment,
    c.c_level_only,
    c.target_audience,
    es.score_value,
    es.comment
`;
const joins = `
  FROM performance_db.evaluations e
  LEFT JOIN performance_db.users evaluator ON e.evaluator_id = evaluator.id
  LEFT JOIN performance_db.users subject ON e.subject_id = subject.id
  LEFT JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
  LEFT JOIN performance_db.criteria c ON es.criteria_id = c.id
`;

let subjectWhere = `e.subject_id = ${userId} AND e.period_id = ${periodId}${evalFilter}`;
if (detailType === 'self') {
  subjectWhere += ` AND e.is_self_evaluation = true`;
} else if (detailType === 'received_from_manager') {
  subjectWhere += ` AND e.is_self_evaluation = false AND e.evaluation_source IN ('manager', 'c_level_direct')`;
} else if (detailType === 'from_subordinates') {
  subjectWhere += ` AND e.evaluation_source = 'subordinate'`;
}

let evaluatorWhere = `e.evaluator_id = ${userId} AND e.is_self_evaluation = false AND e.period_id = ${periodId}${evalFilter}`;
if (detailType === 'gave_to_manager') {
  evaluatorWhere += ` AND e.evaluation_source = 'subordinate'`;
} else if (detailType === 'gave_to_subordinates') {
  evaluatorWhere += ` AND e.evaluation_source IN ('manager', 'c_level_direct')`;
}

const wantSubject = ['all', 'self', 'received_from_manager', 'from_subordinates'].includes(detailType);
const wantEvaluator = ['all', 'gave_to_manager', 'gave_to_subordinates'].includes(detailType);

const sqlAsSubject = `
  SELECT 'as_subject' as query_type, ${columns}
  ${joins}
  WHERE ${subjectWhere}
  ORDER BY e.updated_at DESC, c.id
`;
const sqlAsEvaluator = `
  SELECT 'as_evaluator' as query_type, ${columns}
  ${joins}
  WHERE ${evaluatorWhere}
  ORDER BY e.updated_at DESC, c.id
`;

let sql;
if (wantSubject && wantEvaluator) {
  sql = `(${sqlAsSubject}) UNION ALL (${sqlAsEvaluator})`;
} else if (wantSubject) {
  sql = sqlAsSubject;
} else {
  sql = sqlAsEvaluator;
}

return {
  json: {
    ok: true,
    no_period: false,
    period,
    detail_type: detailType,
    sql,
  },
};
""".strip()

DETAILS_FORMAT = """
const prev = $('Extract Params').first().json;
if (prev.http_status) {
  return { json: prev };
}
const built = $('Build SQL').first().json;
if (built.http_status) {
  return { json: built };
}
const empty = {
  self_evaluation: null,
  manager_evaluations: [],
  c_level_evaluations: [],
  subordinate_evaluations: [],
  evaluation_to_manager: null,
  evaluations_to_subordinates: [],
};
function periodBody(p) {
  if (!p) return { period: null, campaign_active: false };
  const isActive = p.is_active === true || p.is_active === 'true';
  return {
    period: {
      id: Number(p.id),
      name: p.name,
      status: p.status,
      is_active: isActive,
      period_type: p.period_type,
      start_date: p.start_date,
      end_date: p.end_date,
    },
    campaign_active: isActive && p.status === 'active',
  };
}
if (built.no_period) {
  return {
    json: {
      http_status: 200,
      body: {
        success: true,
        data: empty,
        detail_type: built.detail_type || prev.detail_type || 'all',
        ...periodBody(null),
      },
    },
  };
}
const rows = $input.all().map(item => item.json);
const evaluations = {};
rows.forEach(row => {
  const evalId = row.evaluation_id;
  if (!evalId) return;
  if (!evaluations[evalId]) {
    evaluations[evalId] = {
      evaluation_id: evalId,
      query_type: row.query_type,
      evaluator_id: row.evaluator_id,
      evaluator_name: row.evaluator_name,
      evaluator_role: row.evaluator_role,
      subject_id: row.subject_id,
      subject_name: row.subject_name,
      subject_job_title: row.subject_job_title,
      calculated_score: row.calculated_score,
      updated_at: row.updated_at,
      is_self_evaluation: row.is_self_evaluation,
      evaluation_source: row.evaluation_source || 'manager',
      criteria: [],
    };
  }
  if (row.criteria_id) {
    evaluations[evalId].criteria.push({
      criteria_id: row.criteria_id,
      criteria_title: row.criteria_title,
      score_value: row.score_value,
      comment: row.comment,
      selfassesment: row.selfassesment,
      c_level_only: row.c_level_only,
      target_audience: row.target_audience,
    });
  }
});
const result = {
  self_evaluation: null,
  manager_evaluations: [],
  c_level_evaluations: [],
  subordinate_evaluations: [],
  evaluation_to_manager: null,
  evaluations_to_subordinates: [],
};
Object.values(evaluations).forEach(evaluation => {
  if (evaluation.query_type === 'as_subject') {
    if (evaluation.is_self_evaluation) {
      result.self_evaluation = evaluation;
    } else if (evaluation.evaluation_source === 'subordinate') {
      result.subordinate_evaluations.push(evaluation);
    } else if (evaluation.evaluation_source === 'c_level_direct'
        || evaluation.evaluator_role === 'c_level'
        || evaluation.evaluator_role === 'admin') {
      result.c_level_evaluations.push(evaluation);
    } else {
      result.manager_evaluations.push(evaluation);
    }
  } else if (evaluation.query_type === 'as_evaluator') {
    if (evaluation.evaluation_source === 'subordinate') {
      result.evaluation_to_manager = evaluation;
    } else if (evaluation.evaluation_source === 'manager' || evaluation.evaluation_source === 'c_level_direct') {
      result.evaluations_to_subordinates.push(evaluation);
    }
  }
});
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      data: result,
      detail_type: built.detail_type || prev.detail_type || 'all',
      ...periodBody(built.period),
    },
  },
};
""".strip()


def build_details_by_user(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("du-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/admin/evaluation-details-by-user",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="admin-evaluation-details-by-user"),
        node("du-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("du-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("du-extract", "Extract Params", "n8n-nodes-base.code",
             [0, 0], {"jsCode": DETAILS_EXTRACT}),
        node("du-period", "Load Period", "n8n-nodes-base.postgres",
             [220, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("du-build", "Build SQL", "n8n-nodes-base.code",
             [440, 0], {"jsCode": DETAILS_BUILD}),
        node("du-query", "Execute Query", "n8n-nodes-base.postgres",
             [660, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("du-format", "Format Response", "n8n-nodes-base.code",
             [880, 0], {"jsCode": DETAILS_FORMAT}),
        respond_node("du-respond", "Respond", [1100, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Extract Params"),
        "Extract Params": connect("Load Period"),
        "Load Period": connect("Build SQL"),
        "Build SQL": connect("Execute Query"),
        "Execute Query": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: evaluation-details-by-user", nodes_list, connections)


# ── 4. GET api/analytics ─────────────────────────────────────────────────────
# Same AVG formulas as the legacy queries. The only change is period bind:
# every aggregate is restricted to the named period. period_trends therefore
# has at most one row (the shown period), not a mixed history.

ANALYTICS_OVERALL_SQL = """
SELECT
  COUNT(DISTINCT e.id) as total_evaluations,
  COALESCE(ROUND(AVG(e.calculated_score)::numeric, 2), 0) as company_avg_score,
  COUNT(DISTINCT e.subject_id) as total_employees,
  COUNT(DISTINCT e.evaluator_id) as active_evaluators
FROM performance_db.evaluations e
WHERE e.calculated_score IS NOT NULL
  AND e.period_id = ${periodId}
""".strip()

ANALYTICS_DEPT_SQL = """
SELECT
  COALESCE(d.name, 'Без отдела') as department,
  COUNT(e.id) as evaluations_count,
  ROUND(AVG(e.calculated_score)::numeric, 2) as avg_score
FROM performance_db.evaluations e
INNER JOIN performance_db.users u ON e.subject_id = u.id
LEFT JOIN performance_db.departments d ON u.department_id = d.id
WHERE e.calculated_score IS NOT NULL
  AND e.period_id = ${periodId}
GROUP BY d.name
ORDER BY avg_score DESC NULLS LAST
""".strip()

ANALYTICS_TOP_SQL = """
WITH latest_scores AS (
  SELECT DISTINCT ON (subject_id)
    subject_id,
    calculated_score,
    updated_at
  FROM performance_db.evaluations
  WHERE calculated_score IS NOT NULL
    AND period_id = ${periodId}
  ORDER BY subject_id, updated_at DESC
)
SELECT
  u.id,
  u.full_name,
  COALESCE(u.job_title, 'Не указано') as job_title,
  COALESCE(d.name, 'Без отдела') as department,
  ls.calculated_score as score
FROM latest_scores ls
INNER JOIN performance_db.users u ON ls.subject_id = u.id
LEFT JOIN performance_db.departments d ON u.department_id = d.id
ORDER BY ls.calculated_score DESC
LIMIT 10
""".strip()

ANALYTICS_LOW_SQL = """
WITH latest_scores AS (
  SELECT DISTINCT ON (subject_id)
    subject_id,
    calculated_score,
    updated_at
  FROM performance_db.evaluations
  WHERE calculated_score IS NOT NULL
    AND period_id = ${periodId}
  ORDER BY subject_id, updated_at DESC
)
SELECT
  u.id,
  u.full_name,
  COALESCE(u.job_title, 'Не указано') as job_title,
  COALESCE(d.name, 'Без отдела') as department,
  ls.calculated_score as score
FROM latest_scores ls
INNER JOIN performance_db.users u ON ls.subject_id = u.id
LEFT JOIN performance_db.departments d ON u.department_id = d.id
ORDER BY ls.calculated_score ASC
LIMIT 3
""".strip()

ANALYTICS_TRENDS_SQL = """
SELECT
  ep.name as period_name,
  COUNT(e.id) as evaluations_count,
  ROUND(AVG(e.calculated_score)::numeric, 2) as avg_score,
  TO_CHAR(ep.start_date, 'YYYY-MM-DD') as start_date
FROM performance_db.evaluations e
INNER JOIN performance_db.evaluation_periods ep ON e.period_id = ep.id
WHERE e.calculated_score IS NOT NULL
  AND e.period_id = ${periodId}
GROUP BY ep.id, ep.name, ep.start_date
ORDER BY ep.start_date DESC
LIMIT 12
""".strip()

ANALYTICS_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const period = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!period) {
  return { json: { ok: false, no_period: true, period: null } };
}
const periodId = Number(period.id);
return {
  json: {
    ok: true,
    no_period: false,
    period,
    sql_overall: `
""" + ANALYTICS_OVERALL_SQL + """
    `,
    sql_dept: `
""" + ANALYTICS_DEPT_SQL + """
    `,
    sql_top: `
""" + ANALYTICS_TOP_SQL + """
    `,
    sql_low: `
""" + ANALYTICS_LOW_SQL + """
    `,
    sql_trends: `
""" + ANALYTICS_TRENDS_SQL + """
    `,
  },
};
""".strip()


def _wrap_analytics_format() -> str:
    return """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const built = $('Build Analytics Plan').first().json;
if (built.http_status) {
  return { json: built };
}
function periodBody(p) {
  if (!p) return { period: null, campaign_active: false };
  const isActive = p.is_active === true || p.is_active === 'true';
  return {
    period: {
      id: Number(p.id),
      name: p.name,
      status: p.status,
      is_active: isActive,
      period_type: p.period_type,
      start_date: p.start_date,
      end_date: p.end_date,
    },
    campaign_active: isActive && p.status === 'active',
  };
}
const emptyOverall = {
  total_evaluations: 0,
  company_avg_score: 0,
  total_employees: 0,
  active_evaluators: 0,
};
if (built.no_period) {
  return {
    json: {
      http_status: 200,
      body: {
        success: true,
        data: {
          overall: emptyOverall,
          departments: [],
          top_performers: [],
          low_performers: [],
          period_trends: [],
        },
        ...periodBody(null),
      },
    },
  };
}
function uniqueBy(items, key) {
  const seen = new Set();
  const out = [];
  for (const item of items || []) {
    const row = item.json || {};
    const id = row[key];
    if (id === undefined || seen.has(String(id))) continue;
    seen.add(String(id));
    out.push(row);
  }
  return out;
}
const overallItems = $('Get Overall Stats').all();
const overall = overallItems && overallItems.length > 0 && overallItems[0].json.total_evaluations !== undefined
  ? overallItems[0].json
  : emptyOverall;
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      data: {
        overall,
        departments: uniqueBy($('Get Department Stats').all(), 'department'),
        top_performers: uniqueBy($('Get Top Performers').all(), 'id'),
        low_performers: uniqueBy($('Get Low Performers').all(), 'id'),
        period_trends: uniqueBy($('Get Period Trends').all(), 'period_name'),
      },
      ...periodBody(built.period),
    },
  },
};
""".strip()


def build_analytics(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("an-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/analytics",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="analytics-dashboard-v2"),
        node("an-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("an-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("an-period-build", "Build Period Query", "n8n-nodes-base.code",
             [-80, 0], {"jsCode": MATRIX_PERIOD_BUILD}),
        node("an-period", "Load Period", "n8n-nodes-base.postgres",
             [80, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("an-build", "Build Analytics Plan", "n8n-nodes-base.code",
             [260, 0], {"jsCode": ANALYTICS_BUILD}),
        node("an-overall", "Get Overall Stats", "n8n-nodes-base.postgres",
             [480, -200],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Analytics Plan').first().json.ok", "$('Build Analytics Plan').first().json.sql_overall"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("an-dept", "Get Department Stats", "n8n-nodes-base.postgres",
             [480, -100],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Analytics Plan').first().json.ok", "$('Build Analytics Plan').first().json.sql_dept"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("an-top", "Get Top Performers", "n8n-nodes-base.postgres",
             [480, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Analytics Plan').first().json.ok", "$('Build Analytics Plan').first().json.sql_top"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("an-low", "Get Low Performers", "n8n-nodes-base.postgres",
             [480, 100],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Analytics Plan').first().json.ok", "$('Build Analytics Plan').first().json.sql_low"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("an-trends", "Get Period Trends", "n8n-nodes-base.postgres",
             [480, 200],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Analytics Plan').first().json.ok", "$('Build Analytics Plan').first().json.sql_trends"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("an-format", "Build Response", "n8n-nodes-base.code",
             [720, 0], {"jsCode": _wrap_analytics_format()}),
        respond_node("an-respond", "Respond", [940, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Period Query"),
        "Build Period Query": connect("Load Period"),
        "Load Period": connect("Build Analytics Plan"),
        "Build Analytics Plan": connect("Get Overall Stats"),
        "Get Overall Stats": connect("Get Department Stats"),
        "Get Department Stats": connect("Get Top Performers"),
        "Get Top Performers": connect("Get Low Performers"),
        "Get Low Performers": connect("Get Period Trends"),
        "Get Period Trends": connect("Build Response"),
        "Build Response": connect("Respond"),
    }
    return workflow("API: Analytics Dashboard - Optimized", nodes_list, connections)


# ── 5. GET get-admin-data ────────────────────────────────────────────────────

ADMIN_DATA_BUILD = f"""
{guard_reject_js()}
return {{
  json: {{
    ok: true,
    sql_grades: {js_sql_literal("SELECT * FROM performance_db.grades ORDER BY id ASC;")},
    sql_settings: {js_sql_literal("SELECT * FROM performance_db.global_settings ORDER BY setting_key ASC;")},
  }},
}};
""".strip()

ADMIN_DATA_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const grades = $('Get Grades').all().map(item => item.json).filter(item => item.id !== undefined);
const settings = $('Get Settings').all().map(item => item.json).filter(item => item.setting_key !== undefined);
return {
  json: {
    http_status: 200,
    body: { grades, settings },
  },
};
""".strip()


def build_get_admin_data(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("gad-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "get-admin-data",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="8de1bf42-37f2-436c-9150-66dab3c43fb0"),
        node("gad-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("gad-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("gad-build", "Build Admin Data Queries", "n8n-nodes-base.code",
             [0, 0], {"jsCode": ADMIN_DATA_BUILD}),
        node("gad-grades", "Get Grades", "n8n-nodes-base.postgres",
             [250, -80],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Admin Data Queries').first().json.ok", "$('Build Admin Data Queries').first().json.sql_grades"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("gad-settings", "Get Settings", "n8n-nodes-base.postgres",
             [250, 80],
             {"operation": "executeQuery",
              "query": dummy_if("$('Build Admin Data Queries').first().json.ok", "$('Build Admin Data Queries').first().json.sql_settings"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("gad-format", "Combine Data", "n8n-nodes-base.code",
             [500, 0], {"jsCode": ADMIN_DATA_FORMAT}),
        respond_node("gad-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Admin Data Queries"),
        "Build Admin Data Queries": connect("Get Grades"),
        "Get Grades": connect("Get Settings"),
        "Get Settings": connect("Combine Data"),
        "Combine Data": connect("Respond"),
    }
    return workflow("API: Get Admin Data Fixed", nodes_list, connections)


# ── 6. GET api/manager-subordinates-matrix ───────────────────────────────────

MANAGER_ACCESS = f"""
{guard_reject_js()}
const actorId = Number(guard.identity.id);
const role = String(guard.identity.role || '');
// Client manager_id is ignored. Actor is the only manager_id used.
return {{
  json: {{
    ok: true,
    actor_id: actorId,
    role,
    sql: `
      SELECT
        u.id,
        u.role,
        EXISTS(
          SELECT 1 FROM performance_db.users sub
          WHERE sub.manager_id = u.id AND sub.has_subordinates = true
        ) AS has_manager_subordinates
      FROM performance_db.users u
      WHERE u.id = ${{actorId}}
    `,
  }},
}};
""".strip()

MANAGER_VERIFY = """
const prev = $('Build Access Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
const role = prev.role;
if (!row) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'NOT_FOUND', message: 'Actor not found' },
    },
  };
}
if (role === 'manager' && !row.has_manager_subordinates) {
  return {
    json: {
      http_status: 403,
      body: {
        success: false,
        error: 'OWNERSHIP_FORBIDDEN',
        message: 'You must have manager subordinates to access this feature',
      },
    },
  };
}
return {
  json: {
    ok: true,
    actor_id: prev.actor_id,
    role,
  },
};
""".strip()

MANAGER_PERIOD_BUILD = f"""
const prev = $('Verify Access').first().json;
if (prev.http_status) {{
  return {{ json: prev }};
}}
const guard = $('Run Auth Guard').first().json;
const request = guard.request || {{}};
const query = request.query || {{}};
const rawPeriod = query.period_id ?? query.periodId;
const requested = parseInt(rawPeriod, 10);
const hasRequested = Number.isFinite(requested) && requested > 0;
return {{
  json: {{
    ok: true,
    actor_id: prev.actor_id,
    requested_period_id: hasRequested ? requested : null,
    sql: hasRequested
      ? `SELECT id, name, status, is_active, period_type, start_date, end_date
         FROM performance_db.evaluation_periods
         WHERE id = ${{requested}}
         LIMIT 1`
      : `SELECT id, name, status, is_active, period_type, start_date, end_date
         FROM performance_db.evaluation_periods
         WHERE is_active = true AND status = 'active'
         LIMIT 1`,
  }},
}};
""".strip()

MANAGER_MATRIX_INNER_SQL = """
WITH
subordinate_managers AS (
  SELECT id FROM performance_db.users
  WHERE manager_id = ${actorId} AND has_subordinates = true
),
subordinates_of_managers AS (
  SELECT u.*
  FROM performance_db.users u
  WHERE u.manager_id IN (SELECT id FROM subordinate_managers)
)
SELECT
  u.id,
  u.full_name,
  u.job_title,
  u.manager_id,
  mgr.full_name as manager_name,
  d.name as department_name,
  g.code as grade_code,
  g.description as grade_description,
  u.is_project_participant,
  json_agg(
    json_build_object(
      'criteria_id', c.id,
      'criteria_title', c.title,
      'criteria_description', c.description,
      'level_0_desc', c.level_0_desc,
      'level_1_desc', c.level_1_desc,
      'level_2_desc', c.level_2_desc,
      'level_3_desc', c.level_3_desc,
      'level_4_desc', c.level_4_desc,
      'level_5_desc', c.level_5_desc,
      'level_6_desc', c.level_6_desc,
      'level_7_desc', c.level_7_desc,
      'level_8_desc', c.level_8_desc,
      'level_9_desc', c.level_9_desc,
      'level_10_desc', c.level_10_desc,
      'selfassesment', c.selfassesment,
      'c_level_only', c.c_level_only,
      'target_audience', c.target_audience,
      'self_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.is_self_evaluation = true
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
      'manager_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.is_self_evaluation = false
          AND e.evaluation_source = 'manager'
          AND c.c_level_only = false
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
      'mid_level_correction', (
        SELECT sc.correction_score
        FROM performance_db.score_corrections sc
        WHERE sc.subject_id = u.id
          AND sc.criteria_id = c.id
          AND sc.correction_level = 'mid_level'
          AND sc.period_id = ${periodId}
        LIMIT 1
      ),
      'c_level_correction', (
        SELECT sc.correction_score
        FROM performance_db.score_corrections sc
        WHERE sc.subject_id = u.id
          AND sc.criteria_id = c.id
          AND sc.correction_level = 'c_level'
          AND sc.period_id = ${periodId}
        LIMIT 1
      )
    ) ORDER BY
      CASE
        WHEN c.selfassesment THEN 1
        WHEN c.target_audience = 'all' AND NOT c.c_level_only THEN 2
        WHEN c.target_audience = 'project_participants' THEN 3
        WHEN c.c_level_only THEN 4
      END,
      c.id
  ) as criteria
FROM subordinates_of_managers u
LEFT JOIN performance_db.departments d ON u.department_id = d.id
LEFT JOIN performance_db.grades g ON u.grade_id = g.id
LEFT JOIN performance_db.users mgr ON u.manager_id = mgr.id
CROSS JOIN performance_db.criteria c
WHERE c.is_active = true
  AND c.c_level_only = false
GROUP BY u.id, u.full_name, u.job_title, u.manager_id, mgr.full_name,
         d.name, g.code, g.description, u.is_project_participant
ORDER BY mgr.full_name, u.full_name
""".strip()

MANAGER_QUERY_BUILD = """
const prev = $('Build Period Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const period = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!period) {
  return { json: { ok: false, no_period: true, period: null } };
}
const periodId = Number(period.id);
const actorId = Number(prev.actor_id);
return {
  json: {
    ok: true,
    no_period: false,
    period,
    sql: `
""" + MANAGER_MATRIX_INNER_SQL + """
    `,
  },
};
""".strip()

MANAGER_FORMAT = """
const access = $('Verify Access').first().json;
if (access.http_status) {
  return { json: access };
}
const built = $('Build Matrix Query').first().json;
if (built.http_status) {
  return { json: built };
}
if (built.no_period) {
  return {
    json: {
      http_status: 200,
      body: { success: true, data: [], period: null, campaign_active: false },
    },
  };
}
const rows = $input.all().map(item => item.json).filter(item => item.id !== undefined);
const p = built.period;
const isActive = p.is_active === true || p.is_active === 'true';
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      data: rows,
      period: {
        id: Number(p.id),
        name: p.name,
        status: p.status,
        is_active: isActive,
        period_type: p.period_type,
        start_date: p.start_date,
        end_date: p.end_date,
      },
      campaign_active: isActive && p.status === 'active',
    },
  },
};
""".strip()


def build_manager_matrix(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("mm-options", "Webhook OPTIONS", "n8n-nodes-base.webhook", [-700, -200],
             {"httpMethod": "OPTIONS", "path": "api/manager-subordinates-matrix",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="manager-subordinates-matrix-options"),
        node("mm-options-respond", "Respond OPTIONS", "n8n-nodes-base.respondToWebhook",
             [-250, -200],
             {"respondWith": "noData",
              "options": {
                  "responseCode": 204,
                  "responseHeaders": {
                      "entries": [
                          {"name": "Access-Control-Allow-Origin", "value": "*"},
                          {"name": "Access-Control-Allow-Methods", "value": "GET, POST, OPTIONS"},
                          {"name": "Access-Control-Allow-Headers", "value": "*"},
                      ]
                  },
              }},
             type_version=1.4),
        node("mm-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/manager-subordinates-matrix",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="manager-subordinates-matrix"),
        node("mm-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level", "manager"])}),
        run_guard_node("mm-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("mm-access", "Build Access Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": MANAGER_ACCESS}),
        node("mm-check", "Check Manager", "n8n-nodes-base.postgres",
             [220, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("mm-verify", "Verify Access", "n8n-nodes-base.code",
             [440, 0], {"jsCode": MANAGER_VERIFY}),
        node("mm-period-build", "Build Period Query", "n8n-nodes-base.code",
             [660, 0], {"jsCode": MANAGER_PERIOD_BUILD}),
        node("mm-period", "Load Period", "n8n-nodes-base.postgres",
             [880, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("mm-build", "Build Matrix Query", "n8n-nodes-base.code",
             [1100, 0], {"jsCode": MANAGER_QUERY_BUILD}),
        node("mm-query", "Get Subordinates Matrix", "n8n-nodes-base.postgres",
             [1320, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("mm-format", "Format Response", "n8n-nodes-base.code",
             [1540, 0], {"jsCode": MANAGER_FORMAT}),
        respond_node("mm-respond", "Respond", [1760, 0]),
    ]
    connections = {
        "Webhook OPTIONS": connect("Respond OPTIONS"),
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Access Query"),
        "Build Access Query": connect("Check Manager"),
        "Check Manager": connect("Verify Access"),
        "Verify Access": connect("Build Period Query"),
        "Build Period Query": connect("Load Period"),
        "Load Period": connect("Build Matrix Query"),
        "Build Matrix Query": connect("Get Subordinates Matrix"),
        "Get Subordinates Matrix": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Manager Subordinates Matrix", nodes_list, connections)


# ── 7. GET api/employee-self-review ──────────────────────────────────────────
# No React call site. Actor-only: client subject_id / user_id ignored.

SELF_REVIEW_BUILD = f"""
{guard_reject_js()}
const actorId = Number(guard.identity.id);
return {{
  json: {{
    ok: true,
    actor_id: actorId,
    sql: 'SELECT id FROM performance_db.evaluation_periods WHERE is_active = true LIMIT 1',
  }},
}};
""".strip()

SELF_REVIEW_AFTER_PERIOD = """
const prev = $('Build Period Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const period = $input.all().map(item => item.json).find(item => item.id !== undefined);
const actorId = prev.actor_id;
if (!period) {
  return {
    json: {
      skip: true,
      sql: 'SELECT NULL::integer AS id WHERE false',
    },
  };
}
return {
  json: {
    ok: true,
    actor_id: actorId,
    sql: `
      SELECT id, calculated_score, updated_at
      FROM performance_db.evaluations
      WHERE subject_id = ${actorId}
        AND evaluator_id = ${actorId}
        AND period_id = ${Number(period.id)}
        AND evaluation_type = 'self'
      ORDER BY updated_at DESC
      LIMIT 1
    `,
  },
};
""".strip()

SELF_REVIEW_SCORES = """
const prev = $('Build Self Review Query').first().json;
if (prev.http_status || prev.skip) {
  return { json: prev };
}
const review = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!review) {
  return { json: { skip: true, sql: 'SELECT NULL::integer AS criteria_id WHERE false' } };
}
return {
  json: {
    ok: true,
    review,
    sql: `
      SELECT
        es.criteria_id,
        es.score_value,
        es.comment,
        c.title as criteria_title
      FROM performance_db.evaluation_scores es
      LEFT JOIN performance_db.criteria c ON es.criteria_id = c.id
      WHERE es.evaluation_id = ${Number(review.id)}
    `,
  },
};
""".strip()

SELF_REVIEW_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const reviewStep = $('Build Scores Query').first().json;
if (reviewStep.http_status) {
  return { json: reviewStep };
}
if (reviewStep.skip || !reviewStep.review) {
  return {
    json: {
      http_status: 200,
      body: {
        has_self_review: false,
        evaluation_id: null,
        score: null,
        scores: {},
        comments: {},
      },
    },
  };
}
const review = reviewStep.review;
const scoresMap = {};
const commentsMap = {};
$input.all().forEach(item => {
  if (item.json.criteria_id) {
    scoresMap[item.json.criteria_id] = item.json.score_value;
    if (item.json.comment) {
      commentsMap[item.json.criteria_id] = item.json.comment;
    }
  }
});
return {
  json: {
    http_status: 200,
    body: {
      has_self_review: true,
      evaluation_id: review.id,
      total_score: review.calculated_score,
      updated_at: review.updated_at,
      scores: scoresMap,
      comments: commentsMap,
    },
  },
};
""".strip()


def build_employee_self_review(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("esr-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/employee-self-review",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="0bae8451-0de8-48b5-b905-e27da61a2fb1"),
        node("esr-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("esr-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("esr-period-build", "Build Period Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": SELF_REVIEW_BUILD}),
        node("esr-period", "Get Active Period", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("esr-review-build", "Build Self Review Query", "n8n-nodes-base.code",
             [500, 0], {"jsCode": SELF_REVIEW_AFTER_PERIOD}),
        node("esr-review", "Get Self Review", "n8n-nodes-base.postgres",
             [740, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("esr-scores-build", "Build Scores Query", "n8n-nodes-base.code",
             [980, 0], {"jsCode": SELF_REVIEW_SCORES}),
        node("esr-scores", "Get Scores", "n8n-nodes-base.postgres",
             [1220, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("esr-format", "Format Response", "n8n-nodes-base.code",
             [1460, 0], {"jsCode": SELF_REVIEW_FORMAT}),
        respond_node("esr-respond", "Respond", [1700, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Period Query"),
        "Build Period Query": connect("Get Active Period"),
        "Get Active Period": connect("Build Self Review Query"),
        "Build Self Review Query": connect("Get Self Review"),
        "Get Self Review": connect("Build Scores Query"),
        "Build Scores Query": connect("Get Scores"),
        "Get Scores": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Get Employee Self Review", nodes_list, connections)


# ── 8. POST api/admin/score-correction ───────────────────────────────────────
# Live unique key is (subject, criteria, level, period). period_id is NOT NULL.
# That is existing schema, not a new column. Client evaluator_id / correction_level
# are ignored for privilege. admin+c_level → c_level (2025: Alexander/admin wrote
# both c_level rows). mid_level → actor is the subject's manager's manager.

CORR_VALIDATE = f"""
{guard_reject_js()}
const body = guard.request.body || guard.request;
const actorId = Number(guard.identity.id);
const role = String(guard.identity.role || '');
const subjectId = parseInt(body.subject_id, 10);
const criteriaId = parseInt(body.criteria_id, 10);
const correctionScore = parseInt(body.correction_score, 10);
if (!Number.isFinite(subjectId) || !Number.isFinite(criteriaId) || !Number.isFinite(correctionScore)) {{
  return {{
    json: {{
      http_status: 422,
      body: {{
        success: false,
        error: 'INVALID_BODY',
        message: 'subject_id, criteria_id and correction_score are required',
      }},
    }},
  }};
}}
if (correctionScore < 1 || correctionScore > 10) {{
  return {{
    json: {{
      http_status: 422,
      body: {{
        success: false,
        error: 'GRADE_OUT_OF_RANGE',
        message: 'correction_score must be between 1 and 10',
      }},
    }},
  }};
}}
return {{
  json: {{
    ok: true,
    actor_id: actorId,
    role,
    subject_id: subjectId,
    criteria_id: criteriaId,
    correction_score: correctionScore,
    sql: `
      SELECT
        s.id AS subject_id,
        s.manager_id AS subject_manager_id,
        sm.manager_id AS skip_level_id,
        (
          SELECT p.id
          FROM performance_db.evaluation_periods p
          WHERE p.is_active = true AND p.status = 'active'
          LIMIT 1
        ) AS period_id
      FROM performance_db.users s
      LEFT JOIN performance_db.users sm ON sm.id = s.manager_id
      WHERE s.id = ${{subjectId}}
    `,
  }},
}};
""".strip()

CORR_DECIDE = """
const prev = $('Validate Input').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.subject_id !== undefined);
if (!row) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'NOT_FOUND', message: 'Subject not found' },
    },
  };
}
if (!row.period_id) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'NO_ACTIVE_PERIOD',
        message: 'Score corrections bind only to the active evaluation period',
      },
    },
  };
}
let correctionLevel = 'none';
if (prev.role === 'admin' || prev.role === 'c_level') {
  correctionLevel = 'c_level';
} else if (Number(row.skip_level_id) === Number(prev.actor_id)) {
  correctionLevel = 'mid_level';
}
if (correctionLevel === 'none') {
  return {
    json: {
      http_status: 403,
      body: {
        success: false,
        error: 'OWNERSHIP_FORBIDDEN',
        message: 'You can only correct scores if you are the manager of the subject\\'s manager, or admin/C-level',
      },
    },
  };
}
return {
  json: {
    ok: true,
    actor_id: prev.actor_id,
    subject_id: prev.subject_id,
    criteria_id: prev.criteria_id,
    correction_score: prev.correction_score,
    correction_level: correctionLevel,
    period_id: Number(row.period_id),
    sql: `
      INSERT INTO performance_db.score_corrections
        (subject_id, evaluator_id, criteria_id, correction_score, correction_level, period_id, updated_at)
      VALUES
        (${prev.subject_id}, ${prev.actor_id}, ${prev.criteria_id}, ${prev.correction_score}, '${correctionLevel}', ${Number(row.period_id)}, NOW())
      ON CONFLICT (subject_id, criteria_id, correction_level, period_id)
      DO UPDATE SET
        correction_score = EXCLUDED.correction_score,
        evaluator_id = EXCLUDED.evaluator_id,
        updated_at = NOW()
      RETURNING id, subject_id, criteria_id, correction_score, correction_level, period_id
    `,
  },
};
""".strip()

CORR_FORMAT = """
const prev = $('Decide Level').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: {
      http_status: 500,
      body: { success: false, error: 'WRITE_FAILED', message: 'Score correction was not stored' },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      message: 'Score correction saved successfully',
      data: {
        id: row.id,
        subject_id: row.subject_id,
        criteria_id: row.criteria_id,
        correction_score: row.correction_score,
        correction_level: row.correction_level,
      },
    },
  },
};
""".strip()


def build_score_correction(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("sc-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "POST", "path": "api/admin/score-correction",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="score-correction-webhook"),
        node("sc-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level", "manager"])}),
        run_guard_node("sc-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("sc-validate", "Validate Input", "n8n-nodes-base.code",
             [0, 0], {"jsCode": CORR_VALIDATE}),
        node("sc-lookup", "Load Subject And Period", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("sc-decide", "Decide Level", "n8n-nodes-base.code",
             [500, 0], {"jsCode": CORR_DECIDE}),
        node("sc-upsert", "Upsert Correction", "n8n-nodes-base.postgres",
             [740, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("sc-format", "Format Response", "n8n-nodes-base.code",
             [980, 0], {"jsCode": CORR_FORMAT}),
        respond_node("sc-respond", "Respond", [1220, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Validate Input"),
        "Validate Input": connect("Load Subject And Period"),
        "Load Subject And Period": connect("Decide Level"),
        "Decide Level": connect("Upsert Correction"),
        "Upsert Correction": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Score Correction", nodes_list, connections)


# ── 9. POST manage-criteria ──────────────────────────────────────────────────

CRITERIA_ROUTE = f"""
{guard_reject_js()}
const body = guard.request.body || guard.request;
const action = body.action;
if (action !== 'get' && action !== 'save' && action !== 'delete') {{
  return {{
    json: {{
      http_status: 422,
      body: {{ success: false, error: 'INVALID_ACTION', message: 'action must be get, save, or delete' }},
    }},
  }};
}}
if (action === 'get') {{
  return {{
    json: {{
      ok: true,
      mode: 'get',
      sql: `
        SELECT
          c.*,
          (
            SELECT json_build_object(
              'id', p.id,
              'name', p.name,
              'status', p.status,
              'is_active', p.is_active,
              'period_type', p.period_type,
              'start_date', p.start_date,
              'end_date', p.end_date
            )
            FROM performance_db.evaluation_periods p
            WHERE p.is_active = true AND p.status = 'active'
            LIMIT 1
          ) AS _period
        FROM performance_db.criteria c
        ORDER BY c.id ASC
      `,
    }},
  }};
}}
return {{
  json: {{
    ok: true,
    mode: 'write',
    action,
    sql: `
      SELECT id, name, status
      FROM performance_db.evaluation_periods
      WHERE is_active = true OR status = 'active'
      LIMIT 1
    `,
  }},
}};
""".strip()

CRITERIA_AFTER = """
const prev = $('Route Action').first().json;
if (prev.http_status) {
  return { json: prev };
}
if (prev.mode === 'get') {
  const rows = $input.all().map(item => item.json).filter(item => item.id !== undefined);
  let periodRaw = rows.length ? rows[0]._period : null;
  if (typeof periodRaw === 'string') {
    try { periodRaw = JSON.parse(periodRaw); } catch (e) { periodRaw = null; }
  }
  const data = rows.map(row => {
    const copy = { ...row };
    delete copy._period;
    return copy;
  });
  const isActive = periodRaw && (periodRaw.is_active === true || periodRaw.is_active === 'true');
  return {
    json: {
      http_status: 200,
      body: {
        data,
        period: periodRaw
          ? {
              id: Number(periodRaw.id),
              name: periodRaw.name,
              status: periodRaw.status,
              is_active: Boolean(isActive),
              period_type: periodRaw.period_type,
              start_date: periodRaw.start_date,
              end_date: periodRaw.end_date,
            }
          : null,
        campaign_active: Boolean(isActive && periodRaw && periodRaw.status === 'active'),
      },
    },
  };
}
const activePeriod = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (activePeriod) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'ACTIVE_PERIOD_EXISTS',
        message: `Cannot modify criteria while period "${activePeriod.name}" is active`,
      },
    },
  };
}
const guard = $('Run Auth Guard').first().json;
const body = guard.request.body || guard.request;
const item = body.criteria || {};
const action = prev.action;
""" + CRITERIA_PREP_JS.replace(
    "const action = $('Webhook').item.json.body.action;\nconst item = $('Webhook').item.json.body.criteria || {};\n\n",
    "",
)

CRITERIA_WRITE_FORMAT = """
const prev = $('Prepare Write').first().json;
if (prev.http_status) {
  return { json: prev };
}
return {
  json: {
    http_status: 200,
    body: { success: true, message: 'Operation successful' },
  },
};
""".strip()


def build_manage_criteria(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("mc-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "POST", "path": "manage-criteria",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="110ced24-b474-4754-8976-8d8963ebacb9"),
        node("mc-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("mc-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("mc-route", "Route Action", "n8n-nodes-base.code",
             [0, 0], {"jsCode": CRITERIA_ROUTE}),
        node("mc-first", "Load Criteria Or Freeze", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("mc-prep", "Prepare Write", "n8n-nodes-base.code",
             [500, 0], {"jsCode": CRITERIA_AFTER}),
        node("mc-write", "Execute SQL", "n8n-nodes-base.postgres",
             [740, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.query", "$json.query"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("mc-format", "Format Response", "n8n-nodes-base.code",
             [980, 0], {"jsCode": CRITERIA_WRITE_FORMAT}),
        respond_node("mc-respond", "Respond", [1220, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Route Action"),
        "Route Action": connect("Load Criteria Or Freeze"),
        "Load Criteria Or Freeze": connect("Prepare Write"),
        "Prepare Write": connect("Execute SQL"),
        "Execute SQL": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Manage Criteria Admin V7", nodes_list, connections)


# ── 10. POST update-admin-data ───────────────────────────────────────────────

UPDATE_ADMIN_FREEZE = f"""
{guard_reject_js()}
return {{
  json: {{
    ok: true,
    sql: `
      SELECT id, name, status
      FROM performance_db.evaluation_periods
      WHERE is_active = true OR status = 'active'
      LIMIT 1
    `,
  }},
}};
""".strip()

UPDATE_ADMIN_BUILD = """
const prev = $('Check Freeze').first().json;
if (prev.http_status) {
  return { json: prev };
}
const activePeriod = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (activePeriod) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'ACTIVE_PERIOD_EXISTS',
        message: `Cannot modify grade coefficients while period "${activePeriod.name}" is active`,
      },
    },
  };
}
const guard = $('Run Auth Guard').first().json;
""" + UPDATE_ADMIN_BUILD_JS.replace(
    "const body = $input.item.json.body;",
    "const body = (guard.request.body || guard.request);",
)

UPDATE_ADMIN_FORMAT = """
const prev = $('Build SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      message: 'Данные успешно обновлены',
      updatedCount: prev.count || 0,
    },
  },
};
""".strip()


def build_update_admin_data(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("ua-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "POST", "path": "update-admin-data",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="69fc85c5-3526-4074-85c6-ae57782723cf"),
        node("ua-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("ua-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("ua-freeze", "Check Freeze", "n8n-nodes-base.code",
             [0, 0], {"jsCode": UPDATE_ADMIN_FREEZE}),
        node("ua-period", "Load Active Period", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.ok"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("ua-build", "Build SQL", "n8n-nodes-base.code",
             [500, 0], {"jsCode": UPDATE_ADMIN_BUILD}),
        node("ua-exec", "Execute Update", "n8n-nodes-base.postgres",
             [740, 0],
             {"operation": "executeQuery",
              "query": dummy_if("$json.query", "$json.query"),
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("ua-format", "Format Response", "n8n-nodes-base.code",
             [980, 0], {"jsCode": UPDATE_ADMIN_FORMAT}),
        respond_node("ua-respond", "Respond", [1220, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Check Freeze"),
        "Check Freeze": connect("Load Active Period"),
        "Load Active Period": connect("Build SQL"),
        "Build SQL": connect("Execute Update"),
        "Execute Update": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Update Admin Data", nodes_list, connections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deferred route-guard workflows.")
    parser.add_argument("--postgres-credential-id", default=POSTGRES_CREDENTIAL_PLACEHOLDER)
    parser.add_argument("--guard-workflow-id", default=GUARD_WORKFLOW_PLACEHOLDER)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)

    cred = args.postgres_credential_id
    guard = args.guard_workflow_id
    workflows: dict[str, Any] = {
        "evaluations-matrix.json": build_evaluations_matrix(cred, guard),
        "all-evaluations.json": build_all_evaluations(cred, guard),
        "evaluation-details-by-user.json": build_details_by_user(cred, guard),
        "analytics.json": build_analytics(cred, guard),
        "get-admin-data.json": build_get_admin_data(cred, guard),
        "manager-subordinates-matrix.json": build_manager_matrix(cred, guard),
        "employee-self-review.json": build_employee_self_review(cred, guard),
        "score-correction.json": build_score_correction(cred, guard),
        "manage-criteria.json": build_manage_criteria(cred, guard),
        "update-admin-data.json": build_update_admin_data(cred, guard),
    }
    for filename, payload in workflows.items():
        (args.output_directory / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
    print(
        json.dumps(
            {
                "output_directory": str(args.output_directory),
                "workflows": sorted(workflows),
                "postgres_credential_id": cred,
                "guard_workflow_id": guard,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
