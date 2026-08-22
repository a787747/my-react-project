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
               SELECT id FROM performance_db.evaluation_periods
               WHERE is_active = true AND status = 'active'
                 AND evaluation_started_at IS NOT NULL
             )
           LIMIT 1),
          false
        ) AS has_evaluated_manager,
        (SELECT e.calculated_score
         FROM performance_db.evaluations e
         JOIN performance_db.evaluation_periods ep
           ON ep.id = e.period_id AND ep.is_active = true AND ep.status = 'active'
              AND ep.evaluation_started_at IS NOT NULL
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
      SELECT
        e.id AS evaluation_id,
        e.calculated_score,
        e.weighted_score,
        e.updated_at,
        e.is_self_evaluation,
        e.evaluation_source,
        p.name AS period_name,
        p.start_date,
        p.end_date,
        u.full_name AS evaluator_name,
        u.job_title AS evaluator_title
      FROM performance_db.evaluations e
      LEFT JOIN performance_db.evaluation_periods p ON p.id = e.period_id
      LEFT JOIN performance_db.users u ON u.id = e.evaluator_id
      WHERE e.subject_id = ${actorId}
      ORDER BY e.updated_at DESC
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
const data = rows.filter(item => item.evaluation_id !== undefined);

if (!data.length) {
  return {
    json: {
      http_status: 200,
      body: {
        success: true,
        has_evaluations: false,
        evaluations: [],
        stats: { total_evaluations: 0, average_score: null, latest_score: null, latest_period: null, latest_date: null },
      },
    },
  };
}

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
      has_evaluations: true,
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
        actor.can_evaluate,
        EXISTS(
          SELECT 1 FROM performance_db.evaluations dup
          WHERE dup.subject_id = ${rawSubjectId}
            AND dup.evaluator_id = ${actorId}
            AND dup.evaluation_source = '${safeSource}'
            AND dup.period_id = p.id
            AND dup.is_self_evaluation = false
        ) AS is_duplicate
      FROM performance_db.evaluation_periods p
      JOIN performance_db.evaluation_period_participants ep_actor
        ON ep_actor.period_id = p.id AND ep_actor.user_id = ${actorId} AND ep_actor.is_in_scope = true
      JOIN performance_db.evaluation_period_participants ep_subj
        ON ep_subj.period_id = p.id AND ep_subj.user_id = ${rawSubjectId} AND ep_subj.is_in_scope = true
      JOIN performance_db.users subj ON subj.id = ${rawSubjectId}
      JOIN performance_db.users actor ON actor.id = ${actorId}
      WHERE p.is_active = true AND p.status = 'active'
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
if (validation.is_duplicate) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'DUPLICATE_EVALUATION',
        message: 'Такая оценка уже отправлена в текущем периоде',
      },
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
        (p.evaluation_started_at IS NOT NULL) AS period_started
      FROM performance_db.evaluations e
      JOIN performance_db.evaluation_periods p ON p.id = e.period_id
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
  DELETE FROM performance_db.evaluation_scores
  WHERE evaluation_id = ${evalId}
    AND criteria_id NOT IN (SELECT crit_id FROM score_rows)
    AND EXISTS (SELECT 1 FROM updated_header)
  RETURNING criteria_id
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
# ADMIN ONLY (D-0822-2). Until 2026-08-22 this route was authenticated-only and
# every employee read the whole weight + level-coefficient table while filling in
# a self-review. The weighted self-review value is now computed on the server.

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
             [-480, 0], {"jsCode": guard_input_js(["admin"])}),
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
  // The rule is "finite and > 0" (D-0822-2), not a floor: any positive weight is
  // a legitimate business value, and only 0 is the misread one.
  const weight = parseFloat(crit.weight);
  if (!Number.isFinite(weight) || weight <= 0) {
    return {
      json: {
        http_status: 422,
        body: {
          success: false,
          error: 'INVALID_WEIGHT',
          message: `Вес критерия ${criteriaId} должен быть конечным числом больше нуля. ` +
            `Чтобы критерий не влиял на бонус, отключите его (is_active), а не обнуляйте вес: ` +
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
      SELECT
        u.id, u.full_name, u.email, u.role, u.work_category, u.is_project_participant,
        u.job_title, u.manager_id, u.department_id, u.grade_id, u.has_subordinates,
        (u.password_hash IS NOT NULL) AS is_registered,
        d.name AS department_name,
        g.code AS grade_name,
        m.full_name AS manager_name,
        COALESCE(
          (SELECT CASE WHEN e.status = 'completed' THEN true ELSE false END
           FROM performance_db.evaluations e
           WHERE e.subject_id = u.id
             AND e.is_self_evaluation = true
             AND e.period_id = (
               SELECT id FROM performance_db.evaluation_periods
               WHERE is_active = true AND status = 'active' LIMIT 1
             )
           LIMIT 1),
          false
        ) AS self_review_done,
        (SELECT e.status
         FROM performance_db.evaluations e
         WHERE e.subject_id = u.id
           AND e.is_self_evaluation = false
           AND e.period_id = (
             SELECT id FROM performance_db.evaluation_periods
             WHERE is_active = true AND status = 'active' LIMIT 1
           )
         LIMIT 1
        ) AS manager_review_status
      FROM performance_db.users u
      LEFT JOIN performance_db.departments d ON d.id = u.department_id
      LEFT JOIN performance_db.grades g ON g.id = u.grade_id
      LEFT JOIN performance_db.users m ON m.id = u.manager_id
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
const grades = dedup(rawGrades);
const managers = users
  .filter(u => u.role !== 'employee')
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
             [-480, 0], {"jsCode": guard_input_js(["admin"])}),
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
const body = guard.request.body || guard.request;
// H1: only general and project allowed
const VALID_WORK_CATEGORIES = ['general', 'project'];
const VALID_ROLES = ['admin', 'c_level', 'manager', 'employee', 'hr'];

const workCategory = String(body.work_category || 'general').trim();
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
const role = String(body.role || 'employee').trim();
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

const cleanId = (v) => {
  if (v === '' || v == null || v === 'null') return null;
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : null;
};

const userId = cleanId(body.id);
const departmentId = cleanId(body.department_id);
const gradeId = cleanId(body.grade_id);
const managerId = cleanId(body.manager_id);
const isNew = userId === null;
const isProjectParticipant = workCategory === 'project';

const safeFullName = fullName.replace(/'/g, "''");
const safeEmail = email.replace(/'/g, "''");
const safeJobTitle = jobTitle.replace(/'/g, "''");

const departmentSql = departmentId !== null ? String(departmentId) : 'NULL';
const gradeSql = gradeId !== null ? String(gradeId) : 'NULL';
const managerSql = managerId !== null ? String(managerId) : 'NULL';
const jobTitleSql = safeJobTitle ? `'${safeJobTitle}'` : 'NULL';

// Classification is globally frozen once any evaluation exists in the active period.
// Only needed when updating an existing user (is_new=false).
const classCheckSql = userId !== null
  ? `SELECT u.work_category AS old_category,
       EXISTS(
         SELECT 1 FROM performance_db.evaluations e
         JOIN performance_db.evaluation_periods p
           ON p.id = e.period_id AND p.is_active = true AND p.status = 'active'
       ) AS period_has_any_evaluation
     FROM performance_db.users u WHERE u.id = ${userId} LIMIT 1`
  : `SELECT NULL::text AS old_category, false AS period_has_any_evaluation`;

return {
  json: {
    ok: true,
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
    sql: classCheckSql,
  },
};
""".strip()

SAVE_USER_BUILD_UPSERT = """
const prev = $('Validate User Data').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(() => true);

// Classification is globally frozen once any evaluation exists in the active period.
// Reject if: updating existing user AND category is changing AND active period has any evaluations.
if (!prev.is_new && check && check.old_category && check.old_category !== prev.work_category) {
  if (check.period_has_any_evaluation) {
    return {
      json: {
        http_status: 409,
        body: {
          success: false,
          error: 'CLASSIFICATION_FROZEN',
          message: 'Нельзя изменить категорию работы после первой отправленной оценки активного периода',
        },
      },
    };
  }
}

const userId = prev.user_id;
const isNew = prev.is_new;
const isProjectParticipant = prev.is_project_participant;

let sql;
if (isNew) {
  sql = `
INSERT INTO performance_db.users
  (full_name, email, role, job_title, work_category, is_project_participant,
   department_id, grade_id, manager_id, created_at)
VALUES
  ('${prev.full_name}', '${prev.email}', '${prev.role}', ${prev.job_title_sql},
   '${prev.work_category}', ${isProjectParticipant},
   ${prev.department_sql}, ${prev.grade_sql}, ${prev.manager_sql}, now())
RETURNING id, full_name, email, role, work_category, is_project_participant,
          job_title, manager_id, department_id, grade_id, has_subordinates
  `;
} else {
  sql = `
UPDATE performance_db.users
SET full_name = '${prev.full_name}',
    email = '${prev.email}',
    role = '${prev.role}',
    job_title = ${prev.job_title_sql},
    work_category = '${prev.work_category}',
    is_project_participant = ${isProjectParticipant},
    department_id = ${prev.department_sql},
    grade_id = ${prev.grade_sql},
    manager_id = ${prev.manager_sql}
WHERE id = ${userId}
RETURNING id, full_name, email, role, work_category, is_project_participant,
          job_title, manager_id, department_id, grade_id, has_subordinates
  `;
}

return { json: { ok: true, sql } };
""".strip()

SAVE_USER_FORMAT = """
const prev = $('Build User Upsert').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: { http_status: 500, body: { success: false, error: 'UPSERT_FAILED', message: 'Failed to save user' } },
  };
}
return {
  json: {
    http_status: 200,
    body: { success: true, user: row },
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
        node("saveuser-check", "Check Classification", "n8n-nodes-base.postgres",
             [60, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::text AS old_category, false AS has_active_evaluations' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
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
        "Validate User Data": connect("Check Classification"),
        "Check Classification": connect("Build User Upsert"),
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
    CASE
      WHEN u.join_date IS NOT NULL AND u.join_date > '${endDate}'::date THEN false
      ELSE true
    END,
    CASE
      WHEN u.join_date IS NOT NULL AND u.join_date > '${endDate}'::date THEN 'hired_after_period_end'
      ELSE NULL
    END
  FROM new_period np
  CROSS JOIN performance_db.users u
  ON CONFLICT (period_id, user_id) DO UPDATE
    SET is_in_scope = EXCLUDED.is_in_scope,
        exclusion_reason = EXCLUDED.exclusion_reason,
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
# same predicates, same latest-by-updated_at rule, same correction lookups —
# so the persisted final cell is the matrix cell by construction (D-0820-12).
PERIODS_CLOSE_DATASET_SQL = """
WITH criteria_data AS (
  SELECT c.id, c.weight, c.c_level_only,
    COALESCE(
      (SELECT json_object_agg(sc.score_level, sc.coefficient)
       FROM performance_db.score_coefficients sc WHERE sc.criteria_id = c.id),
      '{}'::json
    ) AS score_coefficients
  FROM performance_db.criteria c
  WHERE c.is_active = true
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
      'c_level_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = epp.user_id
          AND e.evaluation_source = 'c_level_direct'
          AND cd.c_level_only = true
          AND es.criteria_id = cd.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
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
   FROM criteria_data cd) AS criteria
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

// matrixUtils.getCriterionFinalScore — the matrix final cell (D-0820-12)
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
