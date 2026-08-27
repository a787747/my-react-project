#!/usr/bin/env python3
"""
Generate inactive n8n route-guard workflow payloads.

Produces deterministic JSON files for 17 EPE API workflows that:
  - call the existing EPE: Auth Guard subworkflow for every protected trigger
  - derive actor identity exclusively from guard output (never from request body)
  - disable execution-data persistence in settings
  - preserve existing frontend response contracts exactly

Usage:
    python3 scripts/build_route_guard_workflows.py \
        --postgres-credential-id VNbfkY8IKbEzn88B \
        --guard-workflow-id L0Zr7nVa8O5YWXd3 \
        --output-directory /tmp/rg_out
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


POSTGRES_CREDENTIAL_PLACEHOLDER = "__EPE_POSTGRES_CREDENTIAL_ID__"
GUARD_WORKFLOW_PLACEHOLDER = "__EPE_AUTH_GUARD_WORKFLOW_ID__"

ROUTE_GUARD_SETTINGS: dict[str, Any] = {
    "executionOrder": "v1",
    "saveDataErrorExecution": "none",
    "saveDataSuccessExecution": "none",
    "saveManualExecutions": False,
}


# ── Node / connection builders ────────────────────────────────────────────────

def node(
    node_id: str,
    name: str,
    node_type: str,
    position: list[int],
    parameters: dict[str, Any],
    *,
    type_version: float = 2,
    credentials: dict[str, Any] | None = None,
    always_output: bool = False,
    webhook_id: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "parameters": parameters,
        "id": node_id,
        "name": name,
        "type": node_type,
        "typeVersion": type_version,
        "position": position,
    }
    if credentials:
        result["credentials"] = credentials
    if always_output:
        result["alwaysOutputData"] = True
    if webhook_id:
        result["webhookId"] = webhook_id
    return result


def postgres_credentials(credential_id: str) -> dict[str, Any]:
    return {"postgres": {"id": credential_id, "name": "EPE 2026 Postgres"}}


def connect(*targets: str) -> dict[str, Any]:
    return {
        "main": [[{"node": t, "type": "main", "index": 0} for t in targets]]
    }


def respond_node(node_id: str, name: str, position: list[int]) -> dict[str, Any]:
    return node(
        node_id,
        name,
        "n8n-nodes-base.respondToWebhook",
        position,
        {
            "respondWith": "json",
            "responseBody": "={{ $json.body }}",
            "options": {"responseCode": "={{ $json.http_status }}"},
        },
        type_version=1.4,
    )


def workflow(
    name: str,
    nodes_list: list[dict[str, Any]],
    connections: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "nodes": nodes_list,
        "connections": connections,
        "settings": ROUTE_GUARD_SETTINGS,
    }


def guard_input_js(
    required_roles: list[str],
    required_capability: str = "",
) -> str:
    roles = json.dumps(required_roles)
    cap = json.dumps(required_capability)
    return (
        "const request = $input.first().json;\n"
        "return {\n"
        "  json: {\n"
        "    authorization: request.headers?.authorization || '',\n"
        f"    required_roles: {roles},\n"
        f"    required_capability: {cap},\n"
        "    request,\n"
        "  },\n"
        "};"
    )


def run_guard_node(
    node_id: str,
    name: str,
    position: list[int],
    guard_workflow_id: str,
) -> dict[str, Any]:
    return node(
        node_id,
        name,
        "n8n-nodes-base.executeWorkflow",
        position,
        {"workflowId": guard_workflow_id, "options": {}},
        type_version=1,
    )


# ── 1. GET api/criteria — API: Get Criteria With Levels ───────────────────────

CRITERIA_BUILD_QUERY = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
return {
  json: {
    ok: true,
    sql: `
      SELECT id, title, description, target_audience, weight, is_active,
        selfassesment, for_manager, c_level_only,
        level_0_desc, level_1_desc, level_2_desc, level_3_desc, level_4_desc,
        level_5_desc, level_6_desc, level_7_desc, level_8_desc, level_9_desc, level_10_desc
      FROM performance_db.criteria
      ORDER BY id ASC
    `,
  },
};
""".strip()

CRITERIA_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const role = String(guard.identity.role || '');
const canSeeCLevelTexts = ['admin', 'c_level'].includes(role);
// Criterion weight is a money input: it decides bonus share. Admin only
// (D-0822-2) — closing GET /api/score-coefficients alone would have left the
// weights readable here.
const canSeeWeight = role === 'admin';
const levelTextFields = Array.from({ length: 10 }, (_, index) => `level_${index + 1}_desc`);
const criteria = $input.all()
  .map(item => item.json)
  .filter(item => item.id !== undefined)
  .map(row => {
    const criterion = { ...row };
    const isCLevelOnly = row.c_level_only === true || row.c_level_only === 't';
    if (isCLevelOnly && !canSeeCLevelTexts) {
      levelTextFields.forEach(field => delete criterion[field]);
    }
    if (!canSeeWeight) {
      delete criterion.weight;
    }
    return criterion;
  });
return {
  json: {
    http_status: 200,
    body: { success: true, data: criteria },
  },
};
""".strip()


def build_criteria(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("criteria-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/criteria",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-criteria"),
        node("criteria-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("criteria-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("criteria-build", "Build Criteria Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": CRITERIA_BUILD_QUERY}),
        node("criteria-query", "Load Criteria", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("criteria-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": CRITERIA_FORMAT}),
        respond_node("criteria-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Criteria Query"),
        "Build Criteria Query": connect("Load Criteria"),
        "Load Criteria": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Get Criteria With Levels", nodes_list, connections)


# ── 2. GET api/get-my-manager — API: Get My Manager ──────────────────────────
# Response: {success, has_manager, manager: {id, full_name, email, job_title, role,
#   has_subordinates, department_name, grade_code, grade_coefficient (admin/c_level only),
#   has_evaluated_manager, last_evaluation_score, previous_scores[]}}

MY_MANAGER_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
return {
  json: {
    ok: true,
    sql: `
      SELECT
        m.id,
        m.full_name,
        m.email,
        m.job_title,
        m.role,
        m.has_subordinates,
        d.name AS department_name,
        g.code AS grade_code,
        g.coefficient AS grade_coefficient,
        COALESCE(
          (SELECT true
           FROM performance_db.evaluations e
           WHERE e.subject_id = m.id
             AND e.evaluator_id = ${actorId}
             AND e.evaluation_source = 'subordinate'
             AND e.period_id IN (
               SELECT cp.id FROM performance_db.evaluation_periods cp
               WHERE cp.is_active = true AND cp.status = 'active'
                 AND cp.evaluation_started_at IS NOT NULL
                 AND cp.period_type <> 'annual'
                 AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                                 WHERE child.parent_period_id = cp.id)
             )
           LIMIT 1),
          false
        ) AS has_evaluated_manager,
        (SELECT e.calculated_score
         FROM performance_db.evaluations e
         JOIN performance_db.evaluation_periods ep
           ON ep.id = e.period_id AND ep.is_active = true AND ep.status = 'active'
              AND ep.evaluation_started_at IS NOT NULL
              AND ep.period_type <> 'annual'
              AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                              WHERE child.parent_period_id = ep.id)
         WHERE e.subject_id = m.id AND e.evaluator_id = ${actorId}
         ORDER BY e.updated_at DESC LIMIT 1
        ) AS last_evaluation_score,
        COALESCE(
          (SELECT json_agg(e.calculated_score ORDER BY e.updated_at DESC)
           FROM performance_db.evaluations e
           WHERE e.subject_id = m.id AND e.evaluator_id = ${actorId}
          ),
          '[]'::json
        ) AS previous_scores
      FROM performance_db.users u
      JOIN performance_db.users m ON m.id = u.manager_id
      LEFT JOIN performance_db.departments d ON d.id = m.department_id
      LEFT JOIN performance_db.grades g ON g.id = m.grade_id
      WHERE u.id = ${actorId}
      LIMIT 1
    `,
  },
};
""".strip()

MY_MANAGER_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const rows = $input.all().map(item => item.json).filter(item => item.id !== undefined);
if (!rows.length) {
  return { json: { http_status: 200, body: { success: true, has_manager: false, manager: null } } };
}
const m = rows[0];
const canSeeGradeCoefficient = ['admin', 'c_level'].includes(String(guard.identity.role || ''));
let previousScores = m.previous_scores;
if (typeof previousScores === 'string') {
  try { previousScores = JSON.parse(previousScores); } catch { previousScores = []; }
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      has_manager: true,
      manager: {
        id: m.id,
        full_name: m.full_name,
        email: m.email,
        job_title: m.job_title,
        role: m.role,
        has_subordinates: m.has_subordinates,
        department_name: m.department_name,
        grade_code: m.grade_code,
        ...(canSeeGradeCoefficient ? { grade_coefficient: m.grade_coefficient } : {}),
        has_evaluated_manager: m.has_evaluated_manager || false,
        last_evaluation_score: m.last_evaluation_score,
        previous_scores: previousScores || [],
      },
    },
  },
};
""".strip()


def build_get_my_manager(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("manager-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/get-my-manager",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-get-my-manager"),
        node("manager-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("manager-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("manager-build", "Build Manager Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": MY_MANAGER_BUILD}),
        node("manager-query", "Load Manager", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("manager-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": MY_MANAGER_FORMAT}),
        respond_node("manager-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Manager Query"),
        "Build Manager Query": connect("Load Manager"),
        "Load Manager": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Get My Manager", nodes_list, connections)


# ── 3. GET api/my-profile — API: My Profile V5 (Fixed Empty) ─────────────────
# Response: {success, has_evaluations, evaluations: [...], stats: {...}}
# Actor is subject. Non-self evaluation content is sealed; subordinate evaluator identity is redacted.

MY_PROFILE_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
return {
  json: {
    ok: true,
    sql: `
      WITH actor AS (
        SELECT
          actor_u.id AS employee_id,
          actor_u.full_name,
          actor_u.job_title,
          departments.name AS department_name,
          manager.full_name AS manager_name,
          grades.code AS grade_label,
          to_char(actor_u.join_date, 'YYYY-MM-DD') AS join_date
        FROM performance_db.users actor_u
        LEFT JOIN performance_db.departments departments
          ON departments.id = actor_u.department_id
        LEFT JOIN performance_db.users manager
          ON manager.id = actor_u.manager_id
        LEFT JOIN performance_db.grades grades
          ON grades.id = actor_u.grade_id
        WHERE actor_u.id = ${actorId}
      ),
      current_period AS (
        SELECT
          period.id,
          period.name,
          period.status,
          period.is_active,
          to_char(period.start_date, 'YYYY-MM-DD') AS start_date,
          to_char(period.end_date, 'YYYY-MM-DD') AS end_date
        FROM performance_db.evaluation_periods period
        WHERE period.is_active = true
          AND period.status = 'active'
          AND period.period_type <> 'annual'
          AND NOT EXISTS (
            SELECT 1
            FROM performance_db.evaluation_periods child
            WHERE child.parent_period_id = period.id
          )
        LIMIT 1
      ),
      actor_evaluations AS (
        SELECT
          e.id AS evaluation_id,
          e.calculated_score,
          e.weighted_score,
          e.updated_at,
          e.is_self_evaluation,
          e.evaluation_source,
          p.name AS period_name,
          to_char(p.start_date, 'YYYY-MM-DD') AS start_date,
          to_char(p.end_date, 'YYYY-MM-DD') AS end_date,
          evaluator.full_name AS evaluator_name,
          evaluator.job_title AS evaluator_title
        FROM performance_db.evaluations e
        LEFT JOIN performance_db.evaluation_periods p ON p.id = e.period_id
        LEFT JOIN performance_db.users evaluator ON evaluator.id = e.evaluator_id
        WHERE e.subject_id = ${actorId}
      )
      SELECT
        actor.*,
        current_period.id AS current_period_id,
        current_period.name AS current_period_name,
        current_period.status AS current_period_status,
        current_period.start_date AS current_period_start_date,
        current_period.end_date AS current_period_end_date,
        participant.is_in_scope,
        participant.exclusion_reason,
        participant.scope_override,
        actor_evaluations.*
      FROM actor
      LEFT JOIN current_period ON true
      LEFT JOIN performance_db.evaluation_period_participants participant
        ON participant.period_id = current_period.id
       AND participant.user_id = actor.employee_id
      LEFT JOIN actor_evaluations ON true
      ORDER BY actor_evaluations.updated_at DESC NULLS LAST
    `,
  },
};
""".strip()

MY_PROFILE_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const rows = $input.all().map(item => item.json);
const first = rows[0] || {};
const data = rows.filter(item => item.evaluation_id !== undefined && item.evaluation_id !== null);

const asBoolean = value => value === true || value === 't';
const employee = {
  id: first.employee_id ?? Number(guard.identity.id),
  full_name: first.full_name ?? guard.identity.full_name ?? null,
  job_title: first.job_title ?? null,
  department_name: first.department_name ?? null,
  manager_name: first.manager_name ?? null,
  grade_label: first.grade_label ?? null,
  join_date: first.join_date ?? null,
};
const currentPeriod = first.current_period_id === null || first.current_period_id === undefined
  ? null
  : {
      id: first.current_period_id,
      name: first.current_period_name,
      status: first.current_period_status,
      start_date: first.current_period_start_date,
      end_date: first.current_period_end_date,
      is_in_scope: first.is_in_scope === null || first.is_in_scope === undefined
        ? null
        : asBoolean(first.is_in_scope),
      exclusion_reason: first.exclusion_reason ?? null,
      scope_override: first.scope_override ?? null,
    };

const evaluations = data.map(row => {
  const isSelfEvaluation = row.is_self_evaluation === true || row.is_self_evaluation === 't';
  const evaluation = {
    evaluation_id: row.evaluation_id,
    updated_at: row.updated_at,
    is_self_evaluation: isSelfEvaluation,
    evaluation_source: row.evaluation_source,
    period_name: row.period_name,
    start_date: row.start_date,
    end_date: row.end_date,
    evaluator_name: row.evaluation_source === 'subordinate' ? null : row.evaluator_name,
    evaluator_title: row.evaluation_source === 'subordinate' ? null : row.evaluator_title,
  };
  if (isSelfEvaluation) {
    evaluation.score = row.calculated_score;
    evaluation.calculated_score = row.calculated_score;
    evaluation.weighted_score = row.weighted_score;
  }
  return evaluation;
});

const selfEvaluations = evaluations.filter(e => e.is_self_evaluation);
const scores = selfEvaluations
  .map(e => e.calculated_score)
  .filter(s => s !== null && s !== undefined);
const total = evaluations.length;
const avg = scores.length ? parseFloat((scores.reduce((a, b) => a + Number(b), 0) / scores.length).toFixed(2)) : null;
const latestSelf = selfEvaluations[0];

return {
  json: {
    http_status: 200,
    body: {
      success: true,
      employee,
      current_period: currentPeriod,
      has_evaluations: evaluations.length > 0,
      evaluations,
      stats: {
        total_evaluations: total,
        average_score: avg,
        latest_score: latestSelf?.calculated_score ?? null,
        latest_period: latestSelf?.period_name ?? null,
        latest_date: latestSelf?.updated_at ?? null,
      },
    },
  },
};
""".strip()


def build_my_profile(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("profile-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/my-profile",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-my-profile"),
        node("profile-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("profile-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("profile-build", "Build Profile Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": MY_PROFILE_BUILD}),
        node("profile-query", "Load Profile Evaluations", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS evaluation_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("profile-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": MY_PROFILE_FORMAT}),
        respond_node("profile-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Profile Query"),
        "Build Profile Query": connect("Load Profile Evaluations"),
        "Load Profile Evaluations": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: My Profile V5 (Fixed Empty)", nodes_list, connections)


# ── 4. GET api/check-evaluated — API: Check Evaluated V2 ─────────────────────
# Response: {success: true, details: [{subject_id, latest_evaluation_id, last_score, updated_at}]}
# Actor is evaluator; no subject_id param needed.

CHECK_EVALUATED_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
return {
  json: {
    ok: true,
    sql: `
      SELECT
        e.subject_id,
        e.id AS latest_evaluation_id,
        e.calculated_score AS last_score,
        e.updated_at
      FROM performance_db.evaluations e
      JOIN performance_db.evaluation_periods ep
        ON ep.id = e.period_id AND ep.is_active = true AND ep.status = 'active'
           AND ep.evaluation_started_at IS NOT NULL
           AND ep.period_type <> 'annual'
           AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                           WHERE child.parent_period_id = ep.id)
      WHERE e.evaluator_id = ${actorId}
        AND e.is_self_evaluation = false
      ORDER BY e.updated_at DESC
    `,
  },
};
""".strip()

CHECK_EVALUATED_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const details = $input.all()
  .map(item => item.json)
  .filter(item => item.subject_id !== undefined);
return {
  json: {
    http_status: 200,
    body: { success: true, details },
  },
};
""".strip()


def build_check_evaluated(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("chkeval-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/check-evaluated",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-check-evaluated"),
        node("chkeval-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("chkeval-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("chkeval-build", "Build Evaluated Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": CHECK_EVALUATED_BUILD}),
        node("chkeval-query", "Load Evaluated", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS subject_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("chkeval-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": CHECK_EVALUATED_FORMAT}),
        respond_node("chkeval-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Evaluated Query"),
        "Build Evaluated Query": connect("Load Evaluated"),
        "Load Evaluated": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Check Evaluated V2", nodes_list, connections)


# ── 5. GET api/check-self-review — API: Check Self Review ────────────────────
# Response: {has_self_review, evaluation_id, score, date, evaluated_criteria_ids, grades, comments}
# user_id may select a direct report for their manager, or any subject for admin/c_level.

CHECK_SELF_REVIEW_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const actorRole = String(guard.identity.role || '');
const request = guard.request || {};
const parsedRequestedId = parseInt(request.query?.user_id || request.body?.user_id, 10);
const requestedId = Number.isFinite(parsedRequestedId) && parsedRequestedId > 0
  ? parsedRequestedId
  : actorId;
const privileged = ['admin', 'c_level'].includes(actorRole);
return {
  json: {
    ok: true,
    sql: `
      WITH selected_subject AS (
        SELECT CASE
          WHEN ${requestedId} = ${actorId} THEN ${actorId}
          WHEN ${privileged} THEN ${requestedId}
          WHEN EXISTS (
            SELECT 1
            FROM performance_db.users target
            WHERE target.id = ${requestedId}
              AND target.manager_id = ${actorId}
          ) THEN ${requestedId}
          ELSE ${actorId}
        END AS subject_id
      )
      SELECT
        e.id,
        e.calculated_score,
        e.general_comment,
        e.updated_at,
        COALESCE(
          ARRAY_AGG(es.criteria_id) FILTER (WHERE es.criteria_id IS NOT NULL),
          '{}'
        ) AS evaluated_criteria_ids,
        COALESCE(
          jsonb_object_agg(es.criteria_id::text, es.score_value)
            FILTER (WHERE es.criteria_id IS NOT NULL),
          '{}'::jsonb
        ) AS grades,
        COALESCE(
          jsonb_object_agg(es.criteria_id::text, es.comment)
            FILTER (WHERE es.criteria_id IS NOT NULL AND es.comment IS NOT NULL AND es.comment != ''),
          '{}'::jsonb
        ) AS comments
      FROM performance_db.evaluations e
      JOIN selected_subject ss ON ss.subject_id = e.subject_id
      JOIN performance_db.evaluation_periods p
        ON p.id = e.period_id AND p.is_active = true AND p.status = 'active'
           AND p.evaluation_started_at IS NOT NULL
           AND p.period_type <> 'annual'
           AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                           WHERE child.parent_period_id = p.id)
      LEFT JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
      WHERE e.is_self_evaluation = true
      GROUP BY e.id, e.calculated_score, e.general_comment, e.updated_at
      ORDER BY e.updated_at DESC
      LIMIT 1
    `,
  },
};
""".strip()

CHECK_SELF_REVIEW_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const rows = $input.all().map(item => item.json).filter(item => item.id !== undefined);
if (!rows.length) {
  return {
    json: {
      http_status: 200,
      body: {
        has_self_review: false,
        evaluation_id: null,
        score: null,
        general_comment: null,
        grades: {},
        comments: {},
      },
    },
  };
}
const review = rows[0];
let grades = review.grades || {};
let comments = review.comments || {};
if (typeof grades === 'string') { try { grades = JSON.parse(grades); } catch { grades = {}; } }
if (typeof comments === 'string') { try { comments = JSON.parse(comments); } catch { comments = {}; } }
return {
  json: {
    http_status: 200,
    body: {
      has_self_review: true,
      evaluation_id: review.id,
      score: review.calculated_score,
      general_comment: review.general_comment,
      date: review.updated_at,
      evaluated_criteria_ids: review.evaluated_criteria_ids || [],
      grades,
      comments,
    },
  },
};
""".strip()


def build_check_self_review(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("chksr-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/check-self-review",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-check-self-review"),
        node("chksr-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("chksr-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("chksr-build", "Build Self Review Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": CHECK_SELF_REVIEW_BUILD}),
        node("chksr-query", "Load Self Review", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("chksr-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": CHECK_SELF_REVIEW_FORMAT}),
        respond_node("chksr-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Self Review Query"),
        "Build Self Review Query": connect("Load Self Review"),
        "Load Self Review": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Check Self Review", nodes_list, connections)


# ── 6. POST api/submit-evaluation — API: Submit Evaluation ───────────────────
# Guard requires can_evaluate. Duplicate key includes evaluation_source.
# Period must have BOTH is_active=true AND status='active'. HTTP 200.
# c_level_direct: actor role admin or c_level; evaluator is always the token
# actor (client evaluator_id ignored); subject must be can_be_evaluated, in
# scope, and not one of the three read-only emails. Stored number is the
# plain average of score rows — same formula as manager/subordinate.

SUBMIT_EVAL_VALIDATE = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const actorRole = String(guard.identity.role || '');
const body = guard.request.body || guard.request;
// Ignore body.evaluator_id — evaluator is always the token actor.

const source = String(body.evaluation_source || 'manager').trim();
if (source !== 'manager' && source !== 'subordinate' && source !== 'c_level_direct') {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_SOURCE', message: 'Источник оценки должен быть manager, subordinate или c_level_direct' },
    },
  };
}
if (source === 'c_level_direct' && actorRole !== 'c_level' && actorRole !== 'admin') {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'ROLE_FORBIDDEN', message: 'Оценка c_level_direct доступна только администратору или C-level' },
    },
  };
}

const rawSubjectId = parseInt(body.subject_id, 10);
if (!Number.isFinite(rawSubjectId) || rawSubjectId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_SUBJECT', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
    },
  };
}
if (rawSubjectId === actorId) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'SELF_EVALUATION_FORBIDDEN', message: 'Для самооценки используйте форму самооценки' },
    },
  };
}

const safeSource = source.replace(/'/g, "''");
let relationFilter;
if (source === 'manager') {
  relationFilter = `AND subj.manager_id = ${actorId} AND subj.can_be_evaluated = true`;
} else if (source === 'subordinate') {
  relationFilter = `AND actor.manager_id = ${rawSubjectId} AND subj.can_be_evaluated = true AND subj.role NOT IN ('c_level', 'admin')`;
} else {
  relationFilter = `AND actor.role IN ('c_level', 'admin') AND subj.can_be_evaluated = true AND lower(subj.email) NOT IN ('cem@sedamedical.com', 'hemra@sedamedical.com', 'mekan@sedamedical.com')`;
}

return {
  json: {
    ok: true,
    actor_id: actorId,
    subject_id: rawSubjectId,
    source: safeSource,
    sql: `
      SELECT
        p.id AS period_id,
        (p.evaluation_started_at IS NOT NULL) AS period_started,
        subj.id AS subject_id,
        subj.role AS subject_role,
        subj.is_project_participant AS subject_is_project,
        actor.can_evaluate,
        (SELECT dup.id
           FROM performance_db.evaluations dup
          WHERE dup.subject_id = ${rawSubjectId}
            AND dup.evaluator_id = ${actorId}
            AND dup.evaluation_source = '${safeSource}'
            AND dup.period_id = p.id
            AND dup.is_self_evaluation = false
          LIMIT 1) AS existing_evaluation_id,
        COALESCE((
          SELECT json_agg(DISTINCT es.criteria_id)
          FROM performance_db.evaluations dup2
          JOIN performance_db.evaluation_scores es ON es.evaluation_id = dup2.id
          WHERE dup2.subject_id = ${rawSubjectId}
            AND dup2.evaluator_id = ${actorId}
            AND dup2.evaluation_source = '${safeSource}'
            AND dup2.period_id = p.id
            AND dup2.is_self_evaluation = false
        ), '[]'::json) AS existing_criteria_ids,
        COALESCE((
          SELECT json_agg(c.id)
          FROM performance_db.criteria c
          WHERE c.target_audience = 'project_participants'
        ), '[]'::json) AS project_criteria_ids
      FROM performance_db.evaluation_periods p
      JOIN performance_db.evaluation_period_participants ep_actor
        ON ep_actor.period_id = p.id AND ep_actor.user_id = ${actorId} AND ep_actor.is_in_scope = true
      JOIN performance_db.evaluation_period_participants ep_subj
        ON ep_subj.period_id = p.id AND ep_subj.user_id = ${rawSubjectId} AND ep_subj.is_in_scope = true
      JOIN performance_db.users subj ON subj.id = ${rawSubjectId}
      JOIN performance_db.users actor ON actor.id = ${actorId}
      WHERE p.is_active = true AND p.status = 'active'
        AND p.period_type <> 'annual'
        AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                        WHERE child.parent_period_id = p.id)
        AND ${rawSubjectId} != ${actorId}
        ${relationFilter}
    `,
  },
};
""".strip()

SUBMIT_EVAL_BUILD_INSERT = """
const prev = $('Validate Evaluation').first().json;
if (prev.http_status) {
  return { json: prev };
}

const validation = $input.first().json;

if (!validation.period_id) {
  return {
    json: {
      http_status: 403,
      body: {
        success: false,
        error: 'SCOPE_MISMATCH',
        message: 'Сотрудник или оценщик вне охвата активного периода либо связь между ними не разрешена',
      },
    },
  };
}
// The campaign period is active AND started (D-0822-1). During the preparation
// window the period exists and scope is real, but nothing may be submitted yet.
if (!validation.period_started) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'PERIOD_NOT_STARTED',
        message: 'Оценка ещё не запущена: период в подготовке',
      },
    },
  };
}
if (!validation.can_evaluate) {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'CANNOT_EVALUATE', message: 'У вас нет права проводить оценку' },
    },
  };
}

const guard = $('Run Auth Guard').first().json;
const body = guard.request.body || guard.request;
const actorId = Number(prev.actor_id);
const subjectId = Number(prev.subject_id);
const periodId = Number(validation.period_id);
const source = String(prev.source);
const grades = body.grades || {};
const comments = body.comments || {};
const generalComment = String(body.general_comment || '').replace(/'/g, "''");
const generalCommentSql = generalComment ? `'${generalComment}'` : 'NULL';

// Validate grades before building SQL — return 422, never throw.
const gradeEntries = Object.entries(grades);
if (!gradeEntries.length) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'NO_GRADES', message: 'Необходимо указать хотя бы одну оценку' },
    },
  };
}
for (const [cId, sv] of gradeEntries) {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Некорректный идентификатор критерия: ${cId}` } } };
  }
  if (!Number.isFinite(scoreValue) || scoreValue < 1 || scoreValue > 10) {
    return { json: { http_status: 422, body: { success: false, error: 'GRADE_OUT_OF_RANGE', message: `Оценка по критерию ${cId} должна быть целым числом от 1 до 10` } } };
  }
}

// ── Applicability, classification dimension only (D-0822-3) ─────────────────
// A project_participants criterion applies to a subject iff the subject is
// CURRENTLY a project participant. Other audiences keep today's semantics.
const parseIdList = (raw) => {
  let value = raw;
  if (typeof value === 'string') {
    try { value = JSON.parse(value); } catch { value = []; }
  }
  return Array.isArray(value) ? value.map(Number) : [];
};
const projectCriteriaIds = parseIdList(validation.project_criteria_ids);
const existingCriteriaIds = parseIdList(validation.existing_criteria_ids);
const subjectIsProject = validation.subject_is_project === true || validation.subject_is_project === 't';
const submittedIds = gradeEntries.map(([cId]) => parseInt(cId, 10));
if (!subjectIsProject) {
  const notApplicable = submittedIds.filter(id => projectCriteriaIds.includes(id));
  if (notApplicable.length) {
    return {
      json: {
        http_status: 422,
        body: {
          success: false,
          error: 'CRITERIA_NOT_APPLICABLE',
          message: `Критерии ${notApplicable.join(', ')} — проектные, а сотрудник сейчас не участник проекта`,
        },
      },
    };
  }
}

const scoreRows = gradeEntries.map(([cId, sv], idx) => {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  const rawComment = String(comments[cId] || '').replace(/'/g, "''");
  const commentLit = rawComment ? `'${rawComment}'` : 'NULL';
  if (idx === 0) {
    return `(${criteriaId}::integer, ${scoreValue}::integer, ${commentLit}::text)`;
  }
  return `(${criteriaId}, ${scoreValue}, ${commentLit})`;
});

// ── Additive path (D-0822-3, retires the BUG-036 409 dead end on this path) ──
// An existing evaluation no longer makes every further submit a 409. Scores
// for criteria the evaluation does not cover yet are ADDED to it; criteria it
// already covers are refused explicitly (edit is the way to change a score).
const existingEvaluationId = validation.existing_evaluation_id
  ? Number(validation.existing_evaluation_id)
  : null;
if (existingEvaluationId) {
  const alreadyScored = submittedIds.filter(id => existingCriteriaIds.includes(id));
  if (alreadyScored.length) {
    // Any overlap — including a full re-submit — is refused by name: these
    // criteria exist, and changing an existing score is what edit is for.
    // (DUPLICATE_EVALUATION remains only on the concurrent-create race path
    // in Format Response.)
    return {
      json: {
        http_status: 409,
        body: {
          success: false,
          error: 'CRITERIA_ALREADY_SCORED',
          message: `Критерии ${alreadyScored.join(', ')} уже оценены — дооценка принимает только недостающие критерии; для изменения оценок используйте редактирование`,
        },
      },
    };
  }
  // calculated_score is recomputed HERE from the full surviving row set that
  // counts under the subject's CURRENT classification — never taken from the
  // client. The overlap and campaign preconditions are re-asserted inline in
  // target_eval, so a lost race adds nothing and recomputes nothing (the
  // BUG-041 rule: every data-modifying branch shares one gate).
  return {
    json: {
      ok: true,
      mode: 'additive',
      sql: `
WITH score_rows(crit_id, score_val, cmt) AS (
  VALUES ${scoreRows.join(', ')}
),
target_eval AS (
  SELECT e.id
  FROM performance_db.evaluations e
  JOIN performance_db.evaluation_periods p ON p.id = e.period_id
  WHERE e.id = ${existingEvaluationId}
    AND e.evaluator_id = ${actorId}
    AND e.is_self_evaluation = false
    AND p.status = 'active'
    AND p.is_active = true
    AND p.evaluation_started_at IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM performance_db.evaluation_scores es
      JOIN score_rows sr ON sr.crit_id = es.criteria_id
      WHERE es.evaluation_id = e.id
    )
  FOR UPDATE OF e
),
added_scores AS (
  INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
  SELECT te.id, sr.crit_id, sr.score_val, sr.cmt
  FROM target_eval te
  CROSS JOIN score_rows sr
  RETURNING criteria_id
),
recomputed AS (
  UPDATE performance_db.evaluations e
  SET calculated_score = (
        SELECT AVG(v.val)
        FROM (
          SELECT es.score_value::numeric AS val
          FROM performance_db.evaluation_scores es
          JOIN performance_db.criteria c ON c.id = es.criteria_id
          WHERE es.evaluation_id = e.id
            AND (c.target_audience <> 'project_participants'
                 OR EXISTS (SELECT 1 FROM performance_db.users s
                            WHERE s.id = e.subject_id AND s.is_project_participant = true))
          UNION ALL
          SELECT sr.score_val::numeric FROM score_rows sr
        ) v
      ),
      updated_at = now()
  WHERE e.id IN (SELECT id FROM target_eval)
  RETURNING e.id, e.calculated_score
)
SELECT r.id AS evaluation_id,
       r.calculated_score AS final_score,
       (SELECT count(*)::integer FROM added_scores) AS scores_added
FROM recomputed r
      `,
    },
  };
}

return {
  json: {
    ok: true,
    mode: 'insert',
    sql: `
WITH score_rows(crit_id, score_val, cmt) AS (
  VALUES ${scoreRows.join(', ')}
),
new_eval AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  SELECT ${subjectId}, ${actorId}, ${periodId},
         (SELECT AVG(score_val::numeric) FROM score_rows),
         '${source}', false, 'completed', ${generalCommentSql}, now()
  WHERE EXISTS (SELECT 1 FROM score_rows)
  ON CONFLICT (subject_id, evaluator_id, evaluation_source, period_id)
  WHERE is_self_evaluation = false
  DO NOTHING
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT ne.id, sr.crit_id, sr.score_val, sr.cmt
FROM new_eval ne
CROSS JOIN score_rows sr
RETURNING evaluation_id
    `,
  },
};
""".strip()

SUBMIT_EVAL_FORMAT = """
const prev = $('Build Insert SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const rows = $input.all().map(item => item.json).filter(item => item.evaluation_id !== undefined);
if (prev.mode === 'additive') {
  if (!rows.length) {
    // target_eval matched zero rows: a criterion got scored, the ownership
    // changed, or the campaign stopped inside the race window. Nothing was
    // inserted and nothing was recomputed.
    return {
      json: {
        http_status: 409,
        body: {
          success: false,
          error: 'ADDITIVE_CONFLICT',
          message: 'Дооценка не выполнена: критерии уже оценены или период больше не идёт',
        },
      },
    };
  }
  const r = rows[0];
  return {
    json: {
      http_status: 200,
      body: {
        success: true,
        message: 'Evaluation extended',
        evaluation_id: r.evaluation_id,
        final_score: parseFloat(r.final_score),
        scores_added: r.scores_added,
      },
    },
  };
}
if (!rows.length) {
  // ON CONFLICT DO NOTHING returned 0 rows — race-condition duplicate
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'DUPLICATE_EVALUATION', message: 'Такая оценка уже была отправлена' },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: { success: true, message: 'Evaluation saved successfully' },
  },
};
""".strip()


def build_submit_evaluation(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("subeval-webhook", "Webhook", "n8n-nodes-base.webhook", [-900, 0],
             {"httpMethod": "POST", "path": "api/submit-evaluation",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-submit-evaluation"),
        node("subeval-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-680, 0], {"jsCode": guard_input_js([], "can_evaluate")}),
        run_guard_node("subeval-run-guard", "Run Auth Guard", [-450, 0], guard_workflow_id),
        node("subeval-validate", "Validate Evaluation", "n8n-nodes-base.code",
             [-200, 0], {"jsCode": SUBMIT_EVAL_VALIDATE}),
        node("subeval-check", "Execute Scope Check", "n8n-nodes-base.postgres",
             [60, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS period_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("subeval-build", "Build Insert SQL", "n8n-nodes-base.code",
             [320, 0], {"jsCode": SUBMIT_EVAL_BUILD_INSERT}),
        node("subeval-insert", "Execute Insert", "n8n-nodes-base.postgres",
             [580, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS evaluation_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("subeval-format", "Format Response", "n8n-nodes-base.code",
             [840, 0], {"jsCode": SUBMIT_EVAL_FORMAT}),
        respond_node("subeval-respond", "Respond", [1080, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Validate Evaluation"),
        "Validate Evaluation": connect("Execute Scope Check"),
        "Execute Scope Check": connect("Build Insert SQL"),
        "Build Insert SQL": connect("Execute Insert"),
        "Execute Insert": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Submit Evaluation", nodes_list, connections)


# ── 7. POST+OPTIONS api/update-evaluation — API: Update Evaluation WITH PERIOD
# Guard requires can_evaluate. Atomic upsert+delete for scores.
# Response: {status:'success', message, evaluation_id, final_score, scores_saved}

UPDATE_EVAL_VALIDATE = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request;
const rawEvalId = parseInt(body.evaluation_id, 10);
if (!Number.isFinite(rawEvalId) || rawEvalId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_EVALUATION_ID', message: 'Идентификатор оценки должен быть положительным целым числом' },
    },
  };
}
return {
  json: {
    ok: true,
    actor_id: actorId,
    evaluation_id: rawEvalId,
    sql: `
      SELECT
        e.id,
        e.subject_id,
        e.evaluator_id,
        e.period_id,
        p.status AS period_status,
        p.is_active AS period_is_active,
        (p.evaluation_started_at IS NOT NULL) AS period_started,
        subj.is_project_participant AS subject_is_project,
        COALESCE((
          SELECT json_agg(c.id)
          FROM performance_db.criteria c
          WHERE c.target_audience = 'project_participants'
        ), '[]'::json) AS project_criteria_ids
      FROM performance_db.evaluations e
      JOIN performance_db.evaluation_periods p ON p.id = e.period_id
      JOIN performance_db.users subj ON subj.id = e.subject_id
      WHERE e.id = ${rawEvalId}
        AND e.evaluator_id = ${actorId}
        AND e.is_self_evaluation = false
      LIMIT 1
    `,
  },
};
""".strip()

UPDATE_EVAL_BUILD_UPDATE = """
const prev = $('Validate Update').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.first().json;

if (!check.id) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'NOT_FOUND', message: 'Оценка не найдена или недоступна вам' },
    },
  };
}
if (check.period_status === 'closed') {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'PERIOD_CLOSED', message: 'Нельзя изменить оценку: период уже закрыт' },
    },
  };
}
// The campaign period is active AND started (D-0822-1). Editing is a campaign
// action: an evaluation may only be changed while its own period is running.
const periodIsActive = check.period_is_active === true || check.period_is_active === 't';
if (String(check.period_status) !== 'active' || !periodIsActive || !check.period_started) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'PERIOD_NOT_STARTED',
        message: 'Оценка ещё не запущена или период больше не активен',
      },
    },
  };
}

const guard = $('Run Auth Guard').first().json;
const body = guard.request.body || guard.request;
const actorId = Number(prev.actor_id);
const evalId = Number(check.id);
const grades = body.grades || {};
const comments = body.comments || {};
const generalComment = String(body.general_comment || '').replace(/'/g, "''");
const generalCommentSql = generalComment ? `'${generalComment}'` : 'NULL';

// Validate grades before building SQL — return 422, never throw.
const gradeEntries = Object.entries(grades);
if (!gradeEntries.length) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'NO_GRADES', message: 'Необходимо указать хотя бы одну оценку' },
    },
  };
}
for (const [cId, sv] of gradeEntries) {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Некорректный идентификатор критерия: ${cId}` } } };
  }
  if (!Number.isFinite(scoreValue) || scoreValue < 1 || scoreValue > 10) {
    return { json: { http_status: 422, body: { success: false, error: 'GRADE_OUT_OF_RANGE', message: `Оценка по критерию ${cId} должна быть целым числом от 1 до 10` } } };
  }
}

// ── Applicability, classification dimension only (D-0822-3) ─────────────────
const parseIdList = (raw) => {
  let value = raw;
  if (typeof value === 'string') {
    try { value = JSON.parse(value); } catch { value = []; }
  }
  return Array.isArray(value) ? value.map(Number) : [];
};
const projectCriteriaIds = parseIdList(check.project_criteria_ids);
const subjectIsProject = check.subject_is_project === true || check.subject_is_project === 't';
if (!subjectIsProject) {
  const notApplicable = gradeEntries
    .map(([cId]) => parseInt(cId, 10))
    .filter(id => projectCriteriaIds.includes(id));
  if (notApplicable.length) {
    return {
      json: {
        http_status: 422,
        body: {
          success: false,
          error: 'CRITERIA_NOT_APPLICABLE',
          message: `Критерии ${notApplicable.join(', ')} — проектные, а сотрудник сейчас не участник проекта`,
        },
      },
    };
  }
}

const scoreRows = gradeEntries.map(([cId, sv], idx) => {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  const rawComment = String(comments[cId] || '').replace(/'/g, "''");
  const commentLit = rawComment ? `'${rawComment}'` : 'NULL';
  if (idx === 0) {
    return `(${criteriaId}::integer, ${scoreValue}::integer, ${commentLit}::text)`;
  }
  return `(${criteriaId}, ${scoreValue}, ${commentLit})`;
});

// Atomic: upsert submitted scores, then delete orphan scores not in submitted list.
// Reassert evaluator ownership and the running-campaign period inline in the UPDATE
// WHERE clause to close the validation/mutation race between the prior SELECT check
// and this DML.
// removed_scores is gated on updated_header: a data-modifying WITH clause runs to
// completion whatever the outer query reads, so an ungated DELETE would still wipe
// score rows on the very race the reassertion exists to refuse (BUG-041).
// Classification exclusion is SOFT (D-0822-3): a row whose criterion is
// project_participants while the subject is currently general is NOT part of
// the presented set the evaluator edited, so its absence from score_rows is
// not a removal — the row is kept (it stops counting elsewhere and comes back
// if the classification is switched back). Deletion is reserved for criteria
// the evaluator actively removed from the currently-applicable set.
return {
  json: {
    ok: true,
    sql: `
WITH score_rows(crit_id, score_val, cmt) AS (
  VALUES ${scoreRows.join(', ')}
),
updated_header AS (
  UPDATE performance_db.evaluations
  SET calculated_score = (SELECT AVG(score_val::numeric) FROM score_rows),
      general_comment = ${generalCommentSql},
      updated_at = now()
  WHERE id = ${evalId}
    AND evaluator_id = ${actorId}
    AND EXISTS (
      SELECT 1 FROM performance_db.evaluation_periods p
      WHERE p.id = period_id
        AND p.status = 'active'
        AND p.is_active = true
        AND p.evaluation_started_at IS NOT NULL
    )
  RETURNING id, calculated_score
),
upserted_scores AS (
  INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
  SELECT uh.id, sr.crit_id, sr.score_val, sr.cmt
  FROM updated_header uh
  CROSS JOIN score_rows sr
  ON CONFLICT (evaluation_id, criteria_id) DO UPDATE
    SET score_value = EXCLUDED.score_value,
        comment     = EXCLUDED.comment
  RETURNING criteria_id
),
removed_scores AS (
  DELETE FROM performance_db.evaluation_scores es
  WHERE es.evaluation_id = ${evalId}
    AND es.criteria_id NOT IN (SELECT crit_id FROM score_rows)
    AND EXISTS (SELECT 1 FROM updated_header)
    AND NOT EXISTS (
      SELECT 1
      FROM performance_db.criteria c
      JOIN performance_db.evaluations e2 ON e2.id = ${evalId}
      JOIN performance_db.users subj ON subj.id = e2.subject_id
      WHERE c.id = es.criteria_id
        AND c.target_audience = 'project_participants'
        AND subj.is_project_participant = false
    )
  RETURNING es.criteria_id
)
SELECT
  uh.id AS evaluation_id,
  uh.calculated_score AS final_score,
  (SELECT count(*)::integer FROM upserted_scores) AS scores_saved
FROM updated_header uh
    `,
  },
};
""".strip()

UPDATE_EVAL_FORMAT = """
const prev = $('Build Update SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const rows = $input.all().map(item => item.json).filter(item => item.evaluation_id !== undefined);
if (!rows.length) {
  // CTE WHERE reassertion failed: the evaluation stopped being owned by the actor,
  // or its period stopped being a running campaign, inside the race window.
  return {
    json: {
      http_status: 403,
      body: { status: 'error', message: 'Изменение недоступно: оценка вам не принадлежит или период больше не идёт' },
    },
  };
}
const r = rows[0];
return {
  json: {
    http_status: 200,
    body: {
      status: 'success',
      message: 'Evaluation updated',
      evaluation_id: r.evaluation_id,
      final_score: parseFloat(r.final_score),
      scores_saved: r.scores_saved,
    },
  },
};
""".strip()

UPDATE_EVAL_OPTIONS_FORMAT = """
const guard = $('Run Auth Guard OPTIONS').first().json;
return {
  json: {
    http_status: guard.ok ? 204 : guard.status,
    body: {},
  },
};
""".strip()


def build_update_evaluation(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("upeval-webhook-post", "Webhook POST", "n8n-nodes-base.webhook", [-900, 0],
             {"httpMethod": "POST", "path": "api/update-evaluation",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-update-evaluation"),
        node("upeval-webhook-options", "Webhook OPTIONS", "n8n-nodes-base.webhook", [-900, 240],
             {"httpMethod": "OPTIONS", "path": "api/update-evaluation",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-update-evaluation-options"),
        # POST path guard
        node("upeval-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-680, 0], {"jsCode": guard_input_js([], "can_evaluate")}),
        run_guard_node("upeval-run-guard", "Run Auth Guard", [-450, 0], guard_workflow_id),
        node("upeval-validate", "Validate Update", "n8n-nodes-base.code",
             [-200, 0], {"jsCode": UPDATE_EVAL_VALIDATE}),
        node("upeval-check", "Execute Ownership Check", "n8n-nodes-base.postgres",
             [60, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("upeval-build", "Build Update SQL", "n8n-nodes-base.code",
             [320, 0], {"jsCode": UPDATE_EVAL_BUILD_UPDATE}),
        node("upeval-execute", "Execute Update", "n8n-nodes-base.postgres",
             [580, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS evaluation_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("upeval-format", "Format POST Response", "n8n-nodes-base.code",
             [840, 0], {"jsCode": UPDATE_EVAL_FORMAT}),
        respond_node("upeval-respond-post", "Respond POST", [1080, 0]),
        # OPTIONS path guard
        node("upeval-options-guard-input", "Prepare Guard Input OPTIONS", "n8n-nodes-base.code",
             [-680, 240], {"jsCode": guard_input_js([])}),
        run_guard_node("upeval-options-run-guard", "Run Auth Guard OPTIONS", [-450, 240], guard_workflow_id),
        node("upeval-options-format", "Format OPTIONS Response", "n8n-nodes-base.code",
             [-200, 240], {"jsCode": UPDATE_EVAL_OPTIONS_FORMAT}),
        respond_node("upeval-respond-options", "Respond OPTIONS", [60, 240]),
    ]
    connections = {
        "Webhook POST": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Validate Update"),
        "Validate Update": connect("Execute Ownership Check"),
        "Execute Ownership Check": connect("Build Update SQL"),
        "Build Update SQL": connect("Execute Update"),
        "Execute Update": connect("Format POST Response"),
        "Format POST Response": connect("Respond POST"),
        "Webhook OPTIONS": connect("Prepare Guard Input OPTIONS"),
        "Prepare Guard Input OPTIONS": connect("Run Auth Guard OPTIONS"),
        "Run Auth Guard OPTIONS": connect("Format OPTIONS Response"),
        "Format OPTIONS Response": connect("Respond OPTIONS"),
    }
    return workflow("API: Update Evaluation WITH PERIOD", nodes_list, connections)


# ── 8. POST api/self-review-submit — API: Submit Self Review ─────────────────
# Guard roles: employee/manager/hr — so admin/c_level get ROLE_FORBIDDEN.
# Period: BOTH is_active=true AND status='active'. HTTP 200.

SELF_REVIEW_VALIDATE = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
// Admin and c_level rejection is handled by the guard's ROLE_FORBIDDEN.
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request;

const finalScore = body.final_score;
const finalScoreNum = Number(finalScore);
if (finalScore === null || finalScore === undefined || finalScore === '' || !Number.isFinite(finalScoreNum)) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_SCORE', message: 'Итоговая оценка должна быть числом' },
    },
  };
}
if (finalScoreNum < 1 || finalScoreNum > 10) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'SCORE_OUT_OF_RANGE', message: 'Итоговая оценка должна быть от 1 до 10' },
    },
  };
}
// The client-supplied weighted score field is deliberately never read
// (D-0822-2). The weighted self-review value is computed in
// Build Self Review Insert, on the server, from the catalogue the client can no
// longer see. A client that still sends the field is not an error — the value
// simply has no effect.

return {
  json: {
    ok: true,
    actor_id: actorId,
    final_score: Number(finalScore),
    sql: `
      SELECT
        p.id AS period_id,
        (p.evaluation_started_at IS NOT NULL) AS period_started,
        EXISTS(
          SELECT 1 FROM performance_db.evaluations dup
          WHERE dup.subject_id = ${actorId}
            AND dup.evaluator_id = ${actorId}
            AND dup.period_id = p.id
            AND dup.is_self_evaluation = true
        ) AS is_duplicate,
        (SELECT g.coefficient
           FROM performance_db.users u
           LEFT JOIN performance_db.grades g ON g.id = u.grade_id
          WHERE u.id = ${actorId}) AS grade_coefficient,
        (SELECT u.is_project_participant
           FROM performance_db.users u
          WHERE u.id = ${actorId}) AS subject_is_project,
        COALESCE((
          SELECT json_agg(c.id)
          FROM performance_db.criteria c
          WHERE c.target_audience = 'project_participants'
        ), '[]'::json) AS project_criteria_ids,
        COALESCE((
          SELECT json_agg(json_build_object(
            'id', c.id,
            'weight', c.weight,
            'score_coefficients', COALESCE((
              SELECT json_object_agg(sc.score_level::text, sc.coefficient)
              FROM performance_db.score_coefficients sc
              WHERE sc.criteria_id = c.id
            ), '{}'::json)
          ) ORDER BY c.id)
          FROM performance_db.criteria c
          WHERE c.is_active = true
        ), '[]'::json) AS coefficients
      FROM performance_db.evaluation_periods p
      JOIN performance_db.evaluation_period_participants epp
        ON epp.period_id = p.id AND epp.user_id = ${actorId} AND epp.is_in_scope = true
      WHERE p.is_active = true AND p.status = 'active'
        AND p.period_type <> 'annual'
        AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                        WHERE child.parent_period_id = p.id)
      LIMIT 1
    `,
  },
};
""".strip()

SELF_REVIEW_BUILD_INSERT = """
const prev = $('Validate Self Review').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.first().json;

if (!check.period_id) {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'NOT_IN_SCOPE', message: 'Вы вне охвата текущего периода оценки' },
    },
  };
}
// The campaign period is active AND started (D-0822-1).
if (!check.period_started) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'PERIOD_NOT_STARTED',
        message: 'Оценка ещё не запущена: период в подготовке',
      },
    },
  };
}
if (check.is_duplicate) {
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'DUPLICATE_SELF_REVIEW', message: 'Самооценка за этот период уже отправлена' },
    },
  };
}

const guard = $('Run Auth Guard').first().json;
const body = guard.request.body || guard.request;
const actorId = Number(prev.actor_id);
const periodId = Number(check.period_id);
const finalScore = Number(prev.final_score);
const grades = body.grades || {};
const comments = body.comments || {};
const generalComment = String(body.general_comment || '').replace(/'/g, "''");
const generalCommentSql = generalComment ? `'${generalComment}'` : 'NULL';

// Validate grades before building SQL — return 422, never throw.
const gradeEntries = Object.entries(grades);
if (!gradeEntries.length) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'NO_GRADES', message: 'Необходимо указать хотя бы одну оценку' },
    },
  };
}
for (const [cId, sv] of gradeEntries) {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Некорректный идентификатор критерия: ${cId}` } } };
  }
  if (!Number.isFinite(scoreValue) || scoreValue < 1 || scoreValue > 10) {
    return { json: { http_status: 422, body: { success: false, error: 'GRADE_OUT_OF_RANGE', message: `Оценка по критерию ${cId} должна быть целым числом от 1 до 10` } } };
  }
}

// ── Applicability, classification dimension only (D-0822-3) ─────────────────
// The self-review subject is the actor. Today no project_participants
// criterion carries selfassesment, so this rejects nothing the form offers —
// it is the same single predicate every write path now enforces.
const parseIdList = (raw) => {
  let value = raw;
  if (typeof value === 'string') {
    try { value = JSON.parse(value); } catch { value = []; }
  }
  return Array.isArray(value) ? value.map(Number) : [];
};
const projectCriteriaIds = parseIdList(check.project_criteria_ids);
const actorIsProject = check.subject_is_project === true || check.subject_is_project === 't';
if (!actorIsProject) {
  const notApplicable = gradeEntries
    .map(([cId]) => parseInt(cId, 10))
    .filter(id => projectCriteriaIds.includes(id));
  if (notApplicable.length) {
    return {
      json: {
        http_status: 422,
        body: {
          success: false,
          error: 'CRITERIA_NOT_APPLICABLE',
          message: `Критерии ${notApplicable.join(', ')} — проектные, а вы сейчас не участник проекта`,
        },
      },
    };
  }
}

// ── weighted_score: computed HERE, never taken from the client (D-0822-2) ────
// Formula #2 of HANDOVER §4, reproduced from the retired client implementation
// (evaluationUtils.calculateWeightedScore, deleted from src/ in this batch — see
// git history for the original) so the stored number is identical to what the
// browser used to compute — including its guards:
//   weight   := parseFloat(criteria.weight) || 1.0
//   coef     := score_coefficients[clamp(round(score), 0, 10)] ?? 1.0
//              (the level map is filled 1..10, so level 0 falls back to 1.0)
//   unknown criterion id -> weight 1.0, coef 1.0
//   value    := (Σ score·coef·weight / Σ weight) × grade_coefficient
// The one guard NOT reproduced is `grade_coefficient || 1.0`: the subject's real
// coefficient is read from the database, and its absence is an error, not a 1.0.
let coefficientList = check.coefficients;
if (typeof coefficientList === 'string') {
  try { coefficientList = JSON.parse(coefficientList); } catch { coefficientList = []; }
}
if (!Array.isArray(coefficientList)) { coefficientList = []; }
const coefficients = coefficientList.map(row => {
  let raw = row.score_coefficients;
  if (typeof raw === 'string') {
    try { raw = JSON.parse(raw); } catch { raw = {}; }
  }
  const levels = {};
  for (let level = 1; level <= 10; level += 1) {
    const value = raw ? raw[String(level)] : undefined;
    const parsed = value === undefined || value === null ? NaN : parseFloat(value);
    levels[level] = Number.isFinite(parsed) ? parsed : 1.0;
  }
  return { id: Number(row.id), weight: parseFloat(row.weight) || 1.0, levels };
});

const gradeCoefficientRaw = check.grade_coefficient;
const gradeCoefficient = gradeCoefficientRaw === null || gradeCoefficientRaw === undefined
  ? NaN
  : Number(gradeCoefficientRaw);
if (!Number.isFinite(gradeCoefficient) || gradeCoefficient <= 0) {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'NO_GRADE_COEFFICIENT',
        message: 'У вашей учётной записи не задан грейд — обратитесь к администратору',
      },
    },
  };
}

let weightedScore;
if (!coefficients.length) {
  // calculateFinalScore fallback: plain average × grade coefficient.
  const values = gradeEntries.map(([, sv]) => parseInt(sv, 10));
  const average = values.reduce((sum, v) => sum + v, 0) / values.length;
  weightedScore = Number((average * gradeCoefficient).toFixed(2));
} else {
  let weightedSum = 0;
  let totalWeight = 0;
  for (const [cId, sv] of gradeEntries) {
    const scoreValue = parseInt(sv, 10);
    const criterion = coefficients.find(c => c.id === parseInt(cId, 10));
    const weight = criterion ? criterion.weight : 1.0;
    let scoreCoef = 1.0;
    if (criterion) {
      const level = Math.max(0, Math.min(10, Math.round(scoreValue)));
      scoreCoef = criterion.levels[level] !== undefined ? criterion.levels[level] : 1.0;
    }
    weightedSum += scoreValue * scoreCoef * weight;
    totalWeight += weight;
  }
  weightedScore = totalWeight === 0
    ? 0
    : Number(((weightedSum / totalWeight) * gradeCoefficient).toFixed(2));
}
if (!Number.isFinite(weightedScore) || weightedScore < 0) {
  return {
    json: {
      http_status: 500,
      body: {
        success: false,
        error: 'WEIGHTED_SCORE_FAILED',
        message: 'Не удалось рассчитать взвешенную самооценку',
      },
    },
  };
}

const scoreRows = gradeEntries.map(([cId, sv], idx) => {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  const rawComment = String(comments[cId] || '').replace(/'/g, "''");
  const commentLit = rawComment ? `'${rawComment}'` : 'NULL';
  if (idx === 0) {
    return `(${criteriaId}::integer, ${scoreValue}::integer, ${commentLit}::text)`;
  }
  return `(${criteriaId}, ${scoreValue}, ${commentLit})`;
});

return {
  json: {
    ok: true,
    weighted_score: weightedScore,
    grade_coefficient: gradeCoefficient,
    sql: `
WITH new_eval AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, weighted_score,
     evaluation_source, is_self_evaluation, status, general_comment, updated_at)
  VALUES (${actorId}, ${actorId}, ${periodId}, ${finalScore}, ${weightedScore},
          'self', true, 'completed', ${generalCommentSql}, now())
  ON CONFLICT (subject_id, period_id) WHERE is_self_evaluation = true DO NOTHING
  RETURNING id
),
score_rows(crit_id, score_val, cmt) AS (
  VALUES ${scoreRows.join(', ')}
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT ne.id, sr.crit_id, sr.score_val, sr.cmt
FROM new_eval ne
CROSS JOIN score_rows sr
RETURNING evaluation_id
    `,
  },
};
""".strip()

SELF_REVIEW_FORMAT = """
const prev = $('Build Self Review Insert').first().json;
if (prev.http_status) {
  return { json: prev };
}
const rows = $input.all().map(item => item.json).filter(item => item.evaluation_id !== undefined);
if (!rows.length) {
  // ON CONFLICT DO NOTHING — race duplicate
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'DUPLICATE_SELF_REVIEW', message: 'Самооценка за этот период уже была отправлена' },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: { success: true },
  },
};
""".strip()


def build_self_review_submit(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("sr-webhook", "Webhook", "n8n-nodes-base.webhook", [-900, 0],
             {"httpMethod": "POST", "path": "api/self-review-submit",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-self-review-submit"),
        node("sr-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-680, 0], {"jsCode": guard_input_js(["employee", "manager", "hr"])}),
        run_guard_node("sr-run-guard", "Run Auth Guard", [-450, 0], guard_workflow_id),
        node("sr-validate", "Validate Self Review", "n8n-nodes-base.code",
             [-200, 0], {"jsCode": SELF_REVIEW_VALIDATE}),
        node("sr-check", "Execute Scope Check", "n8n-nodes-base.postgres",
             [60, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS period_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("sr-build", "Build Self Review Insert", "n8n-nodes-base.code",
             [320, 0], {"jsCode": SELF_REVIEW_BUILD_INSERT}),
        node("sr-insert", "Execute Self Review Insert", "n8n-nodes-base.postgres",
             [580, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS evaluation_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("sr-format", "Format Response", "n8n-nodes-base.code",
             [840, 0], {"jsCode": SELF_REVIEW_FORMAT}),
        respond_node("sr-respond", "Respond", [1080, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Validate Self Review"),
        "Validate Self Review": connect("Execute Scope Check"),
        "Execute Scope Check": connect("Build Self Review Insert"),
        "Build Self Review Insert": connect("Execute Self Review Insert"),
        "Execute Self Review Insert": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Submit Self Review", nodes_list, connections)


# ── 9. GET api/evaluation-details — API: Get Evaluation Details FIXED ─────────
# Response: {status:'success', evaluation: EvaluationHeader, scores: ScoreRow[]}
# Only evaluator, admin/c_level, or the subject of their own self-review may read details.

EVAL_DETAILS_QUERY = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { status: 'error', message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const actorRole = String(guard.identity.role || '');
const request = guard.request;
const rawEvalId = parseInt(request.query?.evaluation_id || request.body?.evaluation_id, 10);
if (!Number.isFinite(rawEvalId) || rawEvalId < 1) {
  return {
    json: {
      http_status: 400,
      body: { status: 'error', message: 'Идентификатор оценки обязателен и должен быть положительным целым числом' },
    },
  };
}
const privileged = ['admin', 'c_level'].includes(actorRole);
return {
  json: {
    ok: true,
    actor_id: actorId,
    actor_role: actorRole,
    is_privileged: privileged,
    evaluation_id: rawEvalId,
    sql: `
      SELECT
        e.id AS evaluation_id,
        e.updated_at AS evaluation_date,
        e.calculated_score AS final_score,
        e.status,
        e.general_comment,
        e.private_comment,
        e.evaluation_source,
        e.is_self_evaluation,
        u_subj.id AS subject_id,
        u_subj.full_name AS subject_name,
        u_subj.job_title,
        u_subj.work_category,
        u_eval.id AS evaluator_id,
        u_eval.full_name AS evaluator_name,
        g.code AS grade_name,
        d.name AS department_name,
        es.id AS score_id,
        es.criteria_id,
        c.title AS criteria_title,
        c.description AS criteria_description,
        c.category AS criteria_category,
        es.score_value,
        es.comment AS score_comment
      FROM performance_db.evaluations e
      JOIN performance_db.users u_subj ON u_subj.id = e.subject_id
      JOIN performance_db.users u_eval ON u_eval.id = e.evaluator_id
      LEFT JOIN performance_db.grades g ON g.id = u_subj.grade_id
      LEFT JOIN performance_db.departments d ON d.id = u_subj.department_id
      LEFT JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
      LEFT JOIN performance_db.criteria c ON c.id = es.criteria_id
      WHERE e.id = ${rawEvalId}
        AND (
          ${privileged}
          OR e.evaluator_id = ${actorId}
          OR (e.subject_id = ${actorId} AND e.is_self_evaluation = true)
        )
    `,
  },
};
""".strip()

EVAL_DETAILS_FORMAT = """
const prev = $('Build Details Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const items = $input.all().map(item => item.json);
if (!items.length || !items[0].evaluation_id) {
  return {
    json: { http_status: 404, body: { status: 'error', message: 'Оценка не найдена или недоступна вам' } },
  };
}
const first = items[0];
const actorId = Number(prev.actor_id);
const isPrivileged = prev.is_privileged;
const isEvaluator = first.evaluator_id === actorId;
// For subject viewers: hide private_comment; hide evaluator identity for subordinate source
const showEvaluatorIdentity = isPrivileged || isEvaluator || first.evaluation_source !== 'subordinate';
const evaluation = {
  evaluation_id: first.evaluation_id,
  evaluation_date: first.evaluation_date,
  final_score: first.final_score,
  status: first.status,
  general_comment: first.general_comment,
  private_comment: (isPrivileged || isEvaluator) ? first.private_comment : null,
  subject_id: first.subject_id,
  subject_name: first.subject_name,
  job_title: first.job_title,
  work_category: first.work_category,
  evaluator_id: showEvaluatorIdentity ? first.evaluator_id : null,
  evaluator_name: showEvaluatorIdentity ? first.evaluator_name : null,
  grade_name: first.grade_name,
  department_name: first.department_name,
};
const scores = items
  .filter(row => row.score_id !== null && row.score_id !== undefined)
  .map(row => ({
    id: row.score_id,
    criteria_id: row.criteria_id,
    criteria_title: row.criteria_title,
    criteria_description: row.criteria_description,
    criteria_category: row.criteria_category,
    score_value: row.score_value,
    comment: row.score_comment,
  }));
return {
  json: {
    http_status: 200,
    body: { status: 'success', evaluation, scores },
  },
};
""".strip()


def build_evaluation_details(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("evdet-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/evaluation-details",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-evaluation-details"),
        node("evdet-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("evdet-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("evdet-build", "Build Details Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": EVAL_DETAILS_QUERY}),
        node("evdet-query", "Load Evaluation Data", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS evaluation_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("evdet-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": EVAL_DETAILS_FORMAT}),
        respond_node("evdet-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Details Query"),
        "Build Details Query": connect("Load Evaluation Data"),
        "Load Evaluation Data": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Get Evaluation Details FIXED", nodes_list, connections)


# ── 10. GET api/evaluation-history — API: My Evaluation History (Received) ───
# Actor as EVALUATOR (evaluations given). Fields: evaluatee_name, evaluation_date, etc.
# Response: {success: true, data: HistoryRow[]}

EVAL_HISTORY_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
// Actor is the evaluator — returns evaluations they gave (not received)
const actorId = Number(guard.identity.id);
return {
  json: {
    ok: true,
    sql: `
      SELECT
        e.id,
        e.calculated_score AS final_score,
        e.updated_at AS evaluation_date,
        e.evaluation_source,
        subject.full_name AS evaluatee_name,
        subject.job_title,
        subject.work_category,
        d.name AS department_name,
        g.code AS grade_name,
        ep.name AS period_name
      FROM performance_db.evaluations e
      JOIN performance_db.users subject ON subject.id = e.subject_id
      LEFT JOIN performance_db.departments d ON d.id = subject.department_id
      LEFT JOIN performance_db.grades g ON g.id = subject.grade_id
      LEFT JOIN performance_db.evaluation_periods ep ON ep.id = e.period_id
      WHERE e.evaluator_id = ${actorId}
        AND e.is_self_evaluation = false
      ORDER BY e.updated_at DESC
    `,
  },
};
""".strip()

EVAL_HISTORY_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const data = $input.all().map(item => item.json).filter(item => item.id !== undefined);
return {
  json: {
    http_status: 200,
    body: { success: true, data },
  },
};
""".strip()


def build_evaluation_history(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("evhist-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/evaluation-history",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-evaluation-history"),
        node("evhist-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js([])}),
        run_guard_node("evhist-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("evhist-build", "Build History Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": EVAL_HISTORY_BUILD}),
        node("evhist-query", "Load History", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("evhist-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": EVAL_HISTORY_FORMAT}),
        respond_node("evhist-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build History Query"),
        "Build History Query": connect("Load History"),
        "Load History": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: My Evaluation History (Received)", nodes_list, connections)


# ── 11. GET api/hr/evaluation-status — API: HR Evaluation Status ──────────────

HR_STATUS_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
return {
  json: {
    ok: true,
    sql: `
      WITH active_period AS (
        SELECT id FROM performance_db.evaluation_periods
        WHERE is_active = true AND status = 'active'
        LIMIT 1
      ),
      self_reviews AS (
        SELECT e.subject_id, true AS has_self_review
        FROM performance_db.evaluations e
        WHERE e.is_self_evaluation = true
          AND e.period_id = (SELECT id FROM active_period)
          AND e.status = 'completed'
      ),
      subordinate_evals AS (
        SELECT e.evaluator_id, e.subject_id
        FROM performance_db.evaluations e
        WHERE e.evaluation_source = 'manager'
          AND e.period_id = (SELECT id FROM active_period)
          AND e.status = 'completed'
      ),
      manager_evals AS (
        SELECT DISTINCT e.evaluator_id
        FROM performance_db.evaluations e
        WHERE e.evaluation_source = 'subordinate'
          AND e.period_id = (SELECT id FROM active_period)
          AND e.status = 'completed'
      ),
      in_scope AS (
        SELECT epp.user_id
        FROM performance_db.evaluation_period_participants epp
        JOIN active_period ap ON ap.id = epp.period_id
        WHERE epp.is_in_scope = true
      ),
      sub_counts AS (
        SELECT u.manager_id, COUNT(*) AS total_subordinates
        FROM performance_db.users u
        JOIN in_scope s ON s.user_id = u.id
        WHERE u.manager_id IS NOT NULL
        GROUP BY u.manager_id
      ),
      eval_counts AS (
        SELECT evaluator_id, COUNT(*) AS evaluated_count FROM subordinate_evals GROUP BY evaluator_id
      )
      SELECT
        u.id, u.full_name, u.email, u.job_title, u.role, u.has_subordinates, u.manager_id,
        d.name AS department_name,
        COALESCE(sr.has_self_review, false) AS has_self_review,
        EXISTS(SELECT 1 FROM manager_evals me WHERE me.evaluator_id = u.id) AS evaluated_manager,
        COALESCE(sc.total_subordinates, 0) AS total_subordinates,
        COALESCE(ec.evaluated_count, 0) AS evaluated_subordinates,
        CASE WHEN COALESCE(sc.total_subordinates, 0) = 0 THEN true
             ELSE COALESCE(ec.evaluated_count, 0) >= COALESCE(sc.total_subordinates, 0)
        END AS all_subordinates_evaluated,
        (SELECT COUNT(*)::integer FROM in_scope) AS in_scope_count,
        EXISTS(SELECT 1 FROM active_period) AS campaign_active
      FROM performance_db.users u
      JOIN in_scope s ON s.user_id = u.id
      LEFT JOIN performance_db.departments d ON d.id = u.department_id
      LEFT JOIN self_reviews sr ON sr.subject_id = u.id
      LEFT JOIN sub_counts sc ON sc.manager_id = u.id
      LEFT JOIN eval_counts ec ON ec.evaluator_id = u.id
      WHERE u.role NOT IN ('admin', 'hr')
      ORDER BY u.full_name
    `,
  },
};
""".strip()

HR_STATUS_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const employees = $input.all().map(item => item.json).filter(item => item.id !== undefined);
const first = employees[0];
const inScopeCount = first ? Number(first.in_scope_count) || 0 : 0;
const campaignActive = first
  ? (first.campaign_active === true || first.campaign_active === 't')
  : false;
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      employees,
      total: employees.length,
      in_scope_count: inScopeCount,
      campaign_active: campaignActive,
    },
  },
};
""".strip()


def build_hr_evaluation_status(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("hrstat-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/hr/evaluation-status",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-hr-evaluation-status"),
        node("hrstat-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["hr", "admin", "c_level"])}),
        run_guard_node("hrstat-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("hrstat-build", "Build Status Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": HR_STATUS_BUILD}),
        node("hrstat-query", "Load Status", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("hrstat-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": HR_STATUS_FORMAT}),
        respond_node("hrstat-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Status Query"),
        "Build Status Query": connect("Load Status"),
        "Load Status": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: HR Evaluation Status", nodes_list, connections)


# ── 12. GET api/score-coefficients — API: Get Score Coefficients ──────────────
# Response: {success: true, data: [{id, title, weight, is_active, score_coefficients: {"1":x,...}}]}
# ADMIN + C_LEVEL, read only (ROLE_ACCESS_HR_CLEVEL, 2026-08-26). D-0822-2 made
# this admin-only after every employee read the whole weight + level-coefficient
# table while filling in a self-review; the weighted self-review value is now
# computed on the server, and that stays. C-level is added back as a READER
# because the owner granted C-level the money-read screens (/admin/final-scores,
# /admin/score-calculator), both of which consume this route. HR and every other
# role still get 403; the POST save route below remains admin-only.

SCORE_COEFF_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
return {
  json: {
    ok: true,
    sql: `
      SELECT c.id, c.title, c.weight, c.is_active,
        COALESCE(
          (SELECT json_agg(json_build_object('score_level', sc.score_level, 'coefficient', sc.coefficient) ORDER BY sc.score_level)
           FROM performance_db.score_coefficients sc WHERE sc.criteria_id = c.id),
          '[]'::json
        ) AS score_coefficients_raw
      FROM performance_db.criteria c
      WHERE c.is_active = true
      ORDER BY c.id ASC
    `,
  },
};
""".strip()

SCORE_COEFF_FORMAT = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const rows = $input.all().map(item => item.json).filter(item => item.id !== undefined);
const data = rows.map(row => {
  let rawCoeffs = row.score_coefficients_raw;
  if (typeof rawCoeffs === 'string') {
    try { rawCoeffs = JSON.parse(rawCoeffs); } catch { rawCoeffs = []; }
  }
  const coeffMap = {};
  for (let i = 1; i <= 10; i++) {
    const found = rawCoeffs.find(c => c.score_level === i);
    coeffMap[i] = found ? parseFloat(found.coefficient) : 1.0;
  }
  return {
    id: row.id,
    title: row.title,
    weight: parseFloat(row.weight) || 1.0,
    is_active: row.is_active,
    score_coefficients: coeffMap,
  };
});
return {
  json: {
    http_status: 200,
    body: { success: true, data },
  },
};
""".strip()


def build_score_coefficients(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("scorecoeff-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/score-coefficients",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-score-coefficients-get"),
        node("scorecoeff-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("scorecoeff-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("scorecoeff-build", "Build Coefficients Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": SCORE_COEFF_BUILD}),
        node("scorecoeff-query", "Load Coefficients", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("scorecoeff-format", "Format Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": SCORE_COEFF_FORMAT}),
        respond_node("scorecoeff-respond", "Respond", [740, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Coefficients Query"),
        "Build Coefficients Query": connect("Load Coefficients"),
        "Load Coefficients": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Get Score Coefficients", nodes_list, connections)


# ── 13. POST api/score-coefficients — API: Save Score Coefficients ────────────
# Request: {criteria: [{id, weight, score_coefficients: {"1":x,...,"10":x}}]}
# Response: {success: true, message: 'Score coefficients saved successfully'}
# Admin only. NO period freeze (D-0822-2): weights and level coefficients stay
# editable until the period is closed. A closed period is immune because its
# numbers live in period_results and no reporting surface re-joins these tables.
# Write validation: every weight finite and >= 0.1 (the client input's `min` is a
# browser hint and is bypassed by a direct request; a zero weight is read back as
# 1.0 and inflates the bonus index — BUG-029), every coefficient finite and > 0,
# levels exactly 1..10.

SAVE_COEFF_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const criteria = body.criteria;
if (!Array.isArray(criteria) || !criteria.length) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_BODY', message: 'Список критериев не должен быть пустым' },
    },
  };
}
// Build batched SQL: update weights and upsert coefficients for each criterion
const sqls = [];
for (const crit of criteria) {
  const criteriaId = parseInt(crit.id, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Некорректный идентификатор критерия: ${crit.id}` },
      },
    };
  }
  // A zero weight does NOT remove a criterion from the bonus index: every
  // consumer reads it back through `parseFloat(weight) || 1.0`, so the criterion
  // silently counts with weight 1.0 — the opposite of what the admin asked for,
  // in the money number, and frozen into period_results at close (BUG-029).
  // The floor is 0.1 (D-0822-2 as amended 2026-08-22): approved by Alexander,
  // mirroring the client input min="0.1" (CoefficientRow.jsx / AdminScoring.jsx),
  // so the server and the form refuse the same values.
  const MIN_WEIGHT = 0.1;
  const weight = parseFloat(crit.weight);
  if (!Number.isFinite(weight) || weight < MIN_WEIGHT) {
    return {
      json: {
        http_status: 422,
        body: {
          success: false,
          error: 'INVALID_WEIGHT',
          message: `Вес критерия ${criteriaId} должен быть числом не меньше 0.1. ` +
            `Чтобы критерий не влиял на бонус, отключите его (is_active), а не занижайте вес: ` +
            `вес 0 читается как 1.0 и критерий всё равно попадёт в расчёт`,
        },
      },
    };
  }
  const coeffMap = crit.score_coefficients;
  if (!coeffMap || typeof coeffMap !== 'object' || Array.isArray(coeffMap)) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_COEFFICIENT_MAP', message: `Не переданы коэффициенты уровней для критерия ${criteriaId}` },
      },
    };
  }
  for (const key of Object.keys(coeffMap)) {
    const level = parseInt(key, 10);
    if (!Number.isFinite(level) || String(level) !== String(key).trim() || level < 1 || level > 10) {
      return {
        json: {
          http_status: 422,
          body: {
            success: false,
            error: 'INVALID_COEFFICIENT_LEVEL',
            message: `Уровень оценки «${key}» вне диапазона 1..10 (критерий ${criteriaId})`,
          },
        },
      };
    }
  }
  sqls.push(`UPDATE performance_db.criteria SET weight = ${weight} WHERE id = ${criteriaId};`);
  for (let level = 1; level <= 10; level++) {
    const raw = coeffMap[level] !== undefined ? coeffMap[level] : coeffMap[String(level)];
    const coef = raw === undefined || raw === null || raw === '' ? NaN : parseFloat(raw);
    if (!Number.isFinite(coef) || coef <= 0) {
      return {
        json: {
          http_status: 422,
          body: {
            success: false,
            error: 'INVALID_COEFFICIENT',
            message: `Коэффициент уровня ${level} критерия ${criteriaId} должен быть конечным числом больше нуля`,
          },
        },
      };
    }
    sqls.push(
      `INSERT INTO performance_db.score_coefficients (criteria_id, score_level, coefficient) ` +
      `VALUES (${criteriaId}, ${level}, ${coef}) ` +
      `ON CONFLICT (criteria_id, score_level) DO UPDATE SET coefficient = EXCLUDED.coefficient;`
    );
  }
}
return {
  json: {
    ok: true,
    query: sqls.join('\\n'),
  },
};
""".strip()

SAVE_COEFF_FORMAT = """
const prev = $('Build Coefficients Update').first().json;
if (prev.http_status) {
  return { json: prev };
}
return {
  json: {
    http_status: 200,
    body: { success: true, message: 'Score coefficients saved successfully' },
  },
};
""".strip()


def build_save_score_coefficients(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("savecoeff-webhook", "Webhook", "n8n-nodes-base.webhook", [-900, 0],
             {"httpMethod": "POST", "path": "api/score-coefficients",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-score-coefficients-post"),
        node("savecoeff-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-680, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("savecoeff-run-guard", "Run Auth Guard", [-450, 0], guard_workflow_id),
        node("savecoeff-build", "Build Coefficients Update", "n8n-nodes-base.code",
             [320, 0], {"jsCode": SAVE_COEFF_BUILD}),
        node("savecoeff-execute", "Execute Update", "n8n-nodes-base.postgres",
             [580, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.query : 'SELECT 1 WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("savecoeff-format", "Format Response", "n8n-nodes-base.code",
             [840, 0], {"jsCode": SAVE_COEFF_FORMAT}),
        respond_node("savecoeff-respond", "Respond", [1080, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Coefficients Update"),
        "Build Coefficients Update": connect("Execute Update"),
        "Execute Update": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Save Score Coefficients", nodes_list, connections)


# ── 14. POST api/admin/create-invite — API: Create Invite ─────────────────────
# Actor from guard (body admin_id ignored for auth). Crypto-random token. HTTPS link. HTTP 200.

CREATE_INVITE_BUILD = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
// Actor from guard; ignore body admin_id and body frontend_url for security
const actorId = Number(guard.identity.id);
const frontendUrl = String($env.EPE_FRONTEND_URL || '').replace(/\\/$/, '');
if (!/^https:\\/\\/[^/]+/i.test(frontendUrl)) {
  return {
    json: {
      http_status: 500,
      body: {
        success: false,
        error: 'CONFIG_ERROR',
        message: 'EPE_FRONTEND_URL must be configured with an HTTPS origin',
      },
    },
  };
}
return {
  json: {
    ok: true,
    actor_id: actorId,
    frontend_url: frontendUrl,
    sql: `
      SELECT id, token, created_at, expires_at
      FROM performance_db.invite_tokens
      WHERE COALESCE(is_used, false) = false
        AND expires_at > now()
      ORDER BY created_at DESC
      LIMIT 1
    `,
  },
};
""".strip()

CREATE_INVITE_BUILD_TOKEN = """
const prev = $('Build Invite Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const existing = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (existing) {
  const registrationLink = `${prev.frontend_url}/register?token=${existing.token}`;
  return {
    json: {
      http_status: 200,
      body: {
        success: true,
        data: {
          id: existing.id,
          token: existing.token,
          registration_link: registrationLink,
          created_at: existing.created_at,
          expires_at: existing.expires_at,
          is_new: false,
        },
        message: 'Existing invite token returned',
      },
    },
  };
}
// Generate cryptographically random token
const crypto = require('crypto');
const rawToken = crypto.randomBytes(32).toString('base64url');
const actorId = Number(prev.actor_id);
const registrationLink = `${prev.frontend_url}/register?token=${rawToken}`;
return {
  json: {
    ok: true,
    frontend_url: prev.frontend_url,
    registration_link: registrationLink,
    token: rawToken,
    sql: `
      INSERT INTO performance_db.invite_tokens (token, created_by, expires_at)
      VALUES ('${rawToken}', ${actorId}, now() + interval '30 days')
      RETURNING id, token, created_at, expires_at
    `,
  },
};
""".strip()

CREATE_INVITE_FORMAT = """
const prev = $('Build Token or Return Existing').first().json;
if (prev.http_status) {
  return { json: prev };
}
if (!prev.ok) {
  return { json: { http_status: 500, body: { success: false, error: 'UNEXPECTED', message: 'Unexpected state' } } };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: { http_status: 500, body: { success: false, error: 'INSERT_FAILED', message: 'Failed to create invite token' } },
  };
}
const registrationLink = `${prev.frontend_url}/register?token=${row.token}`;
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      data: {
        id: row.id,
        token: row.token,
        registration_link: registrationLink,
        created_at: row.created_at,
        expires_at: row.expires_at,
        is_new: true,
      },
      message: 'Invite token created successfully',
    },
  },
};
""".strip()


def build_create_invite(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("invite-webhook", "Webhook", "n8n-nodes-base.webhook", [-900, 0],
             {"httpMethod": "POST", "path": "api/admin/create-invite",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-create-invite"),
        node("invite-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-680, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("invite-run-guard", "Run Auth Guard", [-450, 0], guard_workflow_id),
        node("invite-build", "Build Invite Query", "n8n-nodes-base.code",
             [-200, 0], {"jsCode": CREATE_INVITE_BUILD}),
        node("invite-check", "Find Existing Token", "n8n-nodes-base.postgres",
             [60, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("invite-token-build", "Build Token or Return Existing", "n8n-nodes-base.code",
             [320, 0], {"jsCode": CREATE_INVITE_BUILD_TOKEN}),
        node("invite-insert", "Insert Token", "n8n-nodes-base.postgres",
             [580, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("invite-format", "Format Response", "n8n-nodes-base.code",
             [840, 0], {"jsCode": CREATE_INVITE_FORMAT}),
        respond_node("invite-respond", "Respond", [1080, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Invite Query"),
        "Build Invite Query": connect("Find Existing Token"),
        "Find Existing Token": connect("Build Token or Return Existing"),
        "Build Token or Return Existing": connect("Insert Token"),
        "Insert Token": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Create Invite", nodes_list, connections)


# ── 15. GET api/admin-users-data — API: Admin Get Users Data ──────────────────
# Response: {users: AdminUser[], options: {departments, grades, managers}}
# Users include is_project_participant. Sequential multi-query + merge.
# Readers: admin + hr + c_level (ROLE_ACCESS_HR_CLEVEL, 2026-08-26) — this is
# the feed of the «Сотрудники» roster, which HR and C-level open read-only.
# The users SQL selects no compensation column (salary_current/salary_proposed
# never leave the database on this route, any role). The one money input in the
# payload is options.grades[].coefficient: admin and c_level keep it (the money
# screens they may read consume it via this route), HR receives grades as
# {id, code} only — D-0822-2 still holds for HR. Every write stays admin-only.

ADMIN_USERS_BUILD_QUERY = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
return {
  json: {
    ok: true,
    users_sql: `
      WITH active_period AS (
        SELECT id, name FROM performance_db.evaluation_periods
        WHERE is_active = true AND status = 'active' LIMIT 1
      ),
      in_scope AS (
        SELECT epp.user_id
        FROM performance_db.evaluation_period_participants epp
        JOIN active_period ap ON ap.id = epp.period_id
        WHERE epp.is_in_scope = true
      ),
      -- Manager-path applicable set: same predicate as /api/employees
      -- evaluated_by_actor (D-0822-3). c_level_direct is a shared channel
      -- and is deliberately not in these campaign counters.
      manager_applicable AS (
        SELECT u.id AS subject_id, c.id AS criteria_id
        FROM performance_db.users u
        JOIN performance_db.criteria c
          ON c.is_active = true AND c.c_level_only = false
        WHERE (c.target_audience <> 'project_participants' OR u.is_project_participant = true)
          AND (c.target_audience <> 'managers_only' OR u.has_subordinates = true)
      ),
      manager_scored AS (
        SELECT e.evaluator_id, e.subject_id, es.criteria_id
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
        JOIN active_period ap ON ap.id = e.period_id
        WHERE e.is_self_evaluation = false
          AND e.evaluation_source = 'manager'
      ),
      manager_eval_complete AS (
        SELECT ms.evaluator_id, ms.subject_id
        FROM manager_applicable ma
        JOIN manager_scored ms
          ON ms.subject_id = ma.subject_id AND ms.criteria_id = ma.criteria_id
        GROUP BY ms.evaluator_id, ms.subject_id
        HAVING count(*) = (
          SELECT count(*) FROM manager_applicable ma2
          WHERE ma2.subject_id = ms.subject_id
        )
      ),
      upward_done AS (
        SELECT e.evaluator_id, e.subject_id
        FROM performance_db.evaluations e
        JOIN active_period ap ON ap.id = e.period_id
        WHERE e.evaluation_source = 'subordinate'
      )
      SELECT
        u.id, u.full_name, u.email, u.role, u.work_category, u.is_project_participant,
        u.job_title, u.manager_id, u.department_id, u.grade_id, u.has_subordinates,
        u.can_evaluate, u.can_be_evaluated,
        (u.password_hash IS NOT NULL) AS is_registered,
        -- D-0825-11 / D-0825-12. The evaluation state of the row, for the period
        -- the admin is looking at. Text, never a date object (BUG-031).
        to_char(u.join_date, 'YYYY-MM-DD') AS join_date,
        -- LEFT JOIN, not JOIN: a person with no participants row (BUG-067) must
        -- stay on this page and be visibly distinguishable from an excluded one,
        -- and the whole page must not empty out when no period is active.
        epp.is_in_scope AS period_is_in_scope,
        epp.exclusion_reason AS period_exclusion_reason,
        epp.scope_override AS period_scope_override,
        (epp.user_id IS NOT NULL) AS has_period_row,
        (SELECT id FROM active_period) AS period_id,
        COALESCE((
          SELECT json_agg(
            json_build_object(
              'period_id', p.id,
              'period_name', p.name,
              'period_type', p.period_type,
              'period_status', p.status,
              'start_date', to_char(p.start_date, 'YYYY-MM-DD'),
              'end_date', to_char(p.end_date, 'YYYY-MM-DD'),
              'scope_cutoff_date', to_char(
                (date_trunc('month', p.end_date)::date
                  - interval '2 months' - interval '1 day')::date,
                'YYYY-MM-DD'
              ),
              'has_period_row', pp.user_id IS NOT NULL,
              'is_in_scope', pp.is_in_scope,
              'exclusion_reason', pp.exclusion_reason,
              'scope_override', pp.scope_override
            )
            ORDER BY p.start_date, p.id
          )
          FROM performance_db.evaluation_periods p
          LEFT JOIN performance_db.evaluation_period_participants pp
            ON pp.period_id = p.id AND pp.user_id = u.id
        ), '[]'::json) AS period_scopes,
        -- D-0825-7. Both are text, never a date object: a date column crossing
        -- the n8n Postgres node is UTC-serialised and can shift a calendar day
        -- (BUG-031). The page filters on terminated_at being non-null and shows
        -- termination_date verbatim.
        to_char(u.terminated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS terminated_at,
        to_char(u.termination_date, 'YYYY-MM-DD') AS termination_date,
        d.name AS department_name,
        g.code AS grade_name,
        m.full_name AS manager_name,
        m.role AS manager_role,
        m.can_evaluate AS manager_can_evaluate,
        (SELECT name FROM active_period) AS period_name,
        COALESCE(
          (SELECT CASE WHEN e.status = 'completed' THEN true ELSE false END
           FROM performance_db.evaluations e
           WHERE e.subject_id = u.id
             AND e.is_self_evaluation = true
             AND e.period_id = (SELECT id FROM active_period)
           LIMIT 1),
          false
        ) AS self_review_done,
        (SELECT e.status
         FROM performance_db.evaluations e
         WHERE e.subject_id = u.id
           AND e.is_self_evaluation = false
           AND e.period_id = (SELECT id FROM active_period)
         LIMIT 1
        ) AS manager_review_status,
        EXISTS (
          SELECT 1 FROM upward_done ud
          WHERE ud.evaluator_id = u.id AND ud.subject_id = u.manager_id
        ) AS has_evaluated_manager,
        (
          SELECT count(*)::integer
          FROM performance_db.users sub
          JOIN in_scope ss ON ss.user_id = sub.id
          WHERE sub.manager_id = u.id AND sub.can_be_evaluated = true
        ) AS assigned_subordinate_count,
        (
          SELECT count(*)::integer
          FROM manager_eval_complete mec
          JOIN performance_db.users sub ON sub.id = mec.subject_id
          JOIN in_scope ss ON ss.user_id = sub.id
          WHERE mec.evaluator_id = u.id
            AND sub.manager_id = u.id
            AND sub.can_be_evaluated = true
        ) AS completed_subordinate_count,
        EXISTS (
          SELECT 1 FROM manager_eval_complete mec
          WHERE mec.subject_id = u.id AND mec.evaluator_id = u.manager_id
        ) AS received_manager_eval_complete,
        CASE WHEN u.role IN ('admin', 'c_level') THEN 0 ELSE (
          SELECT count(*)::integer
          FROM performance_db.users sub
          JOIN in_scope ss ON ss.user_id = sub.id
          WHERE sub.manager_id = u.id
        ) END AS expected_upward_count,
        CASE WHEN u.role IN ('admin', 'c_level') THEN 0 ELSE (
          SELECT count(*)::integer
          FROM upward_done ud
          JOIN performance_db.users sub ON sub.id = ud.evaluator_id
          JOIN in_scope ss ON ss.user_id = sub.id
          WHERE ud.subject_id = u.id AND sub.manager_id = u.id
        ) END AS received_upward_count
      FROM performance_db.users u
      LEFT JOIN performance_db.departments d ON d.id = u.department_id
      LEFT JOIN performance_db.grades g ON g.id = u.grade_id
      LEFT JOIN performance_db.users m ON m.id = u.manager_id
      LEFT JOIN performance_db.evaluation_period_participants epp
        ON epp.user_id = u.id
       AND epp.period_id = (SELECT id FROM active_period)
      ORDER BY u.id DESC
    `,
    depts_sql: `SELECT id, name FROM performance_db.departments ORDER BY name`,
    grades_sql: `SELECT id, code, coefficient FROM performance_db.grades ORDER BY code`,
  },
};
""".strip()

ADMIN_USERS_LOAD_USERS = """
const prev = $('Build Users Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
return { json: { ok: true, sql: prev.users_sql, depts_sql: prev.depts_sql, grades_sql: prev.grades_sql } };
""".strip()

ADMIN_USERS_LOAD_DEPTS = """
const prev = $('Load Users').first().json;
if (prev.http_status) {
  return { json: prev };
}
return { json: { ok: true, sql: prev.depts_sql, grades_sql: prev.grades_sql } };
""".strip()

ADMIN_USERS_LOAD_GRADES = """
const prev = $('Load Depts').first().json;
if (prev.http_status) {
  return { json: prev };
}
return { json: { ok: true, sql: prev.grades_sql } };
""".strip()

ADMIN_USERS_MERGE = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
// Read from Postgres result nodes, not the relay Code nodes that only carry SQL strings.
const rawUsers = $('Query Users').all().map(i => i.json);
const rawDepts = $('Query Depts').all().map(i => i.json);
const rawGrades = $('Query Grades').all().map(i => i.json);

function dedup(arr) {
  const seen = new Map();
  arr.forEach(item => { if (item.id) seen.set(item.id, item); });
  return Array.from(seen.values());
}

const users = dedup(rawUsers);
const departments = dedup(rawDepts);
// Grade coefficients are a money input (D-0822-2). Admin and c_level read them
// here because the money screens they may open feed from this route; HR reads
// this roster but never a money input, so HR gets {id, code} only.
const actorRole = String(guard.identity.role || '');
const grades = dedup(rawGrades).map(g =>
  actorRole === 'hr' ? { id: g.id, code: g.code } : g
);
// A terminated person is never offered as somebody's manager (D-0825-7):
// pointing a live employee at them would leave that employee evaluated by
// nobody, because a terminated manager is out of scope and gets no task list.
// The users array itself is NOT filtered — the page needs the terminated rows
// to show them behind its filter and to offer reinstatement.
const managers = users
  .filter(u => u.role !== 'employee' && !u.terminated_at)
  .map(u => ({ id: u.id, name: u.full_name }));

return {
  json: {
    http_status: 200,
    body: { users, options: { departments, grades, managers } },
  },
};
""".strip()


def build_admin_users_data(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("adminusers-webhook", "Webhook", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "GET", "path": "api/admin-users-data",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-admin-users-data"),
        node("adminusers-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin", "hr", "c_level"])}),
        run_guard_node("adminusers-run-guard", "Run Auth Guard", [-250, 0], guard_workflow_id),
        node("adminusers-build", "Build Users Query", "n8n-nodes-base.code",
             [0, 0], {"jsCode": ADMIN_USERS_BUILD_QUERY}),
        # Chain: build query → pass sql down → load users → load depts → load grades → merge
        node("adminusers-pass-users", "Load Users", "n8n-nodes-base.code",
             [250, 0], {"jsCode": ADMIN_USERS_LOAD_USERS}),
        node("adminusers-query-users", "Query Users", "n8n-nodes-base.postgres",
             [500, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("adminusers-pass-depts", "Load Depts", "n8n-nodes-base.code",
             [750, 0], {"mode": "runOnceForAllItems", "jsCode": ADMIN_USERS_LOAD_DEPTS}),
        node("adminusers-query-depts", "Query Depts", "n8n-nodes-base.postgres",
             [1000, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("adminusers-pass-grades", "Load Grades", "n8n-nodes-base.code",
             [1250, 0], {"mode": "runOnceForAllItems", "jsCode": ADMIN_USERS_LOAD_GRADES}),
        node("adminusers-query-grades", "Query Grades", "n8n-nodes-base.postgres",
             [1500, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("adminusers-merge", "Merge and Format", "n8n-nodes-base.code",
             [1750, 0], {"mode": "runOnceForAllItems", "jsCode": ADMIN_USERS_MERGE}),
        respond_node("adminusers-respond", "Respond", [2000, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Users Query"),
        "Build Users Query": connect("Load Users"),
        "Load Users": connect("Query Users"),
        "Query Users": connect("Load Depts"),
        "Load Depts": connect("Query Depts"),
        "Query Depts": connect("Load Grades"),
        "Load Grades": connect("Query Grades"),
        "Query Grades": connect("Merge and Format"),
        "Merge and Format": connect("Respond"),
    }
    return workflow("API: Admin Get Users Data", nodes_list, connections)


# ── 16. POST admin/save-user — API: Admin Save User (GUI Mode) ────────────────
# Response: {success: true, user: <row>}
# H1: only 'general' and 'project' allowed for work_category.

SAVE_USER_VALIDATE = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
// Actor identity comes from guard — body admin_id is ignored for authorization.
const actorId = Number(guard.identity.id);
if (!Number.isFinite(actorId) || actorId < 1) {
  return {
    json: {
      http_status: 500,
      body: { success: false, error: 'INVALID_ACTOR', message: 'Сервер авторизации не вернул корректный actor_id' },
    },
  };
}
const body = guard.request.body || guard.request;
// H1: only general and project allowed
const VALID_WORK_CATEGORIES = ['general', 'project'];
const VALID_ROLES = ['admin', 'c_level', 'manager', 'employee', 'hr'];

const cleanId = (v) => {
  if (v === '' || v == null || v === 'null') return null;
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : null;
};
const userId = cleanId(body.id);
const isNew = userId === null;

// Existing users are a full-row write. Missing role/work_category used to fall
// through to employee/general and could silently change both access and money.
// The client reloads the live row immediately before POST; the server refuses a
// partial body as the second line of defence.
const FULL_ROW_FIELDS = [
  'full_name', 'email', 'role', 'work_category', 'job_title',
  'department_id', 'grade_id', 'manager_id', 'join_date',
];
if (!isNew) {
  const missing = FULL_ROW_FIELDS.filter((field) => !Object.prototype.hasOwnProperty.call(body, field));
  if (missing.length) {
    return {
      json: {
        http_status: 422,
        body: {
          success: false,
          error: 'INCOMPLETE_USER_ROW',
          message: `Карточка не сохранена: передана не вся актуальная строка (${missing.join(', ')})`,
          missing_fields: missing,
        },
      },
    };
  }
}

const workCategory = String(
  Object.prototype.hasOwnProperty.call(body, 'work_category') ? body.work_category : 'general'
).trim();
if (!VALID_WORK_CATEGORIES.includes(workCategory)) {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'INVALID_WORK_CATEGORY',
        message: `Категория работы должна быть одной из: ${VALID_WORK_CATEGORIES.join(', ')}`,
      },
    },
  };
}
const role = String(
  Object.prototype.hasOwnProperty.call(body, 'role') ? body.role : 'employee'
).trim();
if (!VALID_ROLES.includes(role)) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_ROLE', message: `Роль должна быть одной из: ${VALID_ROLES.join(', ')}` },
    },
  };
}
const fullName = String(body.full_name || '').trim();
const email = String(body.email || '').trim().toLowerCase();
const jobTitle = String(body.job_title || '').trim();

if (!fullName || fullName.length > 150) {
  return {
    json: { http_status: 422, body: { success: false, error: 'INVALID_NAME', message: 'Укажите имя сотрудника длиной не более 150 символов' } },
  };
}
if (!email || email.length > 150) {
  return {
    json: { http_status: 422, body: { success: false, error: 'INVALID_EMAIL', message: 'Укажите email длиной не более 150 символов' } },
  };
}

const departmentId = cleanId(body.department_id);
const gradeId = cleanId(body.grade_id);
const managerId = cleanId(body.manager_id);
const isProjectParticipant = workCategory === 'project';
const rawJoinDate = body.join_date == null ? '' : String(body.join_date).trim();
if (rawJoinDate && !/^\\d{4}-\\d{2}-\\d{2}$/.test(rawJoinDate)) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_JOIN_DATE', message: 'Дата приёма должна быть в формате ГГГГ-ММ-ДД или пустой' },
    },
  };
}
if (rawJoinDate) {
  const parsed = new Date(`${rawJoinDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== rawJoinDate) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_JOIN_DATE', message: 'Укажите существующую календарную дату приёма' },
      },
    };
  }
}

const safeFullName = fullName.replace(/'/g, "''");
const safeEmail = email.replace(/'/g, "''");
const safeJobTitle = jobTitle.replace(/'/g, "''");

const departmentSql = departmentId !== null ? String(departmentId) : 'NULL';
const gradeSql = gradeId !== null ? String(gradeId) : 'NULL';
const managerSql = managerId !== null ? String(managerId) : 'NULL';
const jobTitleSql = safeJobTitle ? `'${safeJobTitle}'` : 'NULL';
const joinDateSql = rawJoinDate ? `'${rawJoinDate}'::date` : 'NULL';

// Classification (project/general) stays editable during a running campaign
// (D-0822-3). The classification freeze 409 is gone: a switch never destroys
// evaluation data — score rows for no-longer-applicable criteria stay in the
// database and stop counting; the matrix, the close dataset and the write
// validation all read the CURRENT value of is_project_participant.
return {
  json: {
    ok: true,
    actor_id: actorId,
    is_new: isNew,
    user_id: userId,
    work_category: workCategory,
    is_project_participant: isProjectParticipant,
    full_name: safeFullName,
    email: safeEmail,
    role,
    job_title_sql: jobTitleSql,
    department_sql: departmentSql,
    grade_sql: gradeSql,
    manager_sql: managerSql,
    join_date_sql: joinDateSql,
  },
};
""".strip()

SAVE_USER_BUILD_UPSERT = """
const prev = $('Validate User Data').first().json;
if (prev.http_status) {
  return { json: prev };
}

const userId = prev.user_id;
const isNew = prev.is_new;
const isProjectParticipant = prev.is_project_participant;
const actorId = Number(prev.actor_id);

let sql;
if (isNew) {
  sql = `
WITH inserted AS (
  INSERT INTO performance_db.users
    (full_name, email, role, job_title, work_category, is_project_participant,
     department_id, grade_id, manager_id, join_date, created_at)
  VALUES
    ('${prev.full_name}', '${prev.email}', '${prev.role}', ${prev.job_title_sql},
     '${prev.work_category}', ${isProjectParticipant},
     ${prev.department_sql}, ${prev.grade_sql}, ${prev.manager_sql}, ${prev.join_date_sql}, now())
  RETURNING *
),
logged AS (
  INSERT INTO performance_db.employee_card_events
    (user_id, actor_id, event_type, changes)
  SELECT
    i.id,
    ${actorId},
    'created',
    jsonb_build_object(
      'full_name', jsonb_build_object('old', NULL, 'new', i.full_name),
      'email', jsonb_build_object('old', NULL, 'new', i.email),
      'role', jsonb_build_object('old', NULL, 'new', i.role),
      'job_title', jsonb_build_object('old', NULL, 'new', i.job_title),
      'work_category', jsonb_build_object('old', NULL, 'new', i.work_category),
      'department_id', jsonb_build_object('old', NULL, 'new', i.department_id),
      'grade_id', jsonb_build_object('old', NULL, 'new', i.grade_id),
      'manager_id', jsonb_build_object('old', NULL, 'new', i.manager_id),
      'join_date', jsonb_build_object('old', NULL, 'new', to_char(i.join_date, 'YYYY-MM-DD'))
    )
  FROM inserted i
  RETURNING id
)
SELECT
  true AS target_found,
  false AS blocked,
  row_to_json(i) AS saved_user,
  '[]'::json AS scope_results,
  (SELECT id FROM logged LIMIT 1) AS card_event_id
FROM inserted i
  `;
} else {
  sql = `
WITH target AS (
  SELECT u.*
  FROM performance_db.users u
  WHERE u.id = ${userId}
  FOR UPDATE
),
period_state AS (
  SELECT
    p.id AS period_id,
    p.name AS period_name,
    p.status AS period_status,
    p.period_type,
    p.end_date,
    epp.user_id IS NOT NULL AS row_exists,
    epp.is_in_scope AS old_is_in_scope,
    epp.exclusion_reason AS old_reason,
    epp.scope_override,
    t.terminated_at IS NOT NULL AS user_terminated,
    t.join_date IS DISTINCT FROM ${prev.join_date_sql} AS join_date_changed,
    CASE
      WHEN ${prev.join_date_sql} IS NULL THEN false
      WHEN ${prev.join_date_sql} >
           ((date_trunc('month', p.end_date)::date - interval '2 months' - interval '1 day')::date)
        THEN false
      ELSE true
    END AS desired_is_in_scope,
    CASE
      WHEN ${prev.join_date_sql} IS NULL THEN 'join_date_missing'
      WHEN ${prev.join_date_sql} >
           ((date_trunc('month', p.end_date)::date - interval '2 months' - interval '1 day')::date)
        THEN 'insufficient_tenure'
      ELSE NULL
    END AS desired_reason,
    (SELECT count(*)::integer FROM performance_db.evaluations e
      WHERE e.period_id = p.id AND e.subject_id = ${userId}
        AND e.is_self_evaluation = false) AS evaluations_received,
    (SELECT count(*)::integer FROM performance_db.evaluations e
      WHERE e.period_id = p.id AND e.subject_id = ${userId}
        AND e.is_self_evaluation = true) AS self_reviews,
    (SELECT count(*)::integer FROM performance_db.evaluations e
      WHERE e.period_id = p.id AND e.evaluator_id = ${userId}
        AND e.is_self_evaluation = false) AS evaluations_given,
    (SELECT count(*)::integer FROM performance_db.score_corrections sc
      WHERE sc.period_id = p.id AND sc.subject_id = ${userId}) AS corrections_about
  FROM performance_db.evaluation_periods p
  CROSS JOIN target t
  LEFT JOIN performance_db.evaluation_period_participants epp
    ON epp.period_id = p.id AND epp.user_id = t.id
),
eligible AS (
  SELECT ps.*
  FROM period_state ps
  WHERE ps.period_status <> 'closed'
    AND ps.row_exists
    AND NOT ps.user_terminated
    AND ps.scope_override IS NULL
    AND (ps.old_reason IS NULL OR ps.old_reason IN (
      'join_date_missing', 'hired_after_period_end', 'insufficient_tenure'
    ))
),
blocked_periods AS (
  SELECT *
  FROM eligible e
  WHERE e.join_date_changed
    AND e.old_is_in_scope = true
    AND e.desired_is_in_scope = false
    AND (
      e.evaluations_received + e.self_reviews
      + e.evaluations_given + e.corrections_about
    ) > 0
),
updated AS (
  UPDATE performance_db.users u
  SET full_name = '${prev.full_name}',
      email = '${prev.email}',
      role = '${prev.role}',
      job_title = ${prev.job_title_sql},
      work_category = '${prev.work_category}',
      is_project_participant = ${isProjectParticipant},
      department_id = ${prev.department_sql},
      grade_id = ${prev.grade_sql},
      manager_id = ${prev.manager_sql},
      join_date = ${prev.join_date_sql}
  FROM target t
  WHERE u.id = t.id
    AND NOT EXISTS (SELECT 1 FROM blocked_periods)
  RETURNING u.*
),
scope_changed AS (
  UPDATE performance_db.evaluation_period_participants epp
  SET is_in_scope = e.desired_is_in_scope,
      exclusion_reason = e.desired_reason,
      updated_at = now()
  FROM eligible e
  WHERE epp.period_id = e.period_id
    AND epp.user_id = ${userId}
    AND e.join_date_changed
    AND EXISTS (SELECT 1 FROM updated)
    AND (e.old_is_in_scope, e.old_reason)
        IS DISTINCT FROM (e.desired_is_in_scope, e.desired_reason)
  RETURNING
    epp.period_id,
    epp.is_in_scope,
    epp.exclusion_reason
),
scope_logged AS (
  INSERT INTO performance_db.period_scope_events
    (period_id, user_id, event_type, reason, actor_id, note)
  SELECT
    sc.period_id,
    ${userId},
    CASE WHEN sc.is_in_scope THEN 'included' ELSE 'excluded' END,
    CASE WHEN sc.is_in_scope THEN NULL ELSE sc.exclusion_reason END,
    ${actorId},
    'Автоматический пересчёт после изменения даты приёма'
  FROM scope_changed sc
  RETURNING id
),
card_changes AS (
  SELECT
    (
      CASE WHEN t.full_name IS DISTINCT FROM u.full_name
        THEN jsonb_build_object('full_name', jsonb_build_object('old', t.full_name, 'new', u.full_name))
        ELSE '{}'::jsonb END
      || CASE WHEN t.email IS DISTINCT FROM u.email
        THEN jsonb_build_object('email', jsonb_build_object('old', t.email, 'new', u.email))
        ELSE '{}'::jsonb END
      || CASE WHEN t.role IS DISTINCT FROM u.role
        THEN jsonb_build_object('role', jsonb_build_object('old', t.role, 'new', u.role))
        ELSE '{}'::jsonb END
      || CASE WHEN t.job_title IS DISTINCT FROM u.job_title
        THEN jsonb_build_object('job_title', jsonb_build_object('old', t.job_title, 'new', u.job_title))
        ELSE '{}'::jsonb END
      || CASE WHEN t.work_category IS DISTINCT FROM u.work_category
        THEN jsonb_build_object('work_category', jsonb_build_object('old', t.work_category, 'new', u.work_category))
        ELSE '{}'::jsonb END
      || CASE WHEN t.department_id IS DISTINCT FROM u.department_id
        THEN jsonb_build_object('department_id', jsonb_build_object('old', t.department_id, 'new', u.department_id))
        ELSE '{}'::jsonb END
      || CASE WHEN t.grade_id IS DISTINCT FROM u.grade_id
        THEN jsonb_build_object('grade_id', jsonb_build_object('old', t.grade_id, 'new', u.grade_id))
        ELSE '{}'::jsonb END
      || CASE WHEN t.manager_id IS DISTINCT FROM u.manager_id
        THEN jsonb_build_object('manager_id', jsonb_build_object('old', t.manager_id, 'new', u.manager_id))
        ELSE '{}'::jsonb END
      || CASE WHEN t.join_date IS DISTINCT FROM u.join_date
        THEN jsonb_build_object('join_date', jsonb_build_object(
          'old', to_char(t.join_date, 'YYYY-MM-DD'),
          'new', to_char(u.join_date, 'YYYY-MM-DD')
        ))
        ELSE '{}'::jsonb END
    ) AS changes
  FROM target t
  JOIN updated u ON u.id = t.id
),
card_logged AS (
  INSERT INTO performance_db.employee_card_events
    (user_id, actor_id, event_type, changes)
  SELECT ${userId}, ${actorId}, 'updated', cc.changes
  FROM card_changes cc
  WHERE cc.changes <> '{}'::jsonb
  RETURNING id
),
outcomes AS (
  SELECT
    ps.period_id,
    ps.period_name,
    ps.period_status,
    ps.period_type,
    ps.old_is_in_scope,
    ps.old_reason,
    ps.desired_is_in_scope,
    ps.desired_reason,
    ps.evaluations_received,
    ps.self_reviews,
    ps.evaluations_given,
    ps.corrections_about,
    CASE
      WHEN ps.period_status = 'closed' THEN 'closed_untouched'
      WHEN NOT ps.row_exists THEN 'no_participant_row'
      WHEN ps.user_terminated OR ps.old_reason = 'terminated' THEN 'terminated_preserved'
      WHEN ps.scope_override IS NOT NULL OR ps.old_reason = 'excluded_by_admin' THEN 'manual_preserved'
      WHEN NOT ps.join_date_changed THEN 'not_recomputed'
      WHEN EXISTS (SELECT 1 FROM blocked_periods bp WHERE bp.period_id = ps.period_id)
        THEN 'refused_has_evaluations'
      WHEN EXISTS (SELECT 1 FROM scope_changed sc WHERE sc.period_id = ps.period_id)
        THEN CASE WHEN ps.desired_is_in_scope THEN 'included_by_date' ELSE 'excluded_by_date' END
      WHEN ps.desired_is_in_scope THEN 'unchanged_in_scope'
      ELSE 'unchanged_out_of_scope'
    END AS outcome
  FROM period_state ps
)
SELECT
  EXISTS (SELECT 1 FROM target) AS target_found,
  EXISTS (SELECT 1 FROM blocked_periods) AS blocked,
  (SELECT row_to_json(u) FROM updated u LIMIT 1) AS saved_user,
  COALESCE((SELECT json_agg(row_to_json(o) ORDER BY o.period_id) FROM outcomes o), '[]'::json)
    AS scope_results,
  (SELECT id FROM card_logged LIMIT 1) AS card_event_id,
  COALESCE((SELECT count(*) FROM scope_logged), 0)::integer AS scope_events_written
  `;
}

return { json: { ok: true, sql } };
""".strip()

SAVE_USER_FORMAT = """
const prev = $('Build User Upsert').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.target_found !== undefined);
if (!row) {
  return {
    json: { http_status: 500, body: { success: false, error: 'UPSERT_FAILED', message: 'Failed to save user' } },
  };
}
const found = row.target_found === true || row.target_found === 't';
if (!found) {
  return {
    json: { http_status: 404, body: { success: false, error: 'USER_NOT_FOUND', message: 'Сотрудник не найден' } },
  };
}
let scopeResults = row.scope_results;
if (typeof scopeResults === 'string') {
  try { scopeResults = JSON.parse(scopeResults); } catch { scopeResults = []; }
}
if (!Array.isArray(scopeResults)) scopeResults = [];
const blocked = row.blocked === true || row.blocked === 't';
if (blocked) {
  const blockedPeriods = scopeResults.filter((item) => item.outcome === 'refused_has_evaluations');
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'HIRE_DATE_SCOPE_HAS_EVALUATIONS',
        message: 'Карточка не сохранена целиком: изменение даты приёма исключило бы сотрудника из периода, где уже есть оценки. Все поля, включая остальные правки, остались прежними. Сохраните остальные поля отдельно, затем скорректируйте дату.',
        periods: blockedPeriods,
        scope_results: scopeResults,
      },
    },
  };
}
let savedUser = row.saved_user;
if (typeof savedUser === 'string') {
  try { savedUser = JSON.parse(savedUser); } catch { savedUser = null; }
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      user: savedUser,
      scope_results: scopeResults,
      card_event_id: row.card_event_id != null ? Number(row.card_event_id) : null,
      scope_events_written: Number(row.scope_events_written) || 0,
    },
  },
};
""".strip()


def build_save_user(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        node("saveuser-webhook", "Webhook", "n8n-nodes-base.webhook", [-900, 0],
             {"httpMethod": "POST", "path": "admin/save-user",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-admin-save-user"),
        node("saveuser-guard-input", "Prepare Guard Input", "n8n-nodes-base.code",
             [-680, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("saveuser-run-guard", "Run Auth Guard", [-450, 0], guard_workflow_id),
        node("saveuser-validate", "Validate User Data", "n8n-nodes-base.code",
             [-200, 0], {"jsCode": SAVE_USER_VALIDATE}),
        node("saveuser-build", "Build User Upsert", "n8n-nodes-base.code",
             [320, 0], {"jsCode": SAVE_USER_BUILD_UPSERT}),
        node("saveuser-execute", "Execute User Upsert", "n8n-nodes-base.postgres",
             [580, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("saveuser-format", "Format Response", "n8n-nodes-base.code",
             [840, 0], {"jsCode": SAVE_USER_FORMAT}),
        respond_node("saveuser-respond", "Respond", [1080, 0]),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Validate User Data"),
        "Validate User Data": connect("Build User Upsert"),
        "Build User Upsert": connect("Execute User Upsert"),
        "Execute User Upsert": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow("API: Admin Save User (GUI Mode)", nodes_list, connections)


# ── 17. Manage Periods — period CRUD, hierarchy, close-time persistence, roll-up
# GET api/periods: catalogue incl. child_count/has_evaluations/has_results and
#   evaluation_started_at/evaluation_started (the second gate, D-0822-1).
# POST api/periods/create: atomic CTE period+participants; always draft/inactive;
#   half_year or annual only; optional parent_period_id (container attach at birth).
# POST api/periods/activate: refuses containers (422, D-0821-1), annual periods
#   (422, D-0821-4 — a year is a reporting container whatever its children),
#   closed targets, and switching away from an active period with evaluations (409).
#   Activation does NOT start the evaluation — it opens the preparation window.
# POST api/periods/start-evaluation: the second gate (D-0822-1). Admin only,
#   leaf only, active only, never annual, never twice (a second call answers 200
#   already_started and changes nothing). Sets evaluation_started_at once; no
#   route ever clears it — recovery is SQL on the host, like activation rollback.
# POST api/periods/rename: any period; unique-name guarded. Nothing keys on name.
# POST api/periods/reparent: attach/detach a child; containers are reporting
#   constructs, so reparenting is always safe. A period with evaluations can
#   never become a parent; child dates must lie within the parent's and must not
#   overlap an existing sibling (the annual index is a SUM — overlap double-counts).
# POST api/periods/close: leaf-only, active-only, never annual; computes and stores
#   per-person results in one atomic statement (D-0821-2). Second close: zero rows.
# GET api/periods/annual-rollup: admin + c_level; persisted results only —
#   out-of-scope excluded from the mean, index is a sum (D-0821-3 / D-0819-1).

PERIODS_GET_BUILD = """
const guard = $('Run Auth Guard GET').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
return {
  json: {
    ok: true,
    sql: `
      SELECT id, name, start_date, end_date, is_active, status, period_type, parent_period_id,
        evaluation_started_at,
        evaluation_started_by,
        (evaluation_started_at IS NOT NULL) AS evaluation_started,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = evaluation_periods.id) AS participant_count,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = evaluation_periods.id AND epp.is_in_scope = true) AS in_scope_count,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods child
          WHERE child.parent_period_id = evaluation_periods.id) AS child_count,
        EXISTS(SELECT 1 FROM performance_db.evaluations e
          WHERE e.period_id = evaluation_periods.id) AS has_evaluations,
        EXISTS(SELECT 1 FROM performance_db.period_results pr
          WHERE pr.period_id = evaluation_periods.id) AS has_results
      FROM performance_db.evaluation_periods
      ORDER BY start_date DESC
    `,
  },
};
""".strip()

PERIODS_GET_FORMAT = """
const guard = $('Run Auth Guard GET').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const periods = $input.all().map(item => item.json).filter(item => item.id !== undefined);
return {
  json: {
    http_status: 200,
    body: { status: 'success', data: periods },
  },
};
""".strip()

PERIODS_CREATE_VALIDATE = """
const guard = $('Run Auth Guard CREATE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const name = String(body.name || '').trim();
const startDate = String(body.start_date || '').trim();
const endDate = String(body.end_date || '').trim();
// Limit to half_year and annual for H1/H2; ignore client status — always starts draft
const rawType = String(body.period_type || 'half_year').trim();
const VALID_TYPES = ['half_year', 'annual'];

if (!name || name.length > 100) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_NAME', message: 'Укажите название периода длиной не более 100 символов' } } };
}
if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(startDate)) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_DATE', message: 'Дата начала должна быть в формате ГГГГ-ММ-ДД' } } };
}
if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(endDate)) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_DATE', message: 'Дата окончания должна быть в формате ГГГГ-ММ-ДД' } } };
}
if (endDate <= startDate) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_DATE_RANGE', message: 'Дата окончания должна быть позже даты начала' } } };
}
if (!VALID_TYPES.includes(rawType)) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_TYPE', message: 'Тип периода должен быть half_year или annual' } } };
}

const rawParent = body.parent_period_id;
let parentId = null;
if (rawParent !== undefined && rawParent !== null && String(rawParent).trim() !== '') {
  parentId = parseInt(rawParent, 10);
  if (!Number.isFinite(parentId) || parentId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_PARENT', message: 'Идентификатор родительского периода должен быть положительным целым числом' } } };
  }
}

const safeName = name.replace(/'/g, "''");
// child_inside_parent is decided by Postgres, never in JS: the Postgres node
// hands date columns back as JS Date objects serialised in UTC, so a date read
// here is one calendar day early in Moscow time. Comparing a client
// YYYY-MM-DD string against that refused a child ending on the parent's own
// last day — i.e. the canonical H2 01.07-31.12 under an annual container.
// Always start as draft and inactive; ignore client-supplied status
return {
  json: {
    ok: true,
    name: safeName,
    start_date: startDate,
    end_date: endDate,
    period_type: rawType,
    parent_id: parentId,
    sql: `
SELECT
  EXISTS(SELECT 1 FROM performance_db.evaluation_periods x
         WHERE x.name = '${safeName}') AS name_taken,
  p.id AS parent_id,
  p.start_date AS parent_start,
  p.end_date AS parent_end,
  p.status AS parent_status,
  p.parent_period_id AS parent_parent_id,
  EXISTS(SELECT 1 FROM performance_db.evaluations e
         WHERE e.period_id = ${parentId === null ? -1 : parentId}) AS parent_has_evaluations,
  ('${startDate}'::date >= p.start_date AND '${endDate}'::date <= p.end_date) AS child_inside_parent,
  (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods sib
     WHERE sib.parent_period_id = ${parentId === null ? -1 : parentId}
       AND sib.start_date <= '${endDate}'::date
       AND sib.end_date >= '${startDate}'::date) AS sibling_overlap_count
FROM (SELECT 1) one
LEFT JOIN performance_db.evaluation_periods p
  ON p.id = ${parentId === null ? -1 : parentId}
    `,
  },
};
""".strip()

PERIODS_CREATE_BUILD = """
const prev = $('Validate Period Create').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.name_taken !== undefined);
if (!check) {
  return { json: { http_status: 500, body: { success: false, error: 'CHECK_FAILED', message: 'Не удалось проверить условия создания периода' } } };
}
if (check.name_taken) {
  return { json: { http_status: 409, body: { success: false, error: 'PERIOD_NAME_TAKEN', message: 'Период с таким названием уже существует' } } };
}
const parentId = prev.parent_id;
if (parentId !== null) {
  if (check.parent_id === null || check.parent_id === undefined) {
    return { json: { http_status: 404, body: { success: false, error: 'PARENT_NOT_FOUND', message: 'Родительский период не найден' } } };
  }
  if (check.parent_parent_id !== null && check.parent_parent_id !== undefined) {
    return { json: { http_status: 422, body: { success: false, error: 'PARENT_IS_CHILD', message: 'Контейнер не может быть вложен в другой контейнер' } } };
  }
  if (check.parent_status === 'active') {
    return { json: { http_status: 422, body: { success: false, error: 'PARENT_ACTIVE', message: 'Активный период не может быть контейнером' } } };
  }
  if (check.parent_has_evaluations) {
    return { json: { http_status: 422, body: { success: false, error: 'PARENT_HAS_EVALUATIONS', message: 'Период с оценками не может стать контейнером' } } };
  }
  // NULL (unknown) refuses too: only an explicit "inside" passes.
  const insideParent = check.child_inside_parent === true || check.child_inside_parent === 'true';
  if (!insideParent) {
    return { json: { http_status: 422, body: { success: false, error: 'CHILD_DATES_OUTSIDE_PARENT', message: 'Даты дочернего периода должны находиться внутри дат контейнера' } } };
  }
  // The annual index is a SUM over children: overlapping siblings double-count
  // the overlap, and the roll-up has no way to show that it happened.
  if (Number(check.sibling_overlap_count) > 0) {
    return { json: { http_status: 422, body: { success: false, error: 'SIBLING_DATES_OVERLAP', message: 'Даты пересекаются с другим дочерним периодом этого контейнера' } } };
  }
}
const safeName = prev.name;
const startDate = prev.start_date;
const endDate = prev.end_date;
const rawType = prev.period_type;
const parentLiteral = parentId === null ? 'NULL' : String(parentId);
// Re-assert every precondition inside the INSERT itself: zero rows on a race.
const insertGate = parentId === null
  ? `NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods x WHERE x.name = '${safeName}')`
  : `NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods x WHERE x.name = '${safeName}')
     AND EXISTS (
       SELECT 1 FROM performance_db.evaluation_periods p
       WHERE p.id = ${parentId}
         AND p.parent_period_id IS NULL
         AND p.status != 'active'
         AND p.start_date <= '${startDate}'::date
         AND p.end_date >= '${endDate}'::date
         AND NOT EXISTS (SELECT 1 FROM performance_db.evaluations e WHERE e.period_id = p.id)
     )
     AND NOT EXISTS (
       SELECT 1 FROM performance_db.evaluation_periods sib
       WHERE sib.parent_period_id = ${parentId}
         AND sib.start_date <= '${endDate}'::date
         AND sib.end_date >= '${startDate}'::date
     )`;
return {
  json: {
    ok: true,
    parent_id: parentId,
    sql: `
WITH new_period AS (
  INSERT INTO performance_db.evaluation_periods
    (name, start_date, end_date, is_active, period_type, status, parent_period_id)
  SELECT '${safeName}', '${startDate}'::date, '${endDate}'::date, false, '${rawType}', 'draft', ${parentLiteral}
  WHERE ${insertGate}
  RETURNING id, name, start_date, end_date, is_active, period_type, status, parent_period_id
),
participants AS (
  INSERT INTO performance_db.evaluation_period_participants
    (period_id, user_id, is_in_scope, exclusion_reason)
  SELECT
    np.id,
    u.id,
    -- D-0825-7: a terminated employee is out of scope for every period created
    -- after their termination, and the reason says so. Without this clause the
    -- CROSS JOIN would put them back in scope the moment H2 is created and
    -- silently return them to the bonus pool. Termination wins over the
    -- hire-date rule, so the reason names the state that actually excluded them.
    --
    -- D-0825-12: a person with NO hire date goes OUT of scope with a reason
    -- saying the date is missing and must be confirmed. Until 2026-08-25 the
    -- second branch read "join_date IS NOT NULL AND join_date > end_date", so a
    -- NULL fell through to ELSE true and joined the period silently, looking
    -- exactly like somebody with ten years' service (BUG-066). Somebody entered
    -- in advance of their start date must not dilute a running period's pool by
    -- accident. Reversible by hand: POST /api/admin/include-participant.
    -- This is forward-looking only — no existing row is rewritten, so Cem
    -- Durukan's H1 row stays in scope (D-0821-4 keeps the read-only trio in).
    CASE
      WHEN u.terminated_at IS NOT NULL THEN false
      WHEN u.join_date IS NULL THEN false
      -- D-0826-5: the final three calendar months are outside the minimum
      -- tenure. For H1 ending 2026-06-30 the boundary is 2026-03-31, so a hire
      -- on 31 March is in and a hire on 1 April is out.
      WHEN u.join_date >
           ((date_trunc('month', '${endDate}'::date)::date
             - interval '2 months' - interval '1 day')::date) THEN false
      ELSE true
    END,
    CASE
      WHEN u.terminated_at IS NOT NULL THEN 'terminated'
      WHEN u.join_date IS NULL THEN 'join_date_missing'
      WHEN u.join_date >
           ((date_trunc('month', '${endDate}'::date)::date
             - interval '2 months' - interval '1 day')::date)
        THEN 'insufficient_tenure'
      ELSE NULL
    END
  FROM new_period np
  CROSS JOIN performance_db.users u
  ON CONFLICT (period_id, user_id) DO UPDATE
    SET is_in_scope = EXCLUDED.is_in_scope,
        exclusion_reason = EXCLUDED.exclusion_reason,
        scope_override = NULL,
        updated_at = now()
  RETURNING user_id
)
SELECT np.id, np.name, np.start_date, np.end_date, np.is_active, np.period_type, np.status,
       np.parent_period_id,
       count(p.user_id)::integer AS participants_added
FROM new_period np
LEFT JOIN participants p ON true
GROUP BY np.id, np.name, np.start_date, np.end_date, np.is_active, np.period_type, np.status,
         np.parent_period_id
    `,
  },
};
""".strip()

PERIODS_CREATE_FORMAT = """
const prev = $('Build Create SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: { http_status: 409, body: { success: false, error: 'CREATE_CONFLICT', message: 'Условия создания периода изменились — обновите страницу и повторите' } },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      status: 'success',
      message: 'Period created',
      data: {
        id: row.id,
        name: row.name,
        start_date: row.start_date,
        end_date: row.end_date,
        is_active: row.is_active,
        period_type: row.period_type,
        status: row.status,
        parent_period_id: row.parent_period_id,
      },
      participants_added: row.participants_added,
    },
  },
};
""".strip()

PERIODS_ACTIVATE_VALIDATE = """
const guard = $('Run Auth Guard ACTIVATE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' },
    },
  };
}
// Check the target (containers are never activatable, D-0821-1) and any
// currently-active period that has evaluations (would block the switch).
return {
  json: {
    ok: true,
    target_period_id: periodId,
    sql: `
      SELECT
        t.id AS target_id,
        t.status AS target_status,
        t.period_type AS target_period_type,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods c
          WHERE c.parent_period_id = ${periodId}) AS target_child_count,
        cur.id AS current_active_id,
        cur.name AS current_active_name,
        cur.has_evaluations
      FROM (SELECT 1) one
      LEFT JOIN performance_db.evaluation_periods t ON t.id = ${periodId}
      LEFT JOIN (
        SELECT p.id, p.name,
          EXISTS(
            SELECT 1 FROM performance_db.evaluations WHERE period_id = p.id LIMIT 1
          ) AS has_evaluations
        FROM performance_db.evaluation_periods p
        WHERE (p.is_active = true OR p.status = 'active')
          AND p.id != ${periodId}
        LIMIT 1
      ) cur ON true
    `,
  },
};
""".strip()

PERIODS_ACTIVATE_EXECUTE = """
const prev = $('Validate Period Activate').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.target_child_count !== undefined);
if (!check) {
  return { json: { http_status: 500, body: { success: false, error: 'CHECK_FAILED', message: 'Не удалось проверить условия активации' } } };
}
if (check.target_id === null || check.target_id === undefined) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' },
    },
  };
}
// Containers are non-activatable reporting constructs (D-0821-1)
if (Number(check.target_child_count) > 0) {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'CONTAINER_NOT_ACTIVATABLE',
        message: 'Контейнерный период нельзя активировать: он объединяет дочерние периоды',
      },
    },
  };
}
if (check.target_status === 'closed') {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'PERIOD_CLOSED', message: 'Закрытый период нельзя активировать' },
    },
  };
}
// An annual period is a reporting container whatever its children happen to be:
// detaching the last child must not turn a whole year into a campaign period.
if (String(check.target_period_type) === 'annual') {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'ANNUAL_PERIOD_NOT_ACTIVATABLE',
        message: 'Годовой период — контейнер отчётности: активировать можно только полугодовой период',
      },
    },
  };
}
// Reject if switching away from an active period that already has evaluations
if (check.current_active_id !== null && check.current_active_id !== undefined && check.has_evaluations) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'ACTIVE_PERIOD_HAS_EVALUATIONS',
        message: `Нельзя деактивировать период «${check.current_active_name}»: в нём уже есть оценки`,
      },
    },
  };
}
const periodId = Number(prev.target_period_id);
return {
  json: {
    ok: true,
    sql: `
WITH activatable AS (
  SELECT id FROM performance_db.evaluation_periods
  WHERE id = ${periodId}
    AND status != 'closed'
    AND period_type != 'annual'
    AND NOT EXISTS (
      SELECT 1 FROM performance_db.evaluation_periods c
      WHERE c.parent_period_id = ${periodId}
    )
),
deactivated AS (
  UPDATE performance_db.evaluation_periods
  SET is_active = false, status = 'draft'
  WHERE (is_active = true OR status = 'active') AND id != ${periodId}
    AND EXISTS (SELECT 1 FROM activatable)
  RETURNING id
),
activated AS (
  UPDATE performance_db.evaluation_periods
  SET is_active = true, status = 'active'
  WHERE id IN (SELECT id FROM activatable)
    AND (SELECT count(*) FROM deactivated) >= 0
  RETURNING id, name, start_date, end_date, is_active, status, period_type
)
SELECT a.*, (SELECT count(*)::integer FROM deactivated) AS deactivated_count
FROM activated a
    `,
  },
};
""".strip()

PERIODS_ACTIVATE_FORMAT = """
const prev = $('Build Activation SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: {
      http_status: 404,
      body: { status: 'error', message: 'Период не найден или уже закрыт' },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      status: 'success',
      message: 'Period activated',
      data: {
        id: row.id,
        name: row.name,
        start_date: row.start_date,
        end_date: row.end_date,
        is_active: row.is_active,
        status: row.status,
        period_type: row.period_type,
      },
      deactivated_count: row.deactivated_count,
    },
  },
};
""".strip()


# POST api/periods/start-evaluation — the second gate (D-0822-1).
# Activation opens the preparation window; this opens the campaign itself.
# Admin only, leaf only, active only, never annual, never twice. Irreversible
# at product level: no route clears evaluation_started_at (recovery = SQL).

PERIODS_START_VALIDATE = """
const guard = $('Run Auth Guard START').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' },
    },
  };
}
return {
  json: {
    ok: true,
    target_period_id: periodId,
    actor_id: Number(guard.identity.id),
    sql: `
      SELECT
        t.id AS target_id,
        t.name AS target_name,
        t.status AS target_status,
        t.is_active AS target_is_active,
        t.period_type AS target_period_type,
        t.evaluation_started_at AS target_started_at,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods c
          WHERE c.parent_period_id = ${periodId}) AS target_child_count
      FROM (SELECT 1) one
      LEFT JOIN performance_db.evaluation_periods t ON t.id = ${periodId}
    `,
  },
};
""".strip()

PERIODS_START_EXECUTE = """
const prev = $('Validate Period Start').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.target_child_count !== undefined);
if (!check) {
  return { json: { http_status: 500, body: { success: false, error: 'CHECK_FAILED', message: 'Не удалось проверить условия старта оценки' } } };
}
if (check.target_id === null || check.target_id === undefined) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' },
    },
  };
}
// Containers aggregate children; the campaign runs in the leaf (D-0821-1).
if (Number(check.target_child_count) > 0) {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'CONTAINER_NOT_STARTABLE',
        message: 'Контейнерный период нельзя запустить: оценка идёт в дочернем периоде',
      },
    },
  };
}
// An annual period is a reporting container whatever its children happen to be.
if (String(check.target_period_type) === 'annual') {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'ANNUAL_PERIOD_NOT_STARTABLE',
        message: 'Годовой период — контейнер отчётности: запустить оценку можно только в полугодовом периоде',
      },
    },
  };
}
if (check.target_status === 'closed') {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'PERIOD_CLOSED', message: 'Закрытый период нельзя запустить' },
    },
  };
}
const isActive = check.target_is_active === true || check.target_is_active === 't';
if (String(check.target_status) !== 'active' || !isActive) {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'PERIOD_NOT_ACTIVE',
        message: 'Сначала активируйте период, затем запускайте оценку',
      },
    },
  };
}
// Already started: explicit, and zero state change. Mirrors the already-closed
// answer on close — a second click is not an error, it is a no-op.
if (check.target_started_at !== null && check.target_started_at !== undefined) {
  return {
    json: {
      http_status: 200,
      body: {
        status: 'success',
        already_started: true,
        message: 'Оценка в этом периоде уже запущена',
        data: {
          id: Number(check.target_id),
          name: check.target_name,
          status: check.target_status,
          is_active: isActive,
          period_type: check.target_period_type,
          evaluation_started_at: check.target_started_at,
        },
      },
    },
  };
}
const periodId = Number(prev.target_period_id);
const actorId = Number(prev.actor_id);
// Re-assert every precondition inside the UPDATE itself: a lost race changes
// zero rows and answers 409 rather than starting a period that no longer qualifies.
return {
  json: {
    ok: true,
    sql: `
WITH target AS (
  SELECT id FROM performance_db.evaluation_periods
  WHERE id = ${periodId}
    AND status = 'active'
    AND is_active = true
    AND period_type != 'annual'
    AND evaluation_started_at IS NULL
    AND NOT EXISTS (
      SELECT 1 FROM performance_db.evaluation_periods c
      WHERE c.parent_period_id = ${periodId}
    )
  FOR UPDATE
),
started AS (
  UPDATE performance_db.evaluation_periods p
  SET evaluation_started_at = now(),
      evaluation_started_by = ${actorId}
  FROM target t
  WHERE p.id = t.id
  RETURNING p.id, p.name, p.status, p.is_active, p.period_type,
            p.evaluation_started_at, p.evaluation_started_by
)
SELECT * FROM started
    `,
  },
};
""".strip()

PERIODS_START_FORMAT = """
const prev = $('Build Start SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'START_CONFLICT',
        message: 'Условия старта изменились — обновите страницу и повторите',
      },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      status: 'success',
      already_started: false,
      message: 'Evaluation started',
      data: {
        id: row.id,
        name: row.name,
        status: row.status,
        is_active: row.is_active,
        period_type: row.period_type,
        evaluation_started_at: row.evaluation_started_at,
        evaluation_started_by: row.evaluation_started_by,
      },
    },
  },
};
""".strip()


PERIODS_RENAME_VALIDATE = """
const guard = $('Run Auth Guard RENAME').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' } } };
}
const name = String(body.name || '').trim();
if (!name || name.length > 100) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_NAME', message: 'Укажите название периода длиной не более 100 символов' } } };
}
const safeName = name.replace(/'/g, "''");
return {
  json: {
    ok: true,
    period_id: periodId,
    name: safeName,
    sql: `
      SELECT t.id AS target_id,
        EXISTS(SELECT 1 FROM performance_db.evaluation_periods x
               WHERE x.name = '${safeName}' AND x.id != ${periodId}) AS name_taken
      FROM (SELECT 1) one
      LEFT JOIN performance_db.evaluation_periods t ON t.id = ${periodId}
    `,
  },
};
""".strip()

PERIODS_RENAME_BUILD = """
const prev = $('Validate Period Rename').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.name_taken !== undefined);
if (!check) {
  return { json: { http_status: 500, body: { success: false, error: 'CHECK_FAILED', message: 'Не удалось проверить условия переименования' } } };
}
if (check.target_id === null || check.target_id === undefined) {
  return { json: { http_status: 404, body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' } } };
}
if (check.name_taken) {
  return { json: { http_status: 409, body: { success: false, error: 'PERIOD_NAME_TAKEN', message: 'Период с таким названием уже существует' } } };
}
const periodId = Number(prev.period_id);
const safeName = prev.name;
return {
  json: {
    ok: true,
    sql: `
UPDATE performance_db.evaluation_periods
SET name = '${safeName}'
WHERE id = ${periodId}
  AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods x
                  WHERE x.name = '${safeName}' AND x.id != ${periodId})
RETURNING id, name, start_date, end_date, is_active, status, period_type, parent_period_id
    `,
  },
};
""".strip()

PERIODS_RENAME_FORMAT = """
const prev = $('Build Rename SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return { json: { http_status: 409, body: { success: false, error: 'RENAME_CONFLICT', message: 'Название уже занято — обновите страницу и повторите' } } };
}
return {
  json: {
    http_status: 200,
    body: { status: 'success', message: 'Period renamed', data: row },
  },
};
""".strip()

PERIODS_REPARENT_VALIDATE = """
const guard = $('Run Auth Guard REPARENT').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' } } };
}
const rawParent = body.parent_period_id;
let parentId = null;
if (rawParent !== undefined && rawParent !== null && String(rawParent).trim() !== '') {
  parentId = parseInt(rawParent, 10);
  if (!Number.isFinite(parentId) || parentId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_PARENT', message: 'Идентификатор родительского периода должен быть положительным целым числом' } } };
  }
}
if (parentId !== null && parentId === periodId) {
  return { json: { http_status: 422, body: { success: false, error: 'SELF_PARENT', message: 'Период нельзя вложить в самого себя' } } };
}
// child_inside_parent is decided by Postgres for the same reason as create:
// dates that cross the Postgres node arrive shifted by the timezone offset.
return {
  json: {
    ok: true,
    period_id: periodId,
    parent_id: parentId,
    sql: `
      SELECT
        t.id AS child_id,
        t.start_date AS child_start,
        t.end_date AS child_end,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods c
          WHERE c.parent_period_id = ${periodId}) AS child_child_count,
        p.id AS parent_id,
        p.start_date AS parent_start,
        p.end_date AS parent_end,
        p.status AS parent_status,
        p.parent_period_id AS parent_parent_id,
        EXISTS(SELECT 1 FROM performance_db.evaluations e
               WHERE e.period_id = ${parentId === null ? -1 : parentId}) AS parent_has_evaluations,
        (t.start_date >= p.start_date AND t.end_date <= p.end_date) AS child_inside_parent,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods sib
           WHERE sib.parent_period_id = ${parentId === null ? -1 : parentId}
             AND sib.id != ${periodId}
             AND sib.start_date <= t.end_date
             AND sib.end_date >= t.start_date) AS sibling_overlap_count
      FROM (SELECT 1) one
      LEFT JOIN performance_db.evaluation_periods t ON t.id = ${periodId}
      LEFT JOIN performance_db.evaluation_periods p ON p.id = ${parentId === null ? -1 : parentId}
    `,
  },
};
""".strip()

PERIODS_REPARENT_BUILD = """
const prev = $('Validate Period Reparent').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.child_child_count !== undefined);
if (!check) {
  return { json: { http_status: 500, body: { success: false, error: 'CHECK_FAILED', message: 'Не удалось проверить условия привязки' } } };
}
if (check.child_id === null || check.child_id === undefined) {
  return { json: { http_status: 404, body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' } } };
}
if (Number(check.child_child_count) > 0) {
  return { json: { http_status: 422, body: { success: false, error: 'CHILD_IS_CONTAINER', message: 'Контейнер нельзя вложить в другой период' } } };
}
const periodId = Number(prev.period_id);
const parentId = prev.parent_id;
if (parentId === null) {
  return {
    json: {
      ok: true,
      sql: `
UPDATE performance_db.evaluation_periods
SET parent_period_id = NULL
WHERE id = ${periodId}
RETURNING id, name, parent_period_id
      `,
    },
  };
}
if (check.parent_id === null || check.parent_id === undefined) {
  return { json: { http_status: 404, body: { success: false, error: 'PARENT_NOT_FOUND', message: 'Родительский период не найден' } } };
}
if (check.parent_parent_id !== null && check.parent_parent_id !== undefined) {
  return { json: { http_status: 422, body: { success: false, error: 'PARENT_IS_CHILD', message: 'Контейнер не может быть вложен в другой контейнер' } } };
}
if (check.parent_status === 'active') {
  return { json: { http_status: 422, body: { success: false, error: 'PARENT_ACTIVE', message: 'Активный период не может быть контейнером' } } };
}
// A period that has evaluations can never become a container
if (check.parent_has_evaluations) {
  return { json: { http_status: 422, body: { success: false, error: 'PARENT_HAS_EVALUATIONS', message: 'Период с оценками не может стать контейнером' } } };
}
// NULL (unknown) refuses too: only an explicit "inside" passes.
const insideParent = check.child_inside_parent === true || check.child_inside_parent === 'true';
if (!insideParent) {
  return { json: { http_status: 422, body: { success: false, error: 'CHILD_DATES_OUTSIDE_PARENT', message: 'Даты дочернего периода должны находиться внутри дат контейнера' } } };
}
// The annual index is a SUM over children: overlapping siblings double-count.
if (Number(check.sibling_overlap_count) > 0) {
  return { json: { http_status: 422, body: { success: false, error: 'SIBLING_DATES_OVERLAP', message: 'Даты пересекаются с другим дочерним периодом этого контейнера' } } };
}
return {
  json: {
    ok: true,
    sql: `
UPDATE performance_db.evaluation_periods
SET parent_period_id = ${parentId}
WHERE id = ${periodId}
  AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods c
                  WHERE c.parent_period_id = ${periodId})
  AND EXISTS (
    SELECT 1 FROM performance_db.evaluation_periods p
    WHERE p.id = ${parentId}
      AND p.parent_period_id IS NULL
      AND p.status != 'active'
      AND p.start_date <= (SELECT start_date FROM performance_db.evaluation_periods WHERE id = ${periodId})
      AND p.end_date >= (SELECT end_date FROM performance_db.evaluation_periods WHERE id = ${periodId})
      AND NOT EXISTS (SELECT 1 FROM performance_db.evaluations e WHERE e.period_id = p.id)
  )
  AND NOT EXISTS (
    SELECT 1 FROM performance_db.evaluation_periods sib
    WHERE sib.parent_period_id = ${parentId}
      AND sib.id != ${periodId}
      AND sib.start_date <= (SELECT end_date FROM performance_db.evaluation_periods WHERE id = ${periodId})
      AND sib.end_date >= (SELECT start_date FROM performance_db.evaluation_periods WHERE id = ${periodId})
  )
RETURNING id, name, parent_period_id
    `,
  },
};
""".strip()

PERIODS_REPARENT_FORMAT = """
const prev = $('Build Reparent SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return { json: { http_status: 409, body: { success: false, error: 'REPARENT_CONFLICT', message: 'Условия привязки изменились — обновите страницу и повторите' } } };
}
return {
  json: {
    http_status: 200,
    body: { status: 'success', message: 'Period reparented', data: row },
  },
};
""".strip()

PERIODS_CLOSE_VALIDATE = """
const guard = $('Run Auth Guard CLOSE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const body = guard.request.body || guard.request;
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' } } };
}
return {
  json: {
    ok: true,
    period_id: periodId,
    actor_id: Number(guard.identity.id),
    sql: `
      SELECT
        t.id AS target_id,
        t.name AS target_name,
        t.status AS target_status,
        t.is_active AS target_is_active,
        t.period_type AS target_period_type,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_periods c
          WHERE c.parent_period_id = ${periodId}) AS child_count,
        (SELECT COUNT(*)::integer FROM performance_db.evaluations e
          WHERE e.period_id = ${periodId}) AS evaluation_count,
        EXISTS(SELECT 1 FROM performance_db.period_results pr
          WHERE pr.period_id = ${periodId}) AS has_results,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId}) AS participant_count
      FROM (SELECT 1) one
      LEFT JOIN performance_db.evaluation_periods t ON t.id = ${periodId}
    `,
  },
};
""".strip()

# The dataset mirrors the evaluations-matrix per-criterion subqueries exactly:
# same predicates, same latest-by-updated_at rule for the manager channel, same
# c_level_direct_scores CTE, same correction lookups — so the persisted final
# cell is the matrix cell by construction (D-0820-12).
PERIODS_CLOSE_DATASET_SQL = """
WITH criteria_data AS (
  SELECT c.id, c.weight, c.c_level_only, c.target_audience,
    COALESCE(
      (SELECT json_object_agg(sc.score_level, sc.coefficient)
       FROM performance_db.score_coefficients sc WHERE sc.criteria_id = c.id),
      '{}'::json
    ) AS score_coefficients
  FROM performance_db.criteria c
  WHERE c.is_active = true
),
-- D-0826-1 (owner, 2026-08-26): the C-level direct channel is an AVERAGE
-- across evaluators carrying the number of evaluators, exactly the shape the
-- upward channel already has in the matrix.
--
-- Nothing was ever lost at write time: the unique index on evaluations is
-- (subject, evaluator, source, period), so a second C-level person gets their
-- own row and both rows persist. It was the READER that picked one — this
-- sub-select used to be ORDER BY e.updated_at DESC LIMIT 1 — so whoever
-- submitted last decided the person's share of the pool on criteria 1
-- (weight 5.00) and 10 (1.60), the heaviest pair in the catalogue, and three
-- people hold the right to file them.
--
-- AVG and COUNT come from ONE grouped scan: the mean and the count can never
-- end up describing different sets of rows. This CTE is character-for-character
-- the one in API: evaluations-matrix; if the two ever drift, the screen and
-- the frozen result stop agreeing about money.
c_level_direct_scores AS (
  SELECT
    e.subject_id,
    es.criteria_id,
    AVG(es.score_value) as avg_c_level_score,
    COUNT(*) as c_level_count
  FROM performance_db.evaluations e
  JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
  JOIN performance_db.criteria c ON es.criteria_id = c.id
  WHERE e.evaluation_source = 'c_level_direct'
    AND c.c_level_only = true
    AND c.is_active = true
    AND e.period_id = ${periodId}
  GROUP BY e.subject_id, es.criteria_id
)
SELECT
  epp.user_id,
  epp.is_in_scope,
  u.role,
  g.coefficient AS grade_coefficient,
  (SELECT ROUND(AVG(e.calculated_score)::numeric, 2)
     FROM performance_db.evaluations e
     WHERE e.subject_id = epp.user_id AND e.period_id = ${periodId}
       AND e.is_self_evaluation = false AND e.evaluation_source = 'manager') AS rating_manager,
  (SELECT ROUND(AVG(e.calculated_score)::numeric, 2)
     FROM performance_db.evaluations e
     WHERE e.subject_id = epp.user_id AND e.period_id = ${periodId}
       AND e.is_self_evaluation = false AND e.evaluation_source = 'subordinate') AS rating_upward,
  (SELECT ROUND(AVG(e.calculated_score)::numeric, 2)
     FROM performance_db.evaluations e
     WHERE e.subject_id = epp.user_id AND e.period_id = ${periodId}
       AND e.is_self_evaluation = false AND e.evaluation_source = 'c_level_direct') AS rating_c_level_direct,
  (SELECT e.calculated_score
     FROM performance_db.evaluations e
     WHERE e.subject_id = epp.user_id AND e.period_id = ${periodId}
       AND e.is_self_evaluation = true
     ORDER BY e.updated_at DESC LIMIT 1) AS rating_self,
  EXISTS(SELECT 1 FROM performance_db.evaluations e
     WHERE e.subject_id = epp.user_id AND e.period_id = ${periodId}) AS has_data,
  (SELECT json_agg(json_build_object(
      'criteria_id', cd.id,
      'c_level_only', cd.c_level_only,
      'weight', cd.weight,
      'score_coefficients', cd.score_coefficients,
      'manager_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = epp.user_id
          AND e.is_self_evaluation = false
          AND e.evaluation_source = 'manager'
          AND cd.c_level_only = false
          AND es.criteria_id = cd.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
      -- The mean across every C-level evaluator, and the count beside it
      -- (D-0826-1). Two decimals — the same scale rating_c_level_direct
      -- already uses. A single evaluator returns that evaluator's integer
      -- unchanged, so this is a no-op wherever only one person filed.
      -- The CTE already restricts itself to active c_level_only criteria,
      -- so no cell of any other criterion can match.
      'c_level_score', (
        SELECT ROUND(cds.avg_c_level_score::numeric, 2)
        FROM c_level_direct_scores cds
        WHERE cds.subject_id = epp.user_id
          AND cds.criteria_id = cd.id
      ),
      'c_level_count', (
        SELECT cds.c_level_count::integer
        FROM c_level_direct_scores cds
        WHERE cds.subject_id = epp.user_id
          AND cds.criteria_id = cd.id
      ),
      'mid_level_correction', (
        SELECT sc2.correction_score
        FROM performance_db.score_corrections sc2
        WHERE sc2.subject_id = epp.user_id
          AND sc2.criteria_id = cd.id
          AND sc2.correction_level = 'mid_level'
          AND sc2.period_id = ${periodId}
        LIMIT 1
      ),
      'c_level_correction', (
        SELECT sc2.correction_score
        FROM performance_db.score_corrections sc2
        WHERE sc2.subject_id = epp.user_id
          AND sc2.criteria_id = cd.id
          AND sc2.correction_level = 'c_level'
          AND sc2.period_id = ${periodId}
        LIMIT 1
      )
    ) ORDER BY cd.id)
   FROM criteria_data cd
   -- Applicability, classification dimension only (D-0822-3): a cell for a
   -- project_participants criterion exists only for a CURRENT project
   -- participant — the same predicate as Build Matrix Query, so the frozen
   -- period_results inherit exactly what the matrix shows. Excluded cells
   -- take their correction sub-selects with them.
   WHERE (cd.target_audience <> 'project_participants'
          OR u.is_project_participant = true)
     -- Second applicability dimension, added 2026-08-25, in lockstep with
     -- Build Matrix Query: managers_only applies only to somebody with
     -- direct reports, which is what the manager form has always enforced.
     -- If these two predicates ever drift, the screen and the frozen result
     -- stop agreeing about money.
     AND (cd.target_audience <> 'managers_only'
          OR u.has_subordinates = true)) AS criteria
FROM performance_db.evaluation_period_participants epp
JOIN performance_db.users u ON u.id = epp.user_id
LEFT JOIN performance_db.grades g ON u.grade_id = g.id
WHERE epp.period_id = ${periodId}
ORDER BY epp.user_id
""".strip()

PERIODS_CLOSE_DATASET_BUILD = """
const prev = $('Validate Period Close').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.child_count !== undefined);
if (!check) {
  return { json: { http_status: 500, body: { success: false, error: 'CHECK_FAILED', message: 'Не удалось проверить условия закрытия' } } };
}
if (check.target_id === null || check.target_id === undefined) {
  return { json: { http_status: 404, body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' } } };
}
if (Number(check.child_count) > 0) {
  return { json: { http_status: 422, body: { success: false, error: 'CONTAINER_NOT_CLOSABLE', message: 'Контейнер не закрывается: закрываются его дочерние периоды' } } };
}
if (check.target_status === 'closed') {
  if (check.has_results) {
    // Idempotent second close: zero rows changed, results untouched.
    return {
      json: {
        http_status: 200,
        body: {
          success: true,
          already_closed: true,
          results_stored: 0,
          message: `Период «${check.target_name}» уже закрыт; сохранённые результаты не изменены`,
        },
      },
    };
  }
  return { json: { http_status: 409, body: { success: false, error: 'PERIOD_ALREADY_CLOSED', message: 'Период уже закрыт (без сохранённых результатов)' } } };
}
// Annual periods never close, with or without children: closing a childless
// annual would freeze a full year of has_data=false rows forever.
if (String(check.target_period_type) === 'annual') {
  return { json: { http_status: 422, body: { success: false, error: 'ANNUAL_PERIOD_NOT_CLOSABLE', message: 'Годовой период — контейнер отчётности: закрываются его дочерние периоды' } } };
}
if (check.target_status !== 'active') {
  return { json: { http_status: 422, body: { success: false, error: 'PERIOD_NOT_ACTIVE', message: 'Закрыть можно только активный период' } } };
}
if (Number(check.participant_count) === 0) {
  return { json: { http_status: 422, body: { success: false, error: 'NO_PARTICIPANTS', message: 'У периода нет участников — закрывать нечего' } } };
}
const periodId = Number(prev.period_id);
return {
  json: {
    ok: true,
    period_id: periodId,
    actor_id: prev.actor_id,
    evaluation_count: Number(check.evaluation_count),
    sql: `
""" + PERIODS_CLOSE_DATASET_SQL + """
    `,
  },
};
""".strip()

# Final cell and bonus index replicate the client pipeline verbatim:
# matrixUtils.getCriterionFinalScore + useFinalScoresMatrix.calculateCriterionScore
# (formula #3 — weighted sum WITHOUT dividing by sum of weights, × grade coef).
PERIODS_CLOSE_COMPUTE = """
const prev = $('Build Close Dataset Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const rows = $input.all().map(item => item.json).filter(item => item.user_id !== undefined);
if (rows.length === 0) {
  return { json: { http_status: 422, body: { success: false, error: 'NO_PARTICIPANTS', message: 'У периода нет участников — закрывать нечего' } } };
}
const periodId = Number(prev.period_id);
const actorId = Number(prev.actor_id);

// matrixUtils.getCriterionFinalScore — the matrix final cell (D-0820-12).
// `c_level_score` is now the MEAN across every C-level evaluator of that cell
// (D-0826-1); the count travels beside it as `c_level_count` and is carried to
// the screens, not into period_results — a count is a property of one cell and
// period_results stores one row per person, so a person-level column would
// misdescribe it. A c_level score CORRECTION still does not enter this branch
// at all: see D-0826-1's «surfaced, not resolved» — that is the owner's call.
const finalOf = (crit) => {
  if (crit.c_level_only) {
    return crit.c_level_score != null ? Number(crit.c_level_score) : null;
  }
  if (crit.manager_score == null) return null;
  const scores = [Number(crit.manager_score)];
  if (crit.mid_level_correction != null) scores.push(Number(crit.mid_level_correction));
  if (crit.c_level_correction != null) scores.push(Number(crit.c_level_correction));
  return scores.reduce((acc, s) => acc + s, 0) / scores.length;
};

// useFinalScoresMatrix.calculateCriterionScore — score × coef(round(clamp)) × weight.
// `|| 1.0` mirrors the client exactly (parseFloat(weight) || 1.0 in the
// score-coefficients API): a zero/absent weight or grade behaves as 1.0.
const weightedOf = (raw, crit) => {
  const weight = Number(crit.weight) || 1.0;
  const coefficients = crit.score_coefficients || {};
  const level = Math.max(0, Math.min(10, Math.round(raw)));
  const coefficient = coefficients[level] != null ? Number(coefficients[level]) : 1.0;
  return raw * coefficient * weight;
};

const numLit = (value, digits) => (value == null ? 'NULL' : Number(value).toFixed(digits));
const values = [];
let inScopeCount = 0;
let noDataCount = 0;
for (const row of rows) {
  const inScope = row.is_in_scope === true || row.is_in_scope === 'true';
  let hasData = inScope && (row.has_data === true || row.has_data === 'true');
  let finalRating = null;
  let bonusIndex = null;
  let ratingManager = null;
  let ratingUpward = null;
  let ratingCLevel = null;
  let ratingSelf = null;
  if (hasData) {
    ratingManager = row.rating_manager;
    ratingUpward = row.rating_upward;
    ratingCLevel = row.rating_c_level_direct;
    ratingSelf = row.rating_self;
    const finals = [];
    let weightedSum = 0;
    for (const crit of (row.criteria || [])) {
      const raw = finalOf(crit);
      if (raw !== null) {
        finals.push(raw);
        weightedSum += weightedOf(raw, crit);
      }
    }
    if (finals.length > 0) {
      finalRating = finals.reduce((acc, s) => acc + s, 0) / finals.length;
      const gradeCoefficient = Number(row.grade_coefficient) || 1.0;
      bonusIndex = weightedSum * gradeCoefficient;
    }
  }
  if (inScope) inScopeCount += 1;
  if (inScope && !hasData) noDataCount += 1;
  values.push(`(${Number(row.user_id)}, ${inScope}, ${hasData}, ` +
    `${numLit(ratingManager, 2)}, ${numLit(ratingUpward, 2)}, ${numLit(ratingCLevel, 2)}, ${numLit(ratingSelf, 2)}, ` +
    `${numLit(finalRating, 4)}, ${numLit(bonusIndex, 4)})`);
}

// One atomic statement: preconditions re-asserted in `target`; a second close
// (or any race) selects zero target rows and therefore changes zero rows.
return {
  json: {
    ok: true,
    period_id: periodId,
    in_scope_count: inScopeCount,
    no_data_count: noDataCount,
    sql: `
WITH target AS (
  SELECT id FROM performance_db.evaluation_periods
  WHERE id = ${periodId}
    AND status = 'active' AND is_active = true
    AND period_type != 'annual'
    AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods c
                    WHERE c.parent_period_id = ${periodId})
    AND NOT EXISTS (SELECT 1 FROM performance_db.period_results pr
                    WHERE pr.period_id = ${periodId})
    AND (SELECT COUNT(*) FROM performance_db.evaluations e
         WHERE e.period_id = ${periodId}) = ${prev.evaluation_count}
  FOR UPDATE
),
ins AS (
  INSERT INTO performance_db.period_results
    (period_id, user_id, is_in_scope, has_data, rating_manager, rating_upward,
     rating_c_level_direct, rating_self, final_rating, bonus_index, closed_by)
  SELECT ${periodId}, v.user_id::integer, v.is_in_scope, v.has_data,
         v.rating_manager::numeric(10,2), v.rating_upward::numeric(10,2),
         v.rating_c_level_direct::numeric(10,2), v.rating_self::numeric(10,2),
         v.final_rating::numeric(10,4), v.bonus_index::numeric(14,4), ${actorId}
  FROM (VALUES
${values.join(',\\n')}
  ) AS v(user_id, is_in_scope, has_data, rating_manager, rating_upward,
         rating_c_level_direct, rating_self, final_rating, bonus_index)
  WHERE EXISTS (SELECT 1 FROM target)
  RETURNING user_id
),
closed AS (
  UPDATE performance_db.evaluation_periods
  SET status = 'closed', is_active = false
  WHERE id = ${periodId}
    AND EXISTS (SELECT 1 FROM target)
    AND (SELECT count(*) FROM ins) >= 0
  RETURNING id
)
SELECT
  (SELECT COUNT(*)::integer FROM ins) AS results_stored,
  (SELECT COUNT(*)::integer FROM closed) AS period_closed
    `,
  },
};
""".strip()

PERIODS_CLOSE_FORMAT = """
const prev = $('Compute Close Results').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.period_closed !== undefined);
if (!row || Number(row.period_closed) !== 1) {
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'CLOSE_CONFLICT', message: 'Состояние периода изменилось во время закрытия — обновите страницу и повторите' },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      closed: true,
      period_id: prev.period_id,
      results_stored: Number(row.results_stored),
      in_scope: prev.in_scope_count,
      no_data: prev.no_data_count,
      message: 'Период закрыт; результаты сохранены',
    },
  },
};
""".strip()

# Annual roll-up reads period_results ONLY — no live join against editable
# inputs. Mean over in-scope periods with data; index is a plain sum (D-0819-1,
# D-0821-3): out-of-scope periods are excluded, never zero-filled.
PERIODS_ROLLUP_BUILD = """
const guard = $('Run Auth Guard ROLLUP').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const request = guard.request || {};
const query = request.query || {};
const containerId = parseInt(query.container_id ?? query.containerId, 10);
if (!Number.isFinite(containerId) || containerId < 1) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_CONTAINER_ID', message: 'Идентификатор контейнера должен быть положительным целым числом' } } };
}
return {
  json: {
    ok: true,
    container_id: containerId,
    sql: `
SELECT json_build_object(
  'container', (
    SELECT json_build_object(
      'id', p.id, 'name', p.name, 'start_date', p.start_date, 'end_date', p.end_date,
      'status', p.status, 'period_type', p.period_type
    )
    FROM performance_db.evaluation_periods p WHERE p.id = ${containerId}
  ),
  'children', COALESCE((
    SELECT json_agg(json_build_object(
      'id', c.id, 'name', c.name, 'start_date', c.start_date, 'end_date', c.end_date,
      'status', c.status, 'is_active', c.is_active,
      'has_results', EXISTS(SELECT 1 FROM performance_db.period_results pr
                            WHERE pr.period_id = c.id)
    ) ORDER BY c.start_date, c.id)
    FROM performance_db.evaluation_periods c WHERE c.parent_period_id = ${containerId}
  ), '[]'::json),
  'rows', COALESCE((
    SELECT json_agg(person_row ORDER BY sort_name)
    FROM (
      SELECT u.full_name AS sort_name, json_build_object(
        'user_id', u.id,
        'full_name', u.full_name,
        'job_title', u.job_title,
        'department_name', d.name,
        'grade_code', g.code,
        'results', (
          SELECT COALESCE(json_object_agg(pr.period_id, json_build_object(
            'in_scope', pr.is_in_scope,
            'has_data', pr.has_data,
            'final_rating', pr.final_rating,
            'bonus_index', pr.bonus_index
          )), '{}'::json)
          FROM performance_db.period_results pr
          WHERE pr.user_id = u.id
            AND pr.period_id IN (SELECT id FROM performance_db.evaluation_periods
                                 WHERE parent_period_id = ${containerId})
        ),
        'annual_rating', (
          SELECT ROUND(AVG(pr.final_rating)::numeric, 4)
          FROM performance_db.period_results pr
          WHERE pr.user_id = u.id
            AND pr.period_id IN (SELECT id FROM performance_db.evaluation_periods
                                 WHERE parent_period_id = ${containerId})
            AND pr.is_in_scope = true
            AND pr.final_rating IS NOT NULL
        ),
        'annual_index', (
          SELECT ROUND(SUM(pr.bonus_index)::numeric, 4)
          FROM performance_db.period_results pr
          WHERE pr.user_id = u.id
            AND pr.period_id IN (SELECT id FROM performance_db.evaluation_periods
                                 WHERE parent_period_id = ${containerId})
            AND pr.is_in_scope = true
            AND pr.bonus_index IS NOT NULL
        )
      ) AS person_row
      FROM performance_db.users u
      LEFT JOIN performance_db.departments d ON u.department_id = d.id
      LEFT JOIN performance_db.grades g ON u.grade_id = g.id
      WHERE u.role != 'admin'
        AND EXISTS (
          SELECT 1 FROM performance_db.period_results pr
          WHERE pr.user_id = u.id
            AND pr.is_in_scope = true
            AND pr.period_id IN (SELECT id FROM performance_db.evaluation_periods
                                 WHERE parent_period_id = ${containerId})
        )
    ) t
  ), '[]'::json)
) AS payload
    `,
  },
};
""".strip()

PERIODS_ROLLUP_FORMAT = """
const prev = $('Build Rollup Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.payload !== undefined);
const payload = row ? row.payload : null;
if (!payload || !payload.container) {
  return { json: { http_status: 404, body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' } } };
}
const children = payload.children || [];
if (children.length === 0) {
  return { json: { http_status: 422, body: { success: false, error: 'NOT_A_CONTAINER', message: 'Период не является контейнером: у него нет дочерних периодов' } } };
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      container: payload.container,
      children,
      rows: payload.rows || [],
    },
  },
};
""".strip()


def build_manage_periods(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    nodes_list = [
        # GET trigger
        node("periods-webhook-get", "Webhook GET", "n8n-nodes-base.webhook", [-700, -200],
             {"httpMethod": "GET", "path": "api/periods",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-get"),
        node("periods-guard-input-get", "Prepare Guard Input GET", "n8n-nodes-base.code",
             [-480, -200], {"jsCode": guard_input_js(["admin", "hr", "c_level"])}),
        run_guard_node("periods-run-guard-get", "Run Auth Guard GET", [-250, -200], guard_workflow_id),
        node("periods-get-build", "Build Periods Query", "n8n-nodes-base.code",
             [0, -200], {"jsCode": PERIODS_GET_BUILD}),
        node("periods-get-query", "Load Periods", "n8n-nodes-base.postgres",
             [250, -200],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-get-format", "Format Periods Response", "n8n-nodes-base.code",
             [500, -200], {"jsCode": PERIODS_GET_FORMAT}),
        respond_node("periods-respond-get", "Respond GET", [740, -200]),
        # CREATE trigger
        node("periods-webhook-create", "Webhook CREATE", "n8n-nodes-base.webhook", [-700, 0],
             {"httpMethod": "POST", "path": "api/periods/create",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-create"),
        node("periods-guard-input-create", "Prepare Guard Input CREATE", "n8n-nodes-base.code",
             [-480, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("periods-run-guard-create", "Run Auth Guard CREATE", [-250, 0], guard_workflow_id),
        node("periods-create-validate", "Validate Period Create", "n8n-nodes-base.code",
             [0, 0], {"jsCode": PERIODS_CREATE_VALIDATE}),
        node("periods-create-check", "Check Create Preconditions", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-create-build", "Build Create SQL", "n8n-nodes-base.code",
             [500, 0], {"jsCode": PERIODS_CREATE_BUILD}),
        node("periods-create-execute", "Execute Period Create", "n8n-nodes-base.postgres",
             [750, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-create-format", "Format Create Response", "n8n-nodes-base.code",
             [1000, 0], {"jsCode": PERIODS_CREATE_FORMAT}),
        respond_node("periods-respond-create", "Respond CREATE", [1240, 0]),
        # ACTIVATE trigger
        node("periods-webhook-activate", "Webhook ACTIVATE", "n8n-nodes-base.webhook", [-700, 200],
             {"httpMethod": "POST", "path": "api/periods/activate",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-activate"),
        node("periods-guard-input-activate", "Prepare Guard Input ACTIVATE", "n8n-nodes-base.code",
             [-480, 200], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("periods-run-guard-activate", "Run Auth Guard ACTIVATE", [-250, 200], guard_workflow_id),
        node("periods-activate-validate", "Validate Period Activate", "n8n-nodes-base.code",
             [0, 200], {"jsCode": PERIODS_ACTIVATE_VALIDATE}),
        node("periods-activate-check", "Check Existing Active", "n8n-nodes-base.postgres",
             [250, 200],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS current_active_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-activate-build", "Build Activation SQL", "n8n-nodes-base.code",
             [500, 200], {"jsCode": PERIODS_ACTIVATE_EXECUTE}),
        node("periods-activate-execute", "Execute Activation", "n8n-nodes-base.postgres",
             [750, 200],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-activate-format", "Format Activate Response", "n8n-nodes-base.code",
             [1000, 200], {"jsCode": PERIODS_ACTIVATE_FORMAT}),
        respond_node("periods-respond-activate", "Respond ACTIVATE", [1240, 200]),
        # START trigger — the second gate (D-0822-1), admin only
        node("periods-webhook-start", "Webhook START", "n8n-nodes-base.webhook", [-700, 1200],
             {"httpMethod": "POST", "path": "api/periods/start-evaluation",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-start-evaluation"),
        node("periods-guard-input-start", "Prepare Guard Input START", "n8n-nodes-base.code",
             [-480, 1200], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("periods-run-guard-start", "Run Auth Guard START", [-250, 1200], guard_workflow_id),
        node("periods-start-validate", "Validate Period Start", "n8n-nodes-base.code",
             [0, 1200], {"jsCode": PERIODS_START_VALIDATE}),
        node("periods-start-check", "Load Start Target", "n8n-nodes-base.postgres",
             [250, 1200],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS target_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-start-build", "Build Start SQL", "n8n-nodes-base.code",
             [500, 1200], {"jsCode": PERIODS_START_EXECUTE}),
        node("periods-start-execute", "Execute Start", "n8n-nodes-base.postgres",
             [750, 1200],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-start-format", "Format Start Response", "n8n-nodes-base.code",
             [1000, 1200], {"jsCode": PERIODS_START_FORMAT}),
        respond_node("periods-respond-start", "Respond START", [1240, 1200]),
        # RENAME trigger
        node("periods-webhook-rename", "Webhook RENAME", "n8n-nodes-base.webhook", [-700, 400],
             {"httpMethod": "POST", "path": "api/periods/rename",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-rename"),
        node("periods-guard-input-rename", "Prepare Guard Input RENAME", "n8n-nodes-base.code",
             [-480, 400], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("periods-run-guard-rename", "Run Auth Guard RENAME", [-250, 400], guard_workflow_id),
        node("periods-rename-validate", "Validate Period Rename", "n8n-nodes-base.code",
             [0, 400], {"jsCode": PERIODS_RENAME_VALIDATE}),
        node("periods-rename-check", "Check Rename Preconditions", "n8n-nodes-base.postgres",
             [250, 400],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-rename-build", "Build Rename SQL", "n8n-nodes-base.code",
             [500, 400], {"jsCode": PERIODS_RENAME_BUILD}),
        node("periods-rename-execute", "Execute Rename", "n8n-nodes-base.postgres",
             [750, 400],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-rename-format", "Format Rename Response", "n8n-nodes-base.code",
             [1000, 400], {"jsCode": PERIODS_RENAME_FORMAT}),
        respond_node("periods-respond-rename", "Respond RENAME", [1240, 400]),
        # REPARENT trigger
        node("periods-webhook-reparent", "Webhook REPARENT", "n8n-nodes-base.webhook", [-700, 600],
             {"httpMethod": "POST", "path": "api/periods/reparent",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-reparent"),
        node("periods-guard-input-reparent", "Prepare Guard Input REPARENT", "n8n-nodes-base.code",
             [-480, 600], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("periods-run-guard-reparent", "Run Auth Guard REPARENT", [-250, 600], guard_workflow_id),
        node("periods-reparent-validate", "Validate Period Reparent", "n8n-nodes-base.code",
             [0, 600], {"jsCode": PERIODS_REPARENT_VALIDATE}),
        node("periods-reparent-check", "Check Reparent Preconditions", "n8n-nodes-base.postgres",
             [250, 600],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-reparent-build", "Build Reparent SQL", "n8n-nodes-base.code",
             [500, 600], {"jsCode": PERIODS_REPARENT_BUILD}),
        node("periods-reparent-execute", "Execute Reparent", "n8n-nodes-base.postgres",
             [750, 600],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-reparent-format", "Format Reparent Response", "n8n-nodes-base.code",
             [1000, 600], {"jsCode": PERIODS_REPARENT_FORMAT}),
        respond_node("periods-respond-reparent", "Respond REPARENT", [1240, 600]),
        # CLOSE trigger
        node("periods-webhook-close", "Webhook CLOSE", "n8n-nodes-base.webhook", [-700, 800],
             {"httpMethod": "POST", "path": "api/periods/close",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-close"),
        node("periods-guard-input-close", "Prepare Guard Input CLOSE", "n8n-nodes-base.code",
             [-480, 800], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("periods-run-guard-close", "Run Auth Guard CLOSE", [-250, 800], guard_workflow_id),
        node("periods-close-validate", "Validate Period Close", "n8n-nodes-base.code",
             [0, 800], {"jsCode": PERIODS_CLOSE_VALIDATE}),
        node("periods-close-check", "Load Close Target", "n8n-nodes-base.postgres",
             [250, 800],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-close-dataset-build", "Build Close Dataset Query", "n8n-nodes-base.code",
             [500, 800], {"jsCode": PERIODS_CLOSE_DATASET_BUILD}),
        node("periods-close-dataset", "Load Close Dataset", "n8n-nodes-base.postgres",
             [750, 800],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS user_id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-close-compute", "Compute Close Results", "n8n-nodes-base.code",
             [1000, 800], {"jsCode": PERIODS_CLOSE_COMPUTE}),
        node("periods-close-execute", "Execute Close", "n8n-nodes-base.postgres",
             [1250, 800],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS period_closed WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-close-format", "Format Close Response", "n8n-nodes-base.code",
             [1500, 800], {"jsCode": PERIODS_CLOSE_FORMAT}),
        respond_node("periods-respond-close", "Respond CLOSE", [1740, 800]),
        # ROLLUP trigger (admin + c_level; D-0820-11 audience)
        node("periods-webhook-rollup", "Webhook ROLLUP", "n8n-nodes-base.webhook", [-700, 1000],
             {"httpMethod": "GET", "path": "api/periods/annual-rollup",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-periods-annual-rollup"),
        node("periods-guard-input-rollup", "Prepare Guard Input ROLLUP", "n8n-nodes-base.code",
             [-480, 1000], {"jsCode": guard_input_js(["admin", "c_level"])}),
        run_guard_node("periods-run-guard-rollup", "Run Auth Guard ROLLUP", [-250, 1000], guard_workflow_id),
        node("periods-rollup-build", "Build Rollup Query", "n8n-nodes-base.code",
             [0, 1000], {"jsCode": PERIODS_ROLLUP_BUILD}),
        node("periods-rollup-load", "Load Rollup", "n8n-nodes-base.postgres",
             [250, 1000],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::json AS payload WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-rollup-format", "Format Rollup Response", "n8n-nodes-base.code",
             [500, 1000], {"jsCode": PERIODS_ROLLUP_FORMAT}),
        respond_node("periods-respond-rollup", "Respond ROLLUP", [740, 1000]),
    ]
    connections = {
        # GET path
        "Webhook GET": connect("Prepare Guard Input GET"),
        "Prepare Guard Input GET": connect("Run Auth Guard GET"),
        "Run Auth Guard GET": connect("Build Periods Query"),
        "Build Periods Query": connect("Load Periods"),
        "Load Periods": connect("Format Periods Response"),
        "Format Periods Response": connect("Respond GET"),
        # CREATE path
        "Webhook CREATE": connect("Prepare Guard Input CREATE"),
        "Prepare Guard Input CREATE": connect("Run Auth Guard CREATE"),
        "Run Auth Guard CREATE": connect("Validate Period Create"),
        "Validate Period Create": connect("Check Create Preconditions"),
        "Check Create Preconditions": connect("Build Create SQL"),
        "Build Create SQL": connect("Execute Period Create"),
        "Execute Period Create": connect("Format Create Response"),
        "Format Create Response": connect("Respond CREATE"),
        # ACTIVATE path
        "Webhook ACTIVATE": connect("Prepare Guard Input ACTIVATE"),
        "Prepare Guard Input ACTIVATE": connect("Run Auth Guard ACTIVATE"),
        "Run Auth Guard ACTIVATE": connect("Validate Period Activate"),
        "Validate Period Activate": connect("Check Existing Active"),
        "Check Existing Active": connect("Build Activation SQL"),
        "Build Activation SQL": connect("Execute Activation"),
        "Execute Activation": connect("Format Activate Response"),
        "Format Activate Response": connect("Respond ACTIVATE"),
        # START path
        "Webhook START": connect("Prepare Guard Input START"),
        "Prepare Guard Input START": connect("Run Auth Guard START"),
        "Run Auth Guard START": connect("Validate Period Start"),
        "Validate Period Start": connect("Load Start Target"),
        "Load Start Target": connect("Build Start SQL"),
        "Build Start SQL": connect("Execute Start"),
        "Execute Start": connect("Format Start Response"),
        "Format Start Response": connect("Respond START"),
        # RENAME path
        "Webhook RENAME": connect("Prepare Guard Input RENAME"),
        "Prepare Guard Input RENAME": connect("Run Auth Guard RENAME"),
        "Run Auth Guard RENAME": connect("Validate Period Rename"),
        "Validate Period Rename": connect("Check Rename Preconditions"),
        "Check Rename Preconditions": connect("Build Rename SQL"),
        "Build Rename SQL": connect("Execute Rename"),
        "Execute Rename": connect("Format Rename Response"),
        "Format Rename Response": connect("Respond RENAME"),
        # REPARENT path
        "Webhook REPARENT": connect("Prepare Guard Input REPARENT"),
        "Prepare Guard Input REPARENT": connect("Run Auth Guard REPARENT"),
        "Run Auth Guard REPARENT": connect("Validate Period Reparent"),
        "Validate Period Reparent": connect("Check Reparent Preconditions"),
        "Check Reparent Preconditions": connect("Build Reparent SQL"),
        "Build Reparent SQL": connect("Execute Reparent"),
        "Execute Reparent": connect("Format Reparent Response"),
        "Format Reparent Response": connect("Respond REPARENT"),
        # CLOSE path
        "Webhook CLOSE": connect("Prepare Guard Input CLOSE"),
        "Prepare Guard Input CLOSE": connect("Run Auth Guard CLOSE"),
        "Run Auth Guard CLOSE": connect("Validate Period Close"),
        "Validate Period Close": connect("Load Close Target"),
        "Load Close Target": connect("Build Close Dataset Query"),
        "Build Close Dataset Query": connect("Load Close Dataset"),
        "Load Close Dataset": connect("Compute Close Results"),
        "Compute Close Results": connect("Execute Close"),
        "Execute Close": connect("Format Close Response"),
        "Format Close Response": connect("Respond CLOSE"),
        # ROLLUP path
        "Webhook ROLLUP": connect("Prepare Guard Input ROLLUP"),
        "Prepare Guard Input ROLLUP": connect("Run Auth Guard ROLLUP"),
        "Run Auth Guard ROLLUP": connect("Build Rollup Query"),
        "Build Rollup Query": connect("Load Rollup"),
        "Load Rollup": connect("Format Rollup Response"),
        "Format Rollup Response": connect("Respond ROLLUP"),
    }
    return workflow("API: Manage Periods", nodes_list, connections)


# ── 18. Employment status — terminate / reinstate an employee (D-0825-7) ──────
#
# The owner's decision: a terminated employee disappears from every list, task
# and calculation; they are not evaluated, they do not evaluate, and they take
# no share of the bonus pool for the period. The state is reversible and is
# refused while the person still has direct reports. Evaluations they GAVE stay
# in force — deleting them would silently change the results of people who are
# still employed.
#
# Nothing here deletes anything. Exclusion is achieved by two existing
# mechanisms plus one new state:
#   * users.terminated_at / termination_date (migration 015) — the person-level
#     state. Read by the admin list, by login, by registration and by the
#     password-reset request.
#   * evaluation_period_participants.is_in_scope = false with
#     exclusion_reason = 'terminated' — the per-period money record. This is the
#     SAME machinery that already takes Esenova and Balova out of H1, and it is
#     what every task, submit, completion counter and close-time computation
#     already reads. Nothing new had to be taught to those paths.
#   * token_version + 1 and auth_sessions.revoked_at — the session kill. The
#     guard joins auth_sessions on token_version = users.token_version, so the
#     bump alone invalidates every live JWT; revoked_at is the second lock.
#
# Deliberately NOT touched: can_evaluate / can_be_evaluated. Those are the
# owner's standing policy flags for the read-only C-level trio (D-0821-4).
# Overwriting them here would make reinstatement lossy — after a round trip you
# could no longer tell a read-only C-level from a former employee.

EMPLOYMENT_TERMINATE_VALIDATE = """
const guard = $('Run Auth Guard TERMINATE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request;

const userId = parseInt(body.user_id, 10);
if (!Number.isFinite(userId) || userId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_USER_ID', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
    },
  };
}
// The owner supplies the last working day. It is a separate fact from "when
// somebody clicked": the date decides which period the person dropped out of,
// and the click time is only the audit stamp.
const rawDate = String(body.termination_date || '').trim();
if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(rawDate)) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_TERMINATION_DATE', message: 'Укажите дату увольнения в формате ГГГГ-ММ-ДД' },
    },
  };
}
const parsed = new Date(`${rawDate}T00:00:00Z`);
if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== rawDate) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_TERMINATION_DATE', message: 'Такой даты не существует' },
    },
  };
}
// Terminating yourself locks the only admin out of the product with no route
// back in — reinstatement is admin-only. Refused by name rather than left to
// the owner to discover.
if (userId === actorId) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'CANNOT_TERMINATE_SELF', message: 'Нельзя уволить самого себя' },
    },
  };
}
const note = String(body.note || '').trim().slice(0, 500);

return {
  json: {
    ok: true,
    actor_id: actorId,
    user_id: userId,
    termination_date: rawDate,
    note,
    sql: `
      SELECT
        t.id AS target_id,
        t.full_name AS target_name,
        -- Reported for the response and for the operator's log. There is no
        -- LAST_ADMIN branch: the route is admin-only, so the only way to reach
        -- zero live admins is an admin terminating themselves, which
        -- CANNOT_TERMINATE_SELF already refuses. A second guard here would be
        -- unreachable code that reads as a guarantee.
        t.role::text AS target_role,
        (t.terminated_at IS NOT NULL) AS already_terminated,
        t.has_subordinates,
        -- The refusal is decided on the GRAPH, not on the has_subordinates
        -- flag: trg_update_has_subordinates only fires on INSERT / DELETE /
        -- UPDATE OF manager_id, so the flag is a cache. Terminated reports do
        -- not count — they are forgotten too, so nobody is orphaned by them.
        COALESCE((
          SELECT json_agg(json_build_object('id', r.id, 'full_name', r.full_name) ORDER BY r.full_name)
          FROM performance_db.users r
          WHERE r.manager_id = t.id AND r.terminated_at IS NULL
        ), '[]'::json) AS active_reports,
        (SELECT cp.id FROM performance_db.evaluation_periods cp
          WHERE cp.is_active = true AND cp.status = 'active'
            AND cp.period_type <> 'annual'
            AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                            WHERE child.parent_period_id = cp.id)
          LIMIT 1) AS active_period_id
      FROM performance_db.users t
      WHERE t.id = ${userId}
    `,
  },
};
""".strip()

EMPLOYMENT_TERMINATE_BUILD = """
const prev = $('Validate Terminate').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.target_id !== undefined);
if (!check) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'USER_NOT_FOUND', message: 'Сотрудник не найден' },
    },
  };
}
if (check.already_terminated === true || check.already_terminated === 't') {
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'ALREADY_TERMINATED', message: 'Сотрудник уже отмечен как уволенный' },
    },
  };
}
let reports = check.active_reports;
if (typeof reports === 'string') {
  try { reports = JSON.parse(reports); } catch { reports = []; }
}
if (!Array.isArray(reports)) reports = [];
if (reports.length) {
  // The message the owner reads. It names the people, because "reassign first"
  // is useless without knowing whom. A terminated manager would leave every
  // one of these evaluated by nobody: an out-of-scope actor gets no task list.
  const names = reports.map(r => r.full_name).join(', ');
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'HAS_DIRECT_REPORTS',
        message: `Нельзя уволить: у сотрудника есть прямые подчинённые (${reports.length}) — ${names}. Сначала переназначьте их другому руководителю.`,
        reports,
      },
    },
  };
}
const userId = Number(prev.user_id);
const actorId = Number(prev.actor_id);
const terminationDate = String(prev.termination_date);
const noteLiteral = prev.note ? `'${String(prev.note).replace(/'/g, "''")}'` : 'NULL';
const periodLiteral = check.active_period_id === null || check.active_period_id === undefined
  ? 'NULL'
  : String(Number(check.active_period_id));

// One statement. Every precondition is re-asserted inside `target`, so a lost
// race selects zero rows and every branch below it changes zero rows —
// the BUG-041 rule: one gate for every data-modifying branch.
return {
  json: {
    ok: true,
    user_id: userId,
    sql: `
WITH target AS (
  SELECT u.id, u.full_name
  FROM performance_db.users u
  WHERE u.id = ${userId}
    AND u.terminated_at IS NULL
    AND NOT EXISTS (
      SELECT 1 FROM performance_db.users r
      WHERE r.manager_id = u.id AND r.terminated_at IS NULL
    )
  FOR UPDATE OF u
),
marked AS (
  UPDATE performance_db.users u
  SET terminated_at = now(),
      termination_date = '${terminationDate}'::date,
      -- The guard joins auth_sessions ON token_version = users.token_version,
      -- so the bump alone makes every live JWT unusable on the next request.
      token_version = u.token_version + 1
  WHERE u.id IN (SELECT id FROM target)
  RETURNING u.id, u.full_name, u.token_version
),
revoked AS (
  UPDATE performance_db.auth_sessions s
  SET revoked_at = now()
  WHERE s.user_id IN (SELECT id FROM target) AND s.revoked_at IS NULL
  RETURNING s.jti
),
burned AS (
  -- An outstanding reset link would otherwise let the person set a new
  -- password. Login refuses them anyway, but the link is closed at the source.
  UPDATE performance_db.password_reset_tokens t
  SET used_at = now()
  WHERE t.user_id IN (SELECT id FROM target) AND t.used_at IS NULL
  RETURNING t.id
),
scoped_out AS (
  -- Only rows that are currently IN scope, and only periods that are not
  -- closed. A person already excluded for another reason (hired_after_period_end)
  -- keeps that reason, so reinstatement cannot wrongly put them back in scope;
  -- a closed period and the 2025 archive are never touched.
  UPDATE performance_db.evaluation_period_participants epp
  SET is_in_scope = false,
      exclusion_reason = 'terminated',
      updated_at = now()
  WHERE epp.user_id IN (SELECT id FROM target)
    AND epp.is_in_scope = true
    AND epp.period_id IN (
      SELECT p.id FROM performance_db.evaluation_periods p WHERE p.status <> 'closed'
    )
  RETURNING epp.period_id
),
logged AS (
  INSERT INTO performance_db.employment_events
    (user_id, event_type, effective_date, period_id, actor_id, note)
  SELECT t.id, 'terminated', '${terminationDate}'::date, ${periodLiteral}, ${actorId}, ${noteLiteral}
  FROM target t
  RETURNING id, occurred_at
)
SELECT
  (SELECT count(*)::integer FROM marked) AS marked,
  (SELECT full_name FROM marked LIMIT 1) AS full_name,
  (SELECT count(*)::integer FROM revoked) AS sessions_revoked,
  (SELECT count(*)::integer FROM burned) AS reset_tokens_invalidated,
  (SELECT COALESCE(json_agg(period_id ORDER BY period_id), '[]'::json) FROM scoped_out) AS scoped_out_period_ids,
  (SELECT count(*)::integer FROM logged) AS events_logged,
  (SELECT id FROM logged LIMIT 1) AS event_id
    `,
  },
};
""".strip()

EMPLOYMENT_TERMINATE_FORMAT = """
const prev = $('Build Terminate SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.marked !== undefined);
if (!row || Number(row.marked) === 0) {
  // The gate inside the statement refused after the pre-check passed: somebody
  // else changed the row in between. Nothing was written.
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'TERMINATE_CONFLICT',
        message: 'Состояние сотрудника изменилось во время операции — обновите страницу и повторите',
      },
    },
  };
}
let periodIds = row.scoped_out_period_ids;
if (typeof periodIds === 'string') {
  try { periodIds = JSON.parse(periodIds); } catch { periodIds = []; }
}
if (!Array.isArray(periodIds)) periodIds = [];
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      user_id: Number(prev.user_id),
      full_name: row.full_name,
      event_id: row.event_id != null ? Number(row.event_id) : null,
      sessions_revoked: Number(row.sessions_revoked) || 0,
      reset_tokens_invalidated: Number(row.reset_tokens_invalidated) || 0,
      scoped_out_period_ids: periodIds.map(Number),
      message: 'Сотрудник отмечен как уволенный',
    },
  },
};
""".strip()

EMPLOYMENT_REINSTATE_VALIDATE = """
const guard = $('Run Auth Guard REINSTATE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request;
const userId = parseInt(body.user_id, 10);
if (!Number.isFinite(userId) || userId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_USER_ID', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
    },
  };
}
const note = String(body.note || '').trim().slice(0, 500);
return {
  json: {
    ok: true,
    actor_id: actorId,
    user_id: userId,
    note,
    sql: `
      SELECT
        t.id AS target_id,
        t.full_name AS target_name,
        (t.terminated_at IS NOT NULL) AS is_terminated,
        (SELECT cp.id FROM performance_db.evaluation_periods cp
          WHERE cp.is_active = true AND cp.status = 'active'
            AND cp.period_type <> 'annual'
            AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods child
                            WHERE child.parent_period_id = cp.id)
          LIMIT 1) AS active_period_id
      FROM performance_db.users t
      WHERE t.id = ${userId}
    `,
  },
};
""".strip()

EMPLOYMENT_REINSTATE_BUILD = """
const prev = $('Validate Reinstate').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.target_id !== undefined);
if (!check) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'USER_NOT_FOUND', message: 'Сотрудник не найден' },
    },
  };
}
if (!(check.is_terminated === true || check.is_terminated === 't')) {
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'NOT_TERMINATED', message: 'Сотрудник не отмечен как уволенный' },
    },
  };
}
const userId = Number(prev.user_id);
const actorId = Number(prev.actor_id);
const noteLiteral = prev.note ? `'${String(prev.note).replace(/'/g, "''")}'` : 'NULL';
const periodLiteral = check.active_period_id === null || check.active_period_id === undefined
  ? 'NULL'
  : String(Number(check.active_period_id));

// token_version is deliberately NOT rolled back: revoking a session is a
// one-way security action, and reinstatement is not a reason to resurrect a
// token that was already handed out. The person simply logs in again.
return {
  json: {
    ok: true,
    user_id: userId,
    sql: `
WITH target AS (
  SELECT u.id, u.full_name
  FROM performance_db.users u
  WHERE u.id = ${userId} AND u.terminated_at IS NOT NULL
  FOR UPDATE OF u
),
restored AS (
  UPDATE performance_db.users u
  SET terminated_at = NULL, termination_date = NULL
  WHERE u.id IN (SELECT id FROM target)
  RETURNING u.id, u.full_name
),
scoped_in AS (
  -- Only the rows this feature excluded. exclusion_reason = 'terminated' is the
  -- marker; a row excluded for hired_after_period_end is left exactly as it is,
  -- so the round trip is exact for a person who is both.
  UPDATE performance_db.evaluation_period_participants epp
  SET is_in_scope = true,
      exclusion_reason = NULL,
      updated_at = now()
  WHERE epp.user_id IN (SELECT id FROM target)
    AND epp.exclusion_reason = 'terminated'
    AND epp.period_id IN (
      SELECT p.id FROM performance_db.evaluation_periods p WHERE p.status <> 'closed'
    )
  RETURNING epp.period_id
),
logged AS (
  INSERT INTO performance_db.employment_events
    (user_id, event_type, effective_date, period_id, actor_id, note)
  SELECT t.id, 'reinstated', NULL, ${periodLiteral}, ${actorId}, ${noteLiteral}
  FROM target t
  RETURNING id
)
SELECT
  (SELECT count(*)::integer FROM restored) AS restored,
  (SELECT full_name FROM restored LIMIT 1) AS full_name,
  (SELECT COALESCE(json_agg(period_id ORDER BY period_id), '[]'::json) FROM scoped_in) AS scoped_in_period_ids,
  (SELECT count(*)::integer FROM logged) AS events_logged,
  (SELECT id FROM logged LIMIT 1) AS event_id
    `,
  },
};
""".strip()

EMPLOYMENT_REINSTATE_FORMAT = """
const prev = $('Build Reinstate SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.restored !== undefined);
if (!row || Number(row.restored) === 0) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'REINSTATE_CONFLICT',
        message: 'Состояние сотрудника изменилось во время операции — обновите страницу и повторите',
      },
    },
  };
}
let periodIds = row.scoped_in_period_ids;
if (typeof periodIds === 'string') {
  try { periodIds = JSON.parse(periodIds); } catch { periodIds = []; }
}
if (!Array.isArray(periodIds)) periodIds = [];
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      user_id: Number(prev.user_id),
      full_name: row.full_name,
      event_id: row.event_id != null ? Number(row.event_id) : null,
      scoped_in_period_ids: periodIds.map(Number),
      message: 'Сотрудник восстановлен',
    },
  },
};
""".strip()

EMPLOYMENT_HISTORY_BUILD = """
const guard = $('Run Auth Guard HISTORY').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const request = guard.request || {};
const query = request.query || {};
const parsed = parseInt(query.user_id ?? query.userId, 10);
const userFilter = Number.isFinite(parsed) && parsed > 0
  ? `WHERE e.user_id = ${parsed}`
  : '';
// The termination event has to stay readable after the period closes, so this
// route reads employment_events directly and never depends on the person still
// being out of scope, or on the period still being open.
return {
  json: {
    ok: true,
    sql: `
      SELECT
        e.id,
        e.user_id,
        u.full_name,
        e.event_type,
        to_char(e.effective_date, 'YYYY-MM-DD') AS effective_date,
        e.period_id,
        p.name AS period_name,
        e.actor_id,
        a.full_name AS actor_name,
        to_char(e.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS occurred_at,
        e.note
      FROM performance_db.employment_events e
      JOIN performance_db.users u ON u.id = e.user_id
      JOIN performance_db.users a ON a.id = e.actor_id
      LEFT JOIN performance_db.evaluation_periods p ON p.id = e.period_id
      ${userFilter}
      ORDER BY e.occurred_at DESC, e.id DESC
      LIMIT 500
    `,
  },
};
""".strip()

EMPLOYMENT_HISTORY_FORMAT = """
const guard = $('Run Auth Guard HISTORY').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const events = $input.all().map(item => item.json).filter(item => item.id !== undefined);
return {
  json: {
    http_status: 200,
    body: { success: true, events },
  },
};
""".strip()


def build_manage_employment(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    def pg(node_id: str, name: str, position: list[int], empty_column: str) -> dict[str, Any]:
        return node(
            node_id, name, "n8n-nodes-base.postgres", position,
            {"operation": "executeQuery",
             "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS "
                      + empty_column + " WHERE false' }}",
             "options": {}},
            type_version=2.6,
            credentials=postgres_credentials(credential_id), always_output=True)

    nodes_list = [
        # TERMINATE
        node("employment-webhook-terminate", "Webhook TERMINATE", "n8n-nodes-base.webhook",
             [-700, 0],
             {"httpMethod": "POST", "path": "api/admin/terminate-employee",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-employment-terminate"),
        node("employment-guard-input-terminate", "Prepare Guard Input TERMINATE",
             "n8n-nodes-base.code", [-480, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("employment-run-guard-terminate", "Run Auth Guard TERMINATE",
                       [-250, 0], guard_workflow_id),
        node("employment-terminate-validate", "Validate Terminate", "n8n-nodes-base.code",
             [0, 0], {"jsCode": EMPLOYMENT_TERMINATE_VALIDATE}),
        pg("employment-terminate-check", "Load Terminate Target", [250, 0], "target_id"),
        node("employment-terminate-build", "Build Terminate SQL", "n8n-nodes-base.code",
             [500, 0], {"jsCode": EMPLOYMENT_TERMINATE_BUILD}),
        pg("employment-terminate-execute", "Execute Terminate", [750, 0], "marked"),
        node("employment-terminate-format", "Format Terminate Response", "n8n-nodes-base.code",
             [1000, 0], {"jsCode": EMPLOYMENT_TERMINATE_FORMAT}),
        respond_node("employment-respond-terminate", "Respond TERMINATE", [1240, 0]),
        # REINSTATE
        node("employment-webhook-reinstate", "Webhook REINSTATE", "n8n-nodes-base.webhook",
             [-700, 300],
             {"httpMethod": "POST", "path": "api/admin/reinstate-employee",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-employment-reinstate"),
        node("employment-guard-input-reinstate", "Prepare Guard Input REINSTATE",
             "n8n-nodes-base.code", [-480, 300], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("employment-run-guard-reinstate", "Run Auth Guard REINSTATE",
                       [-250, 300], guard_workflow_id),
        node("employment-reinstate-validate", "Validate Reinstate", "n8n-nodes-base.code",
             [0, 300], {"jsCode": EMPLOYMENT_REINSTATE_VALIDATE}),
        pg("employment-reinstate-check", "Load Reinstate Target", [250, 300], "target_id"),
        node("employment-reinstate-build", "Build Reinstate SQL", "n8n-nodes-base.code",
             [500, 300], {"jsCode": EMPLOYMENT_REINSTATE_BUILD}),
        pg("employment-reinstate-execute", "Execute Reinstate", [750, 300], "restored"),
        node("employment-reinstate-format", "Format Reinstate Response", "n8n-nodes-base.code",
             [1000, 300], {"jsCode": EMPLOYMENT_REINSTATE_FORMAT}),
        respond_node("employment-respond-reinstate", "Respond REINSTATE", [1240, 300]),
        # HISTORY — the record, readable after the period closes
        node("employment-webhook-history", "Webhook HISTORY", "n8n-nodes-base.webhook",
             [-700, 600],
             {"httpMethod": "GET", "path": "api/admin/employment-events",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-employment-events"),
        node("employment-guard-input-history", "Prepare Guard Input HISTORY",
             "n8n-nodes-base.code", [-480, 600], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("employment-run-guard-history", "Run Auth Guard HISTORY",
                       [-250, 600], guard_workflow_id),
        node("employment-history-build", "Build Events Query", "n8n-nodes-base.code",
             [0, 600], {"jsCode": EMPLOYMENT_HISTORY_BUILD}),
        pg("employment-history-load", "Load Events", [250, 600], "id"),
        node("employment-history-format", "Format Events Response", "n8n-nodes-base.code",
             [500, 600], {"jsCode": EMPLOYMENT_HISTORY_FORMAT}),
        respond_node("employment-respond-history", "Respond HISTORY", [740, 600]),
    ]
    connections = {
        "Webhook TERMINATE": connect("Prepare Guard Input TERMINATE"),
        "Prepare Guard Input TERMINATE": connect("Run Auth Guard TERMINATE"),
        "Run Auth Guard TERMINATE": connect("Validate Terminate"),
        "Validate Terminate": connect("Load Terminate Target"),
        "Load Terminate Target": connect("Build Terminate SQL"),
        "Build Terminate SQL": connect("Execute Terminate"),
        "Execute Terminate": connect("Format Terminate Response"),
        "Format Terminate Response": connect("Respond TERMINATE"),
        "Webhook REINSTATE": connect("Prepare Guard Input REINSTATE"),
        "Prepare Guard Input REINSTATE": connect("Run Auth Guard REINSTATE"),
        "Run Auth Guard REINSTATE": connect("Validate Reinstate"),
        "Validate Reinstate": connect("Load Reinstate Target"),
        "Load Reinstate Target": connect("Build Reinstate SQL"),
        "Build Reinstate SQL": connect("Execute Reinstate"),
        "Execute Reinstate": connect("Format Reinstate Response"),
        "Format Reinstate Response": connect("Respond REINSTATE"),
        "Webhook HISTORY": connect("Prepare Guard Input HISTORY"),
        "Prepare Guard Input HISTORY": connect("Run Auth Guard HISTORY"),
        "Run Auth Guard HISTORY": connect("Build Events Query"),
        "Build Events Query": connect("Load Events"),
        "Load Events": connect("Format Events Response"),
        "Format Events Response": connect("Respond HISTORY"),
    }
    return workflow("API: Manage Employment Status", nodes_list, connections)


# ── 19. Period scope by hand — API: Manage Period Scope ───────────────────────
#
# Brief MID_YEAR_HIRES_SCOPE (2026-08-25). Before this workflow the ONLY writer
# of evaluation_period_participants.is_in_scope on live was
# POST /api/periods/create (once, at creation, from join_date > end_date) and
# the two employment routes. There was no way to take an EMPLOYED person out of
# scope of a period that already existed without raw SQL.
#
# This reuses the scope machinery of D-0825-7 and deliberately reuses nothing
# else: no users column is written, no session is revoked, no reset token is
# burned, no capability flag moves. The person stays employed, keeps their
# login, can still register through the shared invite, and enters H2 normally.
#
# exclusion_reason is 'excluded_by_admin' — distinct by construction from
# 'terminated' and from 'hired_after_period_end', so reinstatement of a leaver
# can never pick up one of these rows and vice versa.

PERIOD_SCOPE_EXCLUDE_VALIDATE = """
const guard = $('Run Auth Guard EXCLUDE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request;

const userId = parseInt(body.user_id, 10);
if (!Number.isFinite(userId) || userId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_USER_ID', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
    },
  };
}
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' },
    },
  };
}
// The note is the owner's words for WHY. The machine reason is always
// 'excluded_by_admin'; the sentence that makes it auditable a year later lives
// here.
const note = String(body.note || '').trim().slice(0, 500);

return {
  json: {
    ok: true,
    actor_id: actorId,
    user_id: userId,
    period_id: periodId,
    note,
    sql: `
      SELECT
        u.id AS target_id,
        u.full_name AS target_name,
        (u.terminated_at IS NOT NULL) AS target_terminated,
        (SELECT p.id FROM performance_db.evaluation_periods p WHERE p.id = ${periodId}) AS period_id_found,
        (SELECT p.name FROM performance_db.evaluation_periods p WHERE p.id = ${periodId}) AS period_name,
        (SELECT p.status FROM performance_db.evaluation_periods p WHERE p.id = ${periodId}) AS period_status,
        (SELECT epp.is_in_scope FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId} AND epp.user_id = ${userId}) AS row_is_in_scope,
        EXISTS (SELECT 1 FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId} AND epp.user_id = ${userId}) AS row_exists,
        (SELECT epp.exclusion_reason FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId} AND epp.user_id = ${userId}) AS row_reason,
        -- The GAVE / ABOUT split, counted separately, because the two halves
        -- behave differently and the caller has to be told which is which
        -- BEFORE confirming rather than after.
        (SELECT count(*)::integer FROM performance_db.evaluations e
          WHERE e.period_id = ${periodId} AND e.subject_id = ${userId}
            AND e.is_self_evaluation = false) AS evaluations_received,
        (SELECT count(*)::integer FROM performance_db.evaluations e
          WHERE e.period_id = ${periodId} AND e.subject_id = ${userId}
            AND e.is_self_evaluation = true) AS self_reviews,
        (SELECT count(*)::integer FROM performance_db.evaluations e
          WHERE e.period_id = ${periodId} AND e.evaluator_id = ${userId}
            AND e.is_self_evaluation = false) AS evaluations_given,
        (SELECT count(*)::integer FROM performance_db.score_corrections sc
          WHERE sc.period_id = ${periodId} AND sc.subject_id = ${userId}) AS corrections_about,
        -- Not a refusal: surfaced so the caller sees who is left without an
        -- evaluator. An out-of-scope actor gets no task list, so every one of
        -- these people would be evaluated by nobody until they are reassigned
        -- or excluded too. Whether that is acceptable is the owner's call, not
        -- this route's.
        COALESCE((
          SELECT json_agg(json_build_object('id', r.id, 'full_name', r.full_name) ORDER BY r.full_name)
          FROM performance_db.users r
          JOIN performance_db.evaluation_period_participants rp
            ON rp.user_id = r.id AND rp.period_id = ${periodId} AND rp.is_in_scope = true
          WHERE r.manager_id = ${userId} AND r.terminated_at IS NULL
        ), '[]'::json) AS reports_in_scope
      FROM performance_db.users u
      WHERE u.id = ${userId}
    `,
  },
};
"""


PERIOD_SCOPE_EXCLUDE_BUILD = """
const prev = $('Validate Exclude').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.target_id !== undefined);
if (!check) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'USER_NOT_FOUND', message: 'Сотрудник не найден' },
    },
  };
}
if (check.period_id_found === null || check.period_id_found === undefined) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' },
    },
  };
}
// A closed period is history and its period_results are already frozen. Nothing
// in this feature may touch one, in either direction.
if (String(check.period_status) === 'closed') {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'PERIOD_CLOSED',
        message: `Период «${check.period_name}» закрыт: охват закрытого периода не меняется`,
      },
    },
  };
}
const rowExists = check.row_exists === true || check.row_exists === 't';
if (!rowExists) {
  // Participation rows are written once, when the period is created. A person
  // added to the system afterwards has none — and is already invisible to every
  // read surface. This route does not invent the row, because inventing it
  // would make the person a participant of a period they were never in.
  return {
    json: {
      http_status: 404,
      body: {
        success: false,
        error: 'NOT_A_PARTICIPANT',
        message: `У сотрудника нет строки участия в периоде «${check.period_name}» — он был заведён в систему после создания периода и уже вне охвата. Исключать нечего.`,
      },
    },
  };
}
const inScope = check.row_is_in_scope === true || check.row_is_in_scope === 't';
if (!inScope) {
  const reason = check.row_reason || 'не указана';
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'ALREADY_EXCLUDED',
        message: `Сотрудник уже вне охвата периода «${check.period_name}» (причина: ${reason})`,
        current_reason: check.row_reason || null,
      },
    },
  };
}
let reports = check.reports_in_scope;
if (typeof reports === 'string') {
  try { reports = JSON.parse(reports); } catch { reports = []; }
}
if (!Array.isArray(reports)) reports = [];

const received = Number(check.evaluations_received) || 0;
const selfReviews = Number(check.self_reviews) || 0;
const given = Number(check.evaluations_given) || 0;
const corrections = Number(check.corrections_about) || 0;
const total = received + selfReviews + given + corrections;

if (total > 0) {
  // D-0826-4 supersedes the old confirmation escape hatch: taking somebody
  // out after any evaluation exists is always refused. The response still
  // names both halves so the owner sees exactly what would stop counting and
  // what would remain, but no second request can override the refusal.
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'HAS_EVALUATIONS',
        message: `В периоде «${check.period_name}» у сотрудника уже есть данные оценки, поэтому вывести его из охвата нельзя. Перестали бы считаться оценки, которые он ПОЛУЧИЛ (${received}), его самооценка (${selfReviews}) и корректировки по нему (${corrections}). Оценки, которые он ПОСТАВИЛ другим (${given}), остались бы у этих людей. Ничего не изменено.`,
        evaluations_received: received,
        self_reviews: selfReviews,
        evaluations_given: given,
        corrections_about: corrections,
        reports_in_scope: reports,
      },
    },
  };
}

const userId = Number(prev.user_id);
const periodId = Number(prev.period_id);
const actorId = Number(prev.actor_id);
const noteLiteral = prev.note ? `'${String(prev.note).replace(/'/g, "''")}'` : 'NULL';

// One statement. Every precondition is re-asserted inside `target`, so a lost
// race selects zero rows and both branches below it change zero rows — the
// same one-gate rule the close, termination and additive-submit paths use.
return {
  json: {
    ok: true,
    user_id: userId,
    period_id: periodId,
    period_name: check.period_name,
    full_name: check.target_name,
    evaluations_received: received,
    self_reviews: selfReviews,
    evaluations_given: given,
    corrections_about: corrections,
    reports_in_scope: reports,
    sql: `
WITH target AS (
  SELECT epp.period_id, epp.user_id
  FROM performance_db.evaluation_period_participants epp
  WHERE epp.period_id = ${periodId}
    AND epp.user_id = ${userId}
    AND epp.is_in_scope = true
    AND EXISTS (
      SELECT 1 FROM performance_db.evaluation_periods p
      WHERE p.id = ${periodId} AND p.status <> 'closed'
    )
  FOR UPDATE OF epp
),
scoped_out AS (
  UPDATE performance_db.evaluation_period_participants epp
  SET is_in_scope = false,
      exclusion_reason = 'excluded_by_admin',
      scope_override = 'excluded_by_admin',
      updated_at = now()
  WHERE (epp.period_id, epp.user_id) IN (SELECT period_id, user_id FROM target)
  RETURNING epp.period_id
),
logged AS (
  INSERT INTO performance_db.period_scope_events
    (period_id, user_id, event_type, reason, actor_id, note)
  SELECT t.period_id, t.user_id, 'excluded', 'excluded_by_admin', ${actorId}, ${noteLiteral}
  FROM target t
  RETURNING id
)
SELECT
  (SELECT count(*)::integer FROM scoped_out) AS changed,
  (SELECT id FROM logged LIMIT 1) AS event_id
    `,
  },
};
"""


PERIOD_SCOPE_EXCLUDE_FORMAT = """
const prev = $('Build Exclude SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.changed !== undefined);
if (!row || Number(row.changed) === 0) {
  // The gate inside the statement refused after the pre-check passed: somebody
  // else changed the row in between. Nothing was written.
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'SCOPE_CONFLICT',
        message: 'Состояние участия изменилось во время операции — обновите страницу и повторите',
      },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      user_id: Number(prev.user_id),
      period_id: Number(prev.period_id),
      period_name: prev.period_name,
      full_name: prev.full_name,
      exclusion_reason: 'excluded_by_admin',
      event_id: row.event_id != null ? Number(row.event_id) : null,
      evaluations_received: prev.evaluations_received,
      self_reviews: prev.self_reviews,
      evaluations_given: prev.evaluations_given,
      corrections_about: prev.corrections_about,
      reports_in_scope: prev.reports_in_scope,
      message: 'Сотрудник выведен из охвата периода',
    },
  },
};
"""


PERIOD_SCOPE_INCLUDE_VALIDATE = """
const guard = $('Run Auth Guard INCLUDE').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request;

const userId = parseInt(body.user_id, 10);
if (!Number.isFinite(userId) || userId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_USER_ID', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
    },
  };
}
const periodId = parseInt(body.period_id, 10);
if (!Number.isFinite(periodId) || periodId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' },
    },
  };
}
const note = String(body.note || '').trim().slice(0, 500);

return {
  json: {
    ok: true,
    actor_id: actorId,
    user_id: userId,
    period_id: periodId,
    note,
    sql: `
      SELECT
        u.id AS target_id,
        u.full_name AS target_name,
        (SELECT p.id FROM performance_db.evaluation_periods p WHERE p.id = ${periodId}) AS period_id_found,
        (SELECT p.name FROM performance_db.evaluation_periods p WHERE p.id = ${periodId}) AS period_name,
        (SELECT p.status FROM performance_db.evaluation_periods p WHERE p.id = ${periodId}) AS period_status,
        EXISTS (SELECT 1 FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId} AND epp.user_id = ${userId}) AS row_exists,
        (SELECT epp.is_in_scope FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId} AND epp.user_id = ${userId}) AS row_is_in_scope,
        (SELECT epp.exclusion_reason FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = ${periodId} AND epp.user_id = ${userId}) AS row_reason
      FROM performance_db.users u
      WHERE u.id = ${userId}
    `,
  },
};
"""


PERIOD_SCOPE_INCLUDE_BUILD = """
const prev = $('Validate Include').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.target_id !== undefined);
if (!check) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'USER_NOT_FOUND', message: 'Сотрудник не найден' },
    },
  };
}
if (check.period_id_found === null || check.period_id_found === undefined) {
  return {
    json: {
      http_status: 404,
      body: { success: false, error: 'PERIOD_NOT_FOUND', message: 'Период не найден' },
    },
  };
}
if (String(check.period_status) === 'closed') {
  return {
    json: {
      http_status: 422,
      body: {
        success: false,
        error: 'PERIOD_CLOSED',
        message: `Период «${check.period_name}» закрыт: охват закрытого периода не меняется`,
      },
    },
  };
}
if (!(check.row_exists === true || check.row_exists === 't')) {
  return {
    json: {
      http_status: 404,
      body: {
        success: false,
        error: 'NOT_A_PARTICIPANT',
        message: `У сотрудника нет строки участия в периоде «${check.period_name}» — возвращать в охват нечего.`,
      },
    },
  };
}
// The marker, and the whole reason the reverse action is exact: only rows this
// feature wrote are flipped back. A row excluded for 'terminated' or for
// 'hired_after_period_end' is left exactly as it is, so a person who is both
// stays out for the other reason and the round trip is byte-exact.
//
// D-0825-12 adds a second admissible reason: 'join_date_missing'. That reason is
// written by period creation for somebody with no hire date, and its whole point
// is that it MUST be confirmable by hand — an admin who checks the person and
// decides they belong in the period needs a way in. Without this the new reason
// would be a state with no exit. It stays distinct from 'terminated', which is
// reinstatement's population and is still refused here.
const REVERSIBLE_REASONS = [
  'excluded_by_admin',
  'join_date_missing',
  'hired_after_period_end',
  'insufficient_tenure',
];
if (!REVERSIBLE_REASONS.includes(String(check.row_reason || ''))) {
  const inScope = check.row_is_in_scope === true || check.row_is_in_scope === 't';
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'NOT_EXCLUDED_BY_ADMIN',
        message: inScope
          ? `Сотрудник и так в охвате периода «${check.period_name}»`
          : `Сотрудник вне охвата периода «${check.period_name}» по другой причине (${check.row_reason}) — этот маршрут её не отменяет`,
        current_reason: check.row_reason || null,
      },
    },
  };
}

const userId = Number(prev.user_id);
const periodId = Number(prev.period_id);
const actorId = Number(prev.actor_id);
const noteLiteral = prev.note ? `'${String(prev.note).replace(/'/g, "''")}'` : 'NULL';

return {
  json: {
    ok: true,
    user_id: userId,
    period_id: periodId,
    period_name: check.period_name,
    full_name: check.target_name,
    sql: `
WITH target AS (
  SELECT epp.period_id, epp.user_id
  FROM performance_db.evaluation_period_participants epp
  WHERE epp.period_id = ${periodId}
    AND epp.user_id = ${userId}
    AND epp.is_in_scope = false
    AND epp.exclusion_reason IN (
      'excluded_by_admin', 'join_date_missing',
      'hired_after_period_end', 'insufficient_tenure'
    )
    AND EXISTS (
      SELECT 1 FROM performance_db.evaluation_periods p
      WHERE p.id = ${periodId} AND p.status <> 'closed'
    )
  FOR UPDATE OF epp
),
scoped_in AS (
  UPDATE performance_db.evaluation_period_participants epp
  SET is_in_scope = true,
      exclusion_reason = NULL,
      scope_override = 'included_by_admin',
      updated_at = now()
  WHERE (epp.period_id, epp.user_id) IN (SELECT period_id, user_id FROM target)
  RETURNING epp.period_id
),
logged AS (
  INSERT INTO performance_db.period_scope_events
    (period_id, user_id, event_type, reason, actor_id, note)
  SELECT t.period_id, t.user_id, 'included', NULL, ${actorId}, ${noteLiteral}
  FROM target t
  RETURNING id
)
SELECT
  (SELECT count(*)::integer FROM scoped_in) AS changed,
  (SELECT id FROM logged LIMIT 1) AS event_id
    `,
  },
};
"""


PERIOD_SCOPE_INCLUDE_FORMAT = """
const prev = $('Build Include SQL').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.changed !== undefined);
if (!row || Number(row.changed) === 0) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'SCOPE_CONFLICT',
        message: 'Состояние участия изменилось во время операции — обновите страницу и повторите',
      },
    },
  };
}
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      user_id: Number(prev.user_id),
      period_id: Number(prev.period_id),
      period_name: prev.period_name,
      full_name: prev.full_name,
      event_id: row.event_id != null ? Number(row.event_id) : null,
      message: 'Сотрудник возвращён в охват периода',
    },
  },
};
"""


PERIOD_SCOPE_HISTORY_BUILD = """
const guard = $('Run Auth Guard SCOPE HISTORY').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const query = (guard.request && guard.request.query) || {};
const filters = [];
const rawUser = query.user_id;
if (rawUser !== undefined && rawUser !== null && String(rawUser).trim() !== '') {
  const userId = parseInt(rawUser, 10);
  if (!Number.isFinite(userId) || userId < 1) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_USER_ID', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
      },
    };
  }
  filters.push(`e.user_id = ${userId}`);
}
const rawPeriod = query.period_id;
if (rawPeriod !== undefined && rawPeriod !== null && String(rawPeriod).trim() !== '') {
  const periodId = parseInt(rawPeriod, 10);
  if (!Number.isFinite(periodId) || periodId < 1) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_PERIOD_ID', message: 'Идентификатор периода должен быть положительным целым числом' },
      },
    };
  }
  filters.push(`e.period_id = ${periodId}`);
}
const where = filters.length ? `WHERE ${filters.join(' AND ')}` : '';
return {
  json: {
    ok: true,
    sql: `
      SELECT
        e.id, e.period_id, e.user_id, e.event_type, e.reason, e.actor_id,
        to_char(e.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS occurred_at,
        e.note,
        u.full_name AS user_full_name,
        a.full_name AS actor_full_name,
        p.name AS period_name
      FROM performance_db.period_scope_events e
      JOIN performance_db.users u ON u.id = e.user_id
      LEFT JOIN performance_db.users a ON a.id = e.actor_id
      LEFT JOIN performance_db.evaluation_periods p ON p.id = e.period_id
      ${where}
      ORDER BY e.occurred_at DESC, e.id DESC
    `,
  },
};
"""


PERIOD_SCOPE_HISTORY_FORMAT = """
const prev = $('Build Scope Events Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const events = $input.all().map(item => item.json).filter(item => item.id !== undefined && item.id !== null);
return {
  json: {
    http_status: 200,
    body: { success: true, events, total: events.length },
  },
};
"""


EMPLOYEE_EVENTS_BUILD = """
const guard = $('Run Auth Guard EMPLOYEE EVENTS').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
const query = (guard.request && guard.request.query) || {};
const rawUser = query.user_id;
let userFilter = '';
if (rawUser !== undefined && rawUser !== null && String(rawUser).trim() !== '') {
  const userId = parseInt(rawUser, 10);
  if (!Number.isFinite(userId) || userId < 1) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_USER_ID', message: 'Идентификатор сотрудника должен быть положительным целым числом' },
      },
    };
  }
  userFilter = `WHERE events.user_id = ${userId}`;
}
if (!userFilter) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'USER_ID_REQUIRED', message: 'Параметр user_id обязателен' },
    },
  };
}
return {
  json: {
    ok: true,
    sql: `
      SELECT *
      FROM (
        SELECT
          ce.id AS event_id,
          'card'::text AS source,
          ce.event_type,
          ce.user_id,
          NULL::integer AS period_id,
          ce.actor_id,
          ce.occurred_at,
          jsonb_build_object('changes', ce.changes) AS details
        FROM performance_db.employee_card_events ce
        UNION ALL
        SELECT
          se.id AS event_id,
          'scope'::text AS source,
          se.event_type,
          se.user_id,
          se.period_id,
          se.actor_id,
          se.occurred_at,
          jsonb_build_object('reason', se.reason, 'note', se.note) AS details
        FROM performance_db.period_scope_events se
        UNION ALL
        SELECT
          ee.id AS event_id,
          'employment'::text AS source,
          ee.event_type,
          ee.user_id,
          ee.period_id,
          ee.actor_id,
          ee.occurred_at,
          jsonb_build_object(
            'effective_date', to_char(ee.effective_date, 'YYYY-MM-DD'),
            'note', ee.note
          ) AS details
        FROM performance_db.employment_events ee
      ) events
      ${userFilter}
      ORDER BY events.occurred_at DESC, events.source, events.event_id DESC
    `,
  },
};
"""


EMPLOYEE_EVENTS_FORMAT = """
const prev = $('Build Employee Events Query').first().json;
if (prev.http_status) {
  return { json: prev };
}
const rows = $input.all().map(item => item.json)
  .filter(item => item.event_id !== undefined && item.event_id !== null);
const events = rows.map((row) => ({
  ...row,
  occurred_at: row.occurred_at instanceof Date
    ? row.occurred_at.toISOString()
    : row.occurred_at,
}));
return {
  json: {
    http_status: 200,
    body: { success: true, events, total: events.length },
  },
};
"""


def build_manage_period_scope(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    def pg(node_id: str, name: str, position: list[int], empty_column: str) -> dict[str, Any]:
        return node(
            node_id, name, "n8n-nodes-base.postgres", position,
            {"operation": "executeQuery",
             "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS "
                      + empty_column + " WHERE false' }}",
             "options": {}},
            type_version=2.6,
            credentials=postgres_credentials(credential_id), always_output=True)

    nodes_list = [
        # EXCLUDE
        node("scope-webhook-exclude", "Webhook EXCLUDE", "n8n-nodes-base.webhook",
             [-700, 0],
             {"httpMethod": "POST", "path": "api/admin/exclude-participant",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-scope-exclude"),
        node("scope-guard-input-exclude", "Prepare Guard Input EXCLUDE",
             "n8n-nodes-base.code", [-480, 0], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("scope-run-guard-exclude", "Run Auth Guard EXCLUDE",
                       [-250, 0], guard_workflow_id),
        node("scope-exclude-validate", "Validate Exclude", "n8n-nodes-base.code",
             [0, 0], {"jsCode": PERIOD_SCOPE_EXCLUDE_VALIDATE}),
        pg("scope-exclude-check", "Load Exclude Target", [250, 0], "target_id"),
        node("scope-exclude-build", "Build Exclude SQL", "n8n-nodes-base.code",
             [500, 0], {"jsCode": PERIOD_SCOPE_EXCLUDE_BUILD}),
        pg("scope-exclude-execute", "Execute Exclude", [750, 0], "changed"),
        node("scope-exclude-format", "Format Exclude Response", "n8n-nodes-base.code",
             [1000, 0], {"jsCode": PERIOD_SCOPE_EXCLUDE_FORMAT}),
        respond_node("scope-respond-exclude", "Respond EXCLUDE", [1240, 0]),
        # INCLUDE — the reverse action
        node("scope-webhook-include", "Webhook INCLUDE", "n8n-nodes-base.webhook",
             [-700, 300],
             {"httpMethod": "POST", "path": "api/admin/include-participant",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-scope-include"),
        node("scope-guard-input-include", "Prepare Guard Input INCLUDE",
             "n8n-nodes-base.code", [-480, 300], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("scope-run-guard-include", "Run Auth Guard INCLUDE",
                       [-250, 300], guard_workflow_id),
        node("scope-include-validate", "Validate Include", "n8n-nodes-base.code",
             [0, 300], {"jsCode": PERIOD_SCOPE_INCLUDE_VALIDATE}),
        pg("scope-include-check", "Load Include Target", [250, 300], "target_id"),
        node("scope-include-build", "Build Include SQL", "n8n-nodes-base.code",
             [500, 300], {"jsCode": PERIOD_SCOPE_INCLUDE_BUILD}),
        pg("scope-include-execute", "Execute Include", [750, 300], "changed"),
        node("scope-include-format", "Format Include Response", "n8n-nodes-base.code",
             [1000, 300], {"jsCode": PERIOD_SCOPE_INCLUDE_FORMAT}),
        respond_node("scope-respond-include", "Respond INCLUDE", [1240, 300]),
        # HISTORY — the record, readable after the period closes
        node("scope-webhook-history", "Webhook SCOPE HISTORY", "n8n-nodes-base.webhook",
             [-700, 600],
             {"httpMethod": "GET", "path": "api/admin/period-scope-events",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-scope-events"),
        node("scope-guard-input-history", "Prepare Guard Input SCOPE HISTORY",
             "n8n-nodes-base.code", [-480, 600], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("scope-run-guard-history", "Run Auth Guard SCOPE HISTORY",
                       [-250, 600], guard_workflow_id),
        node("scope-history-build", "Build Scope Events Query", "n8n-nodes-base.code",
             [0, 600], {"jsCode": PERIOD_SCOPE_HISTORY_BUILD}),
        pg("scope-history-load", "Load Scope Events", [250, 600], "id"),
        node("scope-history-format", "Format Scope Events Response", "n8n-nodes-base.code",
             [500, 600], {"jsCode": PERIOD_SCOPE_HISTORY_FORMAT}),
        respond_node("scope-respond-history", "Respond SCOPE HISTORY", [740, 600]),
        # One read surface over the three append-only event families. Historical
        # tables remain physically separate; no row is copied or rewritten.
        node("employee-events-webhook", "Webhook EMPLOYEE EVENTS",
             "n8n-nodes-base.webhook", [-700, 900],
             {"httpMethod": "GET", "path": "api/admin/employee-events",
              "responseMode": "responseNode", "options": {}},
             type_version=2.1, webhook_id="epe-employee-events"),
        node("employee-events-guard-input", "Prepare Guard Input EMPLOYEE EVENTS",
             "n8n-nodes-base.code", [-480, 900], {"jsCode": guard_input_js(["admin"])}),
        run_guard_node("employee-events-run-guard", "Run Auth Guard EMPLOYEE EVENTS",
                       [-250, 900], guard_workflow_id),
        node("employee-events-build", "Build Employee Events Query",
             "n8n-nodes-base.code", [0, 900], {"jsCode": EMPLOYEE_EVENTS_BUILD}),
        pg("employee-events-load", "Load Employee Events", [250, 900], "event_id"),
        node("employee-events-format", "Format Employee Events Response",
             "n8n-nodes-base.code", [500, 900], {"jsCode": EMPLOYEE_EVENTS_FORMAT}),
        respond_node("employee-events-respond", "Respond EMPLOYEE EVENTS", [740, 900]),
    ]
    connections = {
        "Webhook EXCLUDE": connect("Prepare Guard Input EXCLUDE"),
        "Prepare Guard Input EXCLUDE": connect("Run Auth Guard EXCLUDE"),
        "Run Auth Guard EXCLUDE": connect("Validate Exclude"),
        "Validate Exclude": connect("Load Exclude Target"),
        "Load Exclude Target": connect("Build Exclude SQL"),
        "Build Exclude SQL": connect("Execute Exclude"),
        "Execute Exclude": connect("Format Exclude Response"),
        "Format Exclude Response": connect("Respond EXCLUDE"),
        "Webhook INCLUDE": connect("Prepare Guard Input INCLUDE"),
        "Prepare Guard Input INCLUDE": connect("Run Auth Guard INCLUDE"),
        "Run Auth Guard INCLUDE": connect("Validate Include"),
        "Validate Include": connect("Load Include Target"),
        "Load Include Target": connect("Build Include SQL"),
        "Build Include SQL": connect("Execute Include"),
        "Execute Include": connect("Format Include Response"),
        "Format Include Response": connect("Respond INCLUDE"),
        "Webhook SCOPE HISTORY": connect("Prepare Guard Input SCOPE HISTORY"),
        "Prepare Guard Input SCOPE HISTORY": connect("Run Auth Guard SCOPE HISTORY"),
        "Run Auth Guard SCOPE HISTORY": connect("Build Scope Events Query"),
        "Build Scope Events Query": connect("Load Scope Events"),
        "Load Scope Events": connect("Format Scope Events Response"),
        "Format Scope Events Response": connect("Respond SCOPE HISTORY"),
        "Webhook EMPLOYEE EVENTS": connect("Prepare Guard Input EMPLOYEE EVENTS"),
        "Prepare Guard Input EMPLOYEE EVENTS": connect("Run Auth Guard EMPLOYEE EVENTS"),
        "Run Auth Guard EMPLOYEE EVENTS": connect("Build Employee Events Query"),
        "Build Employee Events Query": connect("Load Employee Events"),
        "Load Employee Events": connect("Format Employee Events Response"),
        "Format Employee Events Response": connect("Respond EMPLOYEE EVENTS"),
    }
    return workflow("API: Manage Period Scope", nodes_list, connections)




# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate route-guard EPE workflow payloads.",
    )
    parser.add_argument(
        "--postgres-credential-id",
        default=POSTGRES_CREDENTIAL_PLACEHOLDER,
        help="n8n Postgres credential ID (e.g. VNbfkY8IKbEzn88B)",
    )
    parser.add_argument(
        "--guard-workflow-id",
        default=GUARD_WORKFLOW_PLACEHOLDER,
        help="Workflow ID of EPE: Auth Guard (e.g. L0Zr7nVa8O5YWXd3)",
    )
    parser.add_argument(
        "--output-directory",
        required=True,
        type=Path,
        help="Directory to write generated JSON files",
    )
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)

    cred = args.postgres_credential_id
    guard = args.guard_workflow_id

    workflows: dict[str, Any] = {
        "criteria.json": build_criteria(cred, guard),
        "get-my-manager.json": build_get_my_manager(cred, guard),
        "my-profile.json": build_my_profile(cred, guard),
        "check-evaluated.json": build_check_evaluated(cred, guard),
        "check-self-review.json": build_check_self_review(cred, guard),
        "submit-evaluation.json": build_submit_evaluation(cred, guard),
        "update-evaluation.json": build_update_evaluation(cred, guard),
        "self-review-submit.json": build_self_review_submit(cred, guard),
        "evaluation-details.json": build_evaluation_details(cred, guard),
        "evaluation-history.json": build_evaluation_history(cred, guard),
        "hr-evaluation-status.json": build_hr_evaluation_status(cred, guard),
        "score-coefficients.json": build_score_coefficients(cred, guard),
        "save-score-coefficients.json": build_save_score_coefficients(cred, guard),
        "create-invite.json": build_create_invite(cred, guard),
        "admin-users-data.json": build_admin_users_data(cred, guard),
        "save-user.json": build_save_user(cred, guard),
        "manage-periods.json": build_manage_periods(cred, guard),
        "manage-employment.json": build_manage_employment(cred, guard),
        "manage-period-scope.json": build_manage_period_scope(cred, guard),
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
