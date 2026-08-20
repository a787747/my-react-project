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
const criteria = $input.all().map(item => item.json).filter(item => item.id !== undefined);
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
#   has_subordinates, department_name, grade_code, grade_coefficient,
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
             )
           LIMIT 1),
          false
        ) AS has_evaluated_manager,
        (SELECT e.calculated_score
         FROM performance_db.evaluations e
         JOIN performance_db.evaluation_periods ep
           ON ep.id = e.period_id AND ep.is_active = true AND ep.status = 'active'
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
        grade_coefficient: m.grade_coefficient,
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
# Actor is subject. For evaluation_source='subordinate', redact evaluator id/name/title.

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

// Per D3: redact evaluator identity for subordinate-source evaluations (actor is subject)
const evaluations = data.map(row => ({
  evaluation_id: row.evaluation_id,
  calculated_score: row.calculated_score,
  weighted_score: row.weighted_score,
  updated_at: row.updated_at,
  is_self_evaluation: row.is_self_evaluation,
  evaluation_source: row.evaluation_source,
  period_name: row.period_name,
  start_date: row.start_date,
  end_date: row.end_date,
  evaluator_name: row.evaluation_source === 'subordinate' ? null : row.evaluator_name,
  evaluator_title: row.evaluation_source === 'subordinate' ? null : row.evaluator_title,
}));

const scores = evaluations
  .map(e => e.calculated_score)
  .filter(s => s !== null && s !== undefined);
const total = evaluations.length;
const avg = scores.length ? parseFloat((scores.reduce((a, b) => a + Number(b), 0) / scores.length).toFixed(2)) : null;
const latest = evaluations[0];

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
        latest_score: latest?.calculated_score ?? null,
        latest_period: latest?.period_name ?? null,
        latest_date: latest?.updated_at ?? null,
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
# Actor self; missing user_id param never errors.

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
// Actor is always the subject; body/query user_id is ignored for auth.
const actorId = Number(guard.identity.id);
return {
  json: {
    ok: true,
    sql: `
      SELECT
        e.id,
        e.calculated_score,
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
      JOIN performance_db.evaluation_periods p
        ON p.id = e.period_id AND p.is_active = true AND p.status = 'active'
      LEFT JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
      WHERE e.subject_id = ${actorId}
        AND e.is_self_evaluation = true
      GROUP BY e.id, e.calculated_score, e.updated_at
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
      body: { success: false, error: 'INVALID_SOURCE', message: 'evaluation_source must be manager, subordinate, or c_level_direct' },
    },
  };
}
if (source === 'c_level_direct' && actorRole !== 'c_level' && actorRole !== 'admin') {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'ROLE_FORBIDDEN', message: 'c_level_direct requires c_level or admin role' },
    },
  };
}

const rawSubjectId = parseInt(body.subject_id, 10);
if (!Number.isFinite(rawSubjectId) || rawSubjectId < 1) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_SUBJECT', message: 'subject_id must be a positive integer' },
    },
  };
}
if (rawSubjectId === actorId) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'SELF_EVALUATION_FORBIDDEN', message: 'Use /api/self-review-submit for self-evaluations' },
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
        message: 'Subject or actor is not in scope in an active period, or relationship constraint is not satisfied',
      },
    },
  };
}
if (!validation.can_evaluate) {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'CANNOT_EVALUATE', message: 'Actor does not have the can_evaluate capability' },
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
        message: 'Evaluation already exists for this evaluator/subject/source/period tuple. Use /api/update-evaluation.',
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
      body: { success: false, error: 'NO_GRADES', message: 'grades must contain at least one entry' },
    },
  };
}
for (const [cId, sv] of gradeEntries) {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Invalid criteria_id: ${cId}` } } };
  }
  if (!Number.isFinite(scoreValue) || scoreValue < 1 || scoreValue > 10) {
    return { json: { http_status: 422, body: { success: false, error: 'GRADE_OUT_OF_RANGE', message: `Score for criteria ${cId} must be an integer between 1 and 10` } } };
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
      body: { success: false, error: 'DUPLICATE_EVALUATION', message: 'Evaluation already exists (concurrent submission).' },
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
      body: { success: false, error: 'INVALID_EVALUATION_ID', message: 'evaluation_id must be a positive integer' },
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
        p.status AS period_status
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
      body: { success: false, error: 'NOT_FOUND', message: 'Evaluation not found or does not belong to you' },
    },
  };
}
if (check.period_status === 'closed') {
  return {
    json: {
      http_status: 403,
      body: { success: false, error: 'PERIOD_CLOSED', message: 'Cannot modify evaluation: the evaluation period is closed' },
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
      body: { success: false, error: 'NO_GRADES', message: 'grades must contain at least one entry' },
    },
  };
}
for (const [cId, sv] of gradeEntries) {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Invalid criteria_id: ${cId}` } } };
  }
  if (!Number.isFinite(scoreValue) || scoreValue < 1 || scoreValue > 10) {
    return { json: { http_status: 422, body: { success: false, error: 'GRADE_OUT_OF_RANGE', message: `Score for criteria ${cId} must be an integer between 1 and 10` } } };
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
// Reassert evaluator ownership and non-closed period inline in the UPDATE WHERE clause
// to close the validation/mutation race between the prior SELECT check and this DML.
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
    AND (SELECT status FROM performance_db.evaluation_periods WHERE id = period_id) != 'closed'
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
  // CTE WHERE reassertion failed: evaluation not owned by actor or period became closed in the race window.
  return {
    json: {
      http_status: 403,
      body: { status: 'error', message: 'Update not permitted: evaluation does not belong to you or the period is now closed' },
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
      body: { success: false, error: 'INVALID_SCORE', message: 'final_score must be a valid number' },
    },
  };
}
if (finalScoreNum < 1 || finalScoreNum > 10) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'SCORE_OUT_OF_RANGE', message: 'final_score must be between 1 and 10 inclusive' },
    },
  };
}
// weighted_score may exceed 10 by design (accumulates grade coefficients), but must be finite and non-negative if supplied.
let weightedScore = finalScoreNum;
if (body.weighted_score !== undefined && body.weighted_score !== null && body.weighted_score !== '') {
  const ws = Number(body.weighted_score);
  if (!Number.isFinite(ws) || ws < 0) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_WEIGHTED_SCORE', message: 'weighted_score must be a finite non-negative number' },
      },
    };
  }
  weightedScore = ws;
}

return {
  json: {
    ok: true,
    actor_id: actorId,
    final_score: Number(finalScore),
    weighted_score: weightedScore,
    sql: `
      SELECT
        p.id AS period_id,
        EXISTS(
          SELECT 1 FROM performance_db.evaluations dup
          WHERE dup.subject_id = ${actorId}
            AND dup.evaluator_id = ${actorId}
            AND dup.period_id = p.id
            AND dup.is_self_evaluation = true
        ) AS is_duplicate
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
      body: { success: false, error: 'NOT_IN_SCOPE', message: 'No active period or actor is not in scope' },
    },
  };
}
if (check.is_duplicate) {
  return {
    json: {
      http_status: 409,
      body: { success: false, error: 'DUPLICATE_SELF_REVIEW', message: 'Self-review already exists for this period' },
    },
  };
}

const guard = $('Run Auth Guard').first().json;
const body = guard.request.body || guard.request;
const actorId = Number(prev.actor_id);
const periodId = Number(check.period_id);
const finalScore = Number(prev.final_score);
const weightedScore = Number(prev.weighted_score);
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
      body: { success: false, error: 'NO_GRADES', message: 'grades must contain at least one entry' },
    },
  };
}
for (const [cId, sv] of gradeEntries) {
  const criteriaId = parseInt(cId, 10);
  const scoreValue = parseInt(sv, 10);
  if (!Number.isFinite(criteriaId) || criteriaId < 1) {
    return { json: { http_status: 422, body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Invalid criteria_id: ${cId}` } } };
  }
  if (!Number.isFinite(scoreValue) || scoreValue < 1 || scoreValue > 10) {
    return { json: { http_status: 422, body: { success: false, error: 'GRADE_OUT_OF_RANGE', message: `Score for criteria ${cId} must be an integer between 1 and 10` } } };
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
      body: { success: false, error: 'DUPLICATE_SELF_REVIEW', message: 'Self-review already exists (concurrent submission).' },
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
# private_comment null for subject viewers; evaluator identity null for subject on subordinate source.

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
      body: { status: 'error', message: 'evaluation_id is required and must be a positive integer' },
    },
  };
}
const privileged = ['admin', 'hr', 'c_level'].includes(actorRole);
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
          OR e.subject_id = ${actorId}
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
    json: { http_status: 404, body: { status: 'error', message: 'Evaluation not found' } },
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
             [-480, 0], {"jsCode": guard_input_js([])}),
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
# Admin only. Freeze when is_active=true OR status='active'.

SAVE_COEFF_VALIDATE = """
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: { success: false, error: guard.code, message: guard.message },
    },
  };
}
// Reject if any active period exists (is_active=true OR status='active')
return {
  json: {
    ok: true,
    sql: `
      SELECT id, name, status
      FROM performance_db.evaluation_periods
      WHERE is_active = true OR status = 'active'
      LIMIT 1
    `,
  },
};
""".strip()

SAVE_COEFF_BUILD = """
const prev = $('Validate No Active Period').first().json;
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
        message: `Cannot modify score coefficients while period "${activePeriod.name}" is active`,
      },
    },
  };
}
const guard = $('Run Auth Guard').first().json;
const body = guard.request.body || guard.request;
const criteria = body.criteria;
if (!Array.isArray(criteria) || !criteria.length) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_BODY', message: 'criteria must be a non-empty array' },
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
        body: { success: false, error: 'INVALID_CRITERIA_ID', message: `Invalid criteria id: ${crit.id}` },
      },
    };
  }
  const weight = parseFloat(crit.weight);
  if (!Number.isFinite(weight) || weight < 0) {
    return {
      json: {
        http_status: 422,
        body: { success: false, error: 'INVALID_WEIGHT', message: `Invalid weight for criteria ${criteriaId}` },
      },
    };
  }
  sqls.push(`UPDATE performance_db.criteria SET weight = ${weight} WHERE id = ${criteriaId};`);
  const coeffMap = crit.score_coefficients || {};
  for (let level = 1; level <= 10; level++) {
    const coef = coeffMap[level] !== undefined ? parseFloat(coeffMap[level]) : 1.0;
    if (!Number.isFinite(coef) || coef < 0) {
      return {
        json: {
          http_status: 422,
          body: {
            success: false,
            error: 'INVALID_COEFFICIENT',
            message: `Invalid coefficient at level ${level} for criteria ${criteriaId}`,
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
        node("savecoeff-validate", "Validate No Active Period", "n8n-nodes-base.code",
             [-200, 0], {"jsCode": SAVE_COEFF_VALIDATE}),
        node("savecoeff-check", "Check Active Period", "n8n-nodes-base.postgres",
             [60, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
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
        "Run Auth Guard": connect("Validate No Active Period"),
        "Validate No Active Period": connect("Check Active Period"),
        "Check Active Period": connect("Build Coefficients Update"),
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
        message: `work_category must be one of: ${VALID_WORK_CATEGORIES.join(', ')} (H1 restriction)`,
      },
    },
  };
}
const role = String(body.role || 'employee').trim();
if (!VALID_ROLES.includes(role)) {
  return {
    json: {
      http_status: 422,
      body: { success: false, error: 'INVALID_ROLE', message: `role must be one of: ${VALID_ROLES.join(', ')}` },
    },
  };
}
const fullName = String(body.full_name || '').trim();
const email = String(body.email || '').trim().toLowerCase();
const jobTitle = String(body.job_title || '').trim();

if (!fullName || fullName.length > 150) {
  return {
    json: { http_status: 422, body: { success: false, error: 'INVALID_NAME', message: 'full_name is required (max 150 chars)' } },
  };
}
if (!email || email.length > 150) {
  return {
    json: { http_status: 422, body: { success: false, error: 'INVALID_EMAIL', message: 'email is required (max 150 chars)' } },
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
          message: 'Cannot change work_category: classification is frozen for the active period once any evaluation has been submitted',
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


# ── 17. Manage Periods — GET api/periods, POST api/periods/create, POST …/activate
# GET response: {status:'success', data:[...]}
# Create: atomic CTE period+participants; always draft/inactive; half_year or annual only.
# Activate: reject if switching away from active period with evaluations (409);
#   set both status/is_active; reject closed target.

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
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = evaluation_periods.id) AS participant_count,
        (SELECT COUNT(*)::integer FROM performance_db.evaluation_period_participants epp
          WHERE epp.period_id = evaluation_periods.id AND epp.is_in_scope = true) AS in_scope_count
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
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_NAME', message: 'name is required (max 100 chars)' } } };
}
if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(startDate)) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_DATE', message: 'start_date must be YYYY-MM-DD' } } };
}
if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(endDate)) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_DATE', message: 'end_date must be YYYY-MM-DD' } } };
}
if (endDate <= startDate) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_DATE_RANGE', message: 'end_date must be after start_date' } } };
}
if (!VALID_TYPES.includes(rawType)) {
  return { json: { http_status: 422, body: { success: false, error: 'INVALID_TYPE', message: `period_type must be half_year or annual` } } };
}

const safeName = name.replace(/'/g, "''");
// Always start as draft and inactive; ignore client-supplied status
return {
  json: {
    ok: true,
    end_date: endDate,
    sql: `
WITH new_period AS (
  INSERT INTO performance_db.evaluation_periods
    (name, start_date, end_date, is_active, period_type, status)
  VALUES ('${safeName}', '${startDate}', '${endDate}', false, '${rawType}', 'draft')
  RETURNING id, name, start_date, end_date, is_active, period_type, status
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
       count(p.user_id)::integer AS participants_added
FROM new_period np
LEFT JOIN participants p ON true
GROUP BY np.id, np.name, np.start_date, np.end_date, np.is_active, np.period_type, np.status
    `,
  },
};
""".strip()

PERIODS_CREATE_FORMAT = """
const prev = $('Validate Period Create').first().json;
if (prev.http_status) {
  return { json: prev };
}
const row = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (!row) {
  return {
    json: { http_status: 500, body: { status: 'error', message: 'Period creation failed' } },
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
      body: { success: false, error: 'INVALID_PERIOD_ID', message: 'period_id must be a positive integer' },
    },
  };
}
// Check: is there a currently-active period that has evaluations (would block the switch)?
return {
  json: {
    ok: true,
    target_period_id: periodId,
    sql: `
      SELECT
        p.id AS current_active_id,
        p.name AS current_active_name,
        EXISTS(
          SELECT 1 FROM performance_db.evaluations WHERE period_id = p.id LIMIT 1
        ) AS has_evaluations
      FROM performance_db.evaluation_periods p
      WHERE (p.is_active = true OR p.status = 'active')
        AND p.id != ${periodId}
      LIMIT 1
    `,
  },
};
""".strip()

PERIODS_ACTIVATE_EXECUTE = """
const prev = $('Validate Period Activate').first().json;
if (prev.http_status) {
  return { json: prev };
}
const check = $input.all().map(item => item.json).find(item => item.current_active_id !== undefined);
// Reject if switching away from an active period that already has evaluations
if (check && check.has_evaluations) {
  return {
    json: {
      http_status: 409,
      body: {
        success: false,
        error: 'ACTIVE_PERIOD_HAS_EVALUATIONS',
        message: `Cannot deactivate period "${check.current_active_name}": it already has evaluations`,
      },
    },
  };
}
const periodId = Number(prev.target_period_id);
return {
  json: {
    ok: true,
    sql: `
WITH deactivated AS (
  UPDATE performance_db.evaluation_periods
  SET is_active = false, status = 'draft'
  WHERE (is_active = true OR status = 'active') AND id != ${periodId}
  RETURNING id
),
activated AS (
  UPDATE performance_db.evaluation_periods
  SET is_active = true, status = 'active'
  WHERE id = ${periodId}
    AND status != 'closed'
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
      body: { status: 'error', message: 'Period not found or is already closed' },
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
        node("periods-create-execute", "Execute Period Create", "n8n-nodes-base.postgres",
             [250, 0],
             {"operation": "executeQuery",
              "query": "={{ $json.ok ? $json.sql : 'SELECT NULL::integer AS id WHERE false' }}",
              "options": {}},
             type_version=2.6,
             credentials=postgres_credentials(credential_id), always_output=True),
        node("periods-create-format", "Format Create Response", "n8n-nodes-base.code",
             [500, 0], {"jsCode": PERIODS_CREATE_FORMAT}),
        respond_node("periods-respond-create", "Respond CREATE", [740, 0]),
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
        "Validate Period Create": connect("Execute Period Create"),
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
