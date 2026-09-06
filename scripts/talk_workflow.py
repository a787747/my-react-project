"""Generated n8n workflow for TALK — management listening channel."""
from __future__ import annotations

import json
from typing import Any

WAVE_KEY = "talk-2026-wave-1"

ANSWER_LABELS = {
    "all_good": "У меня всё в порядке, срочных тем для обсуждения нет",
    "topic_only": "Есть тема, но отдельная встреча сейчас не нужна",
    "conversation": "Да, мне нужен разговор",
}
URGENCY_LABELS = {
    "this_cycle": "Хочу обсудить в рамках этого цикла",
    "soon": "Желательно поговорить в ближайшее время — ситуация уже влияет на мою работу",
}
GROUP_LABELS = {"yes": "Да", "individual_only": "Только индивидуально"}


def _node(node_id: str, name: str, kind: str, position: list[int],
          parameters: dict[str, Any], **extra: Any) -> dict[str, Any]:
    value = {
        "parameters": parameters, "id": node_id, "name": name, "type": kind,
        "typeVersion": extra.pop("type_version", 2), "position": position,
    }
    value.update(extra)
    return value


def _guard_input(roles: list[str]) -> str:
    return (
        "const request = $input.first().json;\n"
        "return { json: {\n"
        "  authorization: request.headers?.authorization || '',\n"
        f"  required_roles: {json.dumps(roles)},\n"
        "  required_capability: '',\n"
        "  request,\n"
        "}};"
    )


def _run_guard(node_id: str, name: str, position: list[int], guard_id: str) -> dict[str, Any]:
    return _node(node_id, name, "n8n-nodes-base.executeWorkflow", position,
                 {"workflowId": guard_id, "options": {}}, type_version=1)


def _respond(node_id: str, name: str, position: list[int]) -> dict[str, Any]:
    return _node(
        node_id, name, "n8n-nodes-base.respondToWebhook", position,
        {"respondWith": "json", "responseBody": "={{ $json.body }}",
         "options": {"responseCode": "={{ $json.http_status }}"}},
        type_version=1.4,
    )


def _connect(name: str) -> dict[str, Any]:
    return {"main": [[{"node": name, "type": "main", "index": 0}]]}


FORM_BUILD = r"""
const guard = $('Run Auth Guard FORM').first().json;
if (!guard.ok) return { json: { http_status: guard.status,
  body: { success: false, error: guard.code, message: guard.message },
  sql: 'SELECT NULL::integer AS actor_id WHERE false' } };
const actorId = Number(guard.identity.id);
return { json: { sql: `
WITH wave AS (
  SELECT w.id, w.wave_key, w.opens_at, w.closes_at,
         clock_timestamp() BETWEEN w.opens_at AND w.closes_at AS is_open,
         to_char(w.opens_at AT TIME ZONE 'Asia/Ashgabat', 'YYYY-MM-DD"T"HH24:MI:SS') AS opens_local,
         to_char(w.closes_at AT TIME ZONE 'Asia/Ashgabat', 'YYYY-MM-DD"T"HH24:MI:SS') AS closes_local,
         extract(day FROM w.closes_at AT TIME ZONE 'Asia/Ashgabat')::integer::text ||
           CASE extract(month FROM w.closes_at AT TIME ZONE 'Asia/Ashgabat')::integer
             WHEN 1 THEN ' января' WHEN 2 THEN ' февраля' WHEN 3 THEN ' марта'
             WHEN 4 THEN ' апреля' WHEN 5 THEN ' мая' WHEN 6 THEN ' июня'
             WHEN 7 THEN ' июля' WHEN 8 THEN ' августа' WHEN 9 THEN ' сентября'
             WHEN 10 THEN ' октября' WHEN 11 THEN ' ноября' WHEN 12 THEN ' декабря'
           END AS deadline_text
  FROM (SELECT * FROM performance_db.management_talk_waves ORDER BY id DESC LIMIT 1) w
), actor AS (
  SELECT u.id, u.manager_id, (u.terminated_at IS NOT NULL) AS is_terminated
  FROM performance_db.users u WHERE u.id = ${actorId}
), mine AS (
  SELECT r.answer_key, r.topic_key, r.counterpart_mode, r.urgency_key,
         r.group_readiness_key,
         to_char(r.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at,
         COALESCE(json_agg(c.counterpart_id ORDER BY c.counterpart_id)
           FILTER (WHERE c.counterpart_id IS NOT NULL), '[]'::json) AS counterpart_ids
  FROM wave w
  JOIN performance_db.management_talk_responses r ON r.wave_id = w.id
  LEFT JOIN performance_db.management_talk_counterparts c
    ON c.wave_id = r.wave_id AND c.responder_id = r.responder_id
  WHERE r.responder_id = ${actorId}
  GROUP BY r.answer_key, r.topic_key, r.counterpart_mode, r.urgency_key,
           r.group_readiness_key, r.updated_at
)
SELECT a.id AS actor_id, a.manager_id, a.is_terminated,
  w.id AS wave_id, w.wave_key, w.is_open, w.opens_local, w.closes_local, w.deadline_text,
  COALESCE((SELECT json_agg(json_build_object(
    'key', t.topic_key, 'label', t.label,
    'sensitive', t.topic_key IN ('t09_team','t10_manager','t11_unfair','t12_personal')
  ) ORDER BY t.topic_key) FROM performance_db.management_talk_topics t), '[]'::json) AS topics,
  COALESCE((SELECT json_agg(json_build_object(
    'id', u.id, 'full_name', u.full_name,
    'is_own_manager', u.id = a.manager_id
  ) ORDER BY CASE u.role WHEN 'admin' THEN 0 ELSE 1 END, u.full_name, u.id)
  FROM performance_db.users u
  WHERE u.terminated_at IS NULL AND u.role IN ('admin','c_level')
    AND u.id IN (2,18,21,40,47,61)), '[]'::json) AS leadership,
  (SELECT row_to_json(m) FROM mine m) AS my_response
FROM actor a CROSS JOIN wave w
` } };
""".strip()

FORM_FORMAT = r"""
const prev = $('Build Form Query').first().json;
if (prev.http_status) return { json: prev };
const row = $input.all().map(i => i.json).find(r => r.actor_id !== undefined);
if (!row) return { json: { http_status: 404,
  body: { success: false, error: 'TALK_WAVE_OR_ACTOR_NOT_FOUND', message: 'Окно ответа недоступно' } } };
const truthy = v => v === true || v === 't';
if (truthy(row.is_terminated)) return { json: { http_status: 403,
  body: { success: false, error: 'ACTOR_TERMINATED', message: 'Учётная запись неактивна' } } };
const parse = (v, fallback) => {
  if (v === null || v === undefined) return fallback;
  if (typeof v !== 'string') return v;
  try { return JSON.parse(v); } catch { return fallback; }
};
const mine = parse(row.my_response, null);
return { json: { http_status: 200, body: {
  success: true,
  wave: {
    id: Number(row.wave_id), key: row.wave_key, is_open: truthy(row.is_open),
    opens_at: row.opens_local ? `${row.opens_local}+05:00` : null,
    closes_at: row.closes_local ? `${row.closes_local}+05:00` : null,
    deadline_text: row.deadline_text,
  },
  topics: parse(row.topics, []),
  counterparts: parse(row.leadership, []),
  my_response: mine ? {
    answer_key: mine.answer_key, topic_key: mine.topic_key,
    counterpart_mode: mine.counterpart_mode,
    counterpart_ids: parse(mine.counterpart_ids, []).map(Number),
    urgency_key: mine.urgency_key,
    group_readiness_key: mine.group_readiness_key,
    updated_at: mine.updated_at,
  } : null,
} } };
""".strip()

SAVE_VALIDATE = r"""
const guard = $('Run Auth Guard SAVE').first().json;
if (!guard.ok) return { json: { http_status: guard.status,
  body: { success: false, error: guard.code, message: guard.message },
  sql: 'SELECT NULL::integer AS actor_id WHERE false' } };
const actorId = Number(guard.identity.id);
const body = guard.request.body || guard.request || {};
const answerKey = String(body.answer_key || '');
const topicKey = body.topic_key == null ? null : String(body.topic_key);
const mode = String(body.counterpart_mode || 'none');
const urgencyKey = body.urgency_key == null ? null : String(body.urgency_key);
const groupKey = body.group_readiness_key == null ? null : String(body.group_readiness_key);
const rawIds = Array.isArray(body.counterpart_ids) ? body.counterpart_ids : [];
const counterpartIds = [...new Set(rawIds.map(v => parseInt(v, 10)))];
const shapeOk =
  (answerKey === 'all_good' && topicKey === null && mode === 'none'
    && urgencyKey === null && groupKey === null && counterpartIds.length === 0)
  || (answerKey === 'topic_only' && /^t(0[1-9]|1[0-2])_[a-z_]+$/.test(topicKey || '')
    && mode === 'none' && urgencyKey === null && groupKey === null && counterpartIds.length === 0)
  || (answerKey === 'conversation' && /^t(0[1-9]|1[0-2])_[a-z_]+$/.test(topicKey || '')
    && ['people','help_choose','all_leadership'].includes(mode)
    && ['this_cycle','soon'].includes(urgencyKey)
    && ['yes','individual_only'].includes(groupKey)
    && ((mode === 'people' && counterpartIds.length > 0)
      || (mode !== 'people' && counterpartIds.length === 0)));
if (!shapeOk || counterpartIds.some(v => !Number.isFinite(v) || v < 1)) {
  return { json: { http_status: 422,
    body: { success: false, error: 'TALK_INVALID_RESPONSE', message: 'Проверьте выбранные варианты ответа' },
    sql: 'SELECT NULL::integer AS actor_id WHERE false' } };
}
return { json: {
  actor_id: actorId, answer_key: answerKey, topic_key: topicKey,
  counterpart_mode: mode, counterpart_ids: counterpartIds,
  urgency_key: urgencyKey, group_readiness_key: groupKey,
  sql: `
WITH wave AS (
  SELECT w.id, clock_timestamp() BETWEEN w.opens_at AND w.closes_at AS is_open
  FROM (SELECT * FROM performance_db.management_talk_waves ORDER BY id DESC LIMIT 1) w
), actor AS (
  SELECT u.id, u.manager_id, (u.terminated_at IS NOT NULL) AS is_terminated
  FROM performance_db.users u WHERE u.id = ${actorId}
), requested(counterpart_id) AS (
  SELECT unnest(ARRAY[${counterpartIds.join(',') || 'NULL'}]::integer[])
), eligible AS (
  SELECT u.id FROM performance_db.users u
  WHERE u.terminated_at IS NULL AND u.role IN ('admin','c_level')
    AND u.id IN (2,18,21,40,47,61)
)
SELECT a.id AS actor_id, a.manager_id, a.is_terminated, w.id AS wave_id, w.is_open,
  ${topicKey === null ? 'true' : `EXISTS (
    SELECT 1 FROM performance_db.management_talk_topics t WHERE t.topic_key = '${topicKey}'
  )`} AS topic_exists,
  (SELECT count(*)::integer FROM requested WHERE counterpart_id IS NOT NULL) AS requested_count,
  (SELECT count(*)::integer FROM requested r JOIN eligible e ON e.id = r.counterpart_id) AS eligible_count,
  (SELECT count(*)::integer FROM requested r WHERE r.counterpart_id = a.manager_id) AS own_manager_count
FROM actor a CROSS JOIN wave w
` } };
""".strip()

SAVE_BUILD = r"""
const prev = $('Validate Save').first().json;
if (prev.http_status) return { json: prev };
const check = $input.all().map(i => i.json).find(r => r.actor_id !== undefined);
const truthy = v => v === true || v === 't';
if (!check) return { json: { http_status: 404,
  body: { success: false, error: 'TALK_WAVE_OR_ACTOR_NOT_FOUND', message: 'Окно ответа недоступно' } } };
if (truthy(check.is_terminated)) return { json: { http_status: 403,
  body: { success: false, error: 'ACTOR_TERMINATED', message: 'Учётная запись неактивна' } } };
if (!truthy(check.is_open)) return { json: { http_status: 409,
  body: { success: false, error: 'TALK_WAVE_CLOSED', message: 'Срок ответа завершён' } } };
if (!truthy(check.topic_exists)) return { json: { http_status: 422,
  body: { success: false, error: 'TALK_TOPIC_INVALID', message: 'Выберите тему из списка' } } };
if (prev.counterpart_mode === 'people'
    && Number(check.requested_count) !== Number(check.eligible_count)) {
  return { json: { http_status: 422,
    body: { success: false, error: 'TALK_COUNTERPART_INVALID', message: 'Выберите собеседника из списка' } } };
}
// Topic 10 only: topics 9, 11 and 12 deliberately may concern anyone.
if (prev.topic_key === 't10_manager' && prev.counterpart_mode === 'people'
    && Number(check.own_manager_count) > 0) {
  return { json: { http_status: 422,
    body: { success: false, error: 'TALK_OWN_MANAGER_FORBIDDEN',
            message: 'Для этой темы выберите другого собеседника' } } };
}
const ids = prev.counterpart_ids.join(',') || 'NULL';
const lit = v => v === null ? 'NULL' : `'${String(v).replace(/'/g, "''")}'`;
const actorId = Number(prev.actor_id);
return { json: { sql: `
WITH wave AS (
  SELECT w.id
  FROM (SELECT * FROM performance_db.management_talk_waves ORDER BY id DESC LIMIT 1) w
  WHERE clock_timestamp() BETWEEN w.opens_at AND w.closes_at
), actor AS (
  SELECT u.id, u.manager_id FROM performance_db.users u
  WHERE u.id = ${actorId} AND u.terminated_at IS NULL
), requested(counterpart_id) AS (
  SELECT unnest(ARRAY[${ids}]::integer[])
), eligible AS (
  SELECT u.id FROM performance_db.users u
  WHERE u.terminated_at IS NULL AND u.role IN ('admin','c_level')
    AND u.id IN (2,18,21,40,47,61)
), valid AS (
  SELECT w.id AS wave_id, a.id AS responder_id, a.manager_id
  FROM wave w CROSS JOIN actor a
  WHERE ${prev.topic_key === null ? 'true' : `EXISTS (
      SELECT 1 FROM performance_db.management_talk_topics t
      WHERE t.topic_key = ${lit(prev.topic_key)}
    )`}
    AND (${lit(prev.counterpart_mode)} <> 'people' OR (
      (SELECT count(*) FROM requested WHERE counterpart_id IS NOT NULL) > 0
      AND (SELECT count(*) FROM requested WHERE counterpart_id IS NOT NULL)
        = (SELECT count(*) FROM requested r JOIN eligible e ON e.id = r.counterpart_id)
      AND (${lit(prev.topic_key)} <> 't10_manager'
        OR NOT EXISTS (SELECT 1 FROM requested r WHERE r.counterpart_id = a.manager_id))
    ))
), cleared AS (
  DELETE FROM performance_db.management_talk_counterparts c USING valid v
  WHERE c.wave_id = v.wave_id AND c.responder_id = v.responder_id
  RETURNING c.counterpart_id
), saved AS (
  INSERT INTO performance_db.management_talk_responses
    (wave_id, responder_id, answer_key, topic_key, counterpart_mode,
     urgency_key, group_readiness_key)
  SELECT v.wave_id, v.responder_id, ${lit(prev.answer_key)}, ${lit(prev.topic_key)},
         ${lit(prev.counterpart_mode)}, ${lit(prev.urgency_key)}, ${lit(prev.group_readiness_key)}
  FROM valid v LEFT JOIN (SELECT count(*) FROM cleared) force_order ON true
  ON CONFLICT (wave_id, responder_id) DO UPDATE SET
    answer_key = EXCLUDED.answer_key, topic_key = EXCLUDED.topic_key,
    counterpart_mode = EXCLUDED.counterpart_mode, urgency_key = EXCLUDED.urgency_key,
    group_readiness_key = EXCLUDED.group_readiness_key, updated_at = now()
  RETURNING wave_id, responder_id
), named AS (
  INSERT INTO performance_db.management_talk_counterparts
    (wave_id, responder_id, counterpart_id)
  SELECT s.wave_id, s.responder_id, e.id
  FROM saved s JOIN valid v USING (wave_id, responder_id)
  JOIN eligible e ON (
    (${lit(prev.counterpart_mode)} = 'people'
      AND e.id IN (SELECT counterpart_id FROM requested WHERE counterpart_id IS NOT NULL))
    OR ${lit(prev.counterpart_mode)} = 'all_leadership'
  )
  WHERE ${lit(prev.topic_key)} <> 't10_manager' OR e.id <> v.manager_id
  ON CONFLICT DO NOTHING RETURNING counterpart_id
)
SELECT (SELECT count(*)::integer FROM saved) AS written,
       (SELECT count(*)::integer FROM named) AS counterpart_rows
` } };
""".strip()

SAVE_FORMAT = r"""
const prev = $('Build Save SQL').first().json;
if (prev.http_status) return { json: prev };
const row = $input.all().map(i => i.json).find(r => r.written !== undefined);
if (!row || Number(row.written) !== 1) return { json: { http_status: 409,
  body: { success: false, error: 'TALK_WRITE_CONFLICT', message: 'Состояние изменилось — обновите страницу' } } };
return { json: { http_status: 200,
  body: { success: true, message: 'Ответ получен' } } };
""".strip()

WITHDRAW_BUILD = r"""
const guard = $('Run Auth Guard WITHDRAW').first().json;
if (!guard.ok) return { json: { http_status: guard.status,
  body: { success: false, error: guard.code, message: guard.message },
  sql: 'SELECT NULL::integer AS written WHERE false' } };
const actorId = Number(guard.identity.id);
return { json: { sql: `
WITH wave AS (
  SELECT w.id
  FROM (SELECT * FROM performance_db.management_talk_waves ORDER BY id DESC LIMIT 1) w
  WHERE clock_timestamp() BETWEEN w.opens_at AND w.closes_at
), actor AS (
  SELECT u.id FROM performance_db.users u
  WHERE u.id = ${actorId} AND u.terminated_at IS NULL
), deleted AS (
  DELETE FROM performance_db.management_talk_responses r USING wave w, actor a
  WHERE r.wave_id = w.id AND r.responder_id = a.id RETURNING r.responder_id
)
SELECT (SELECT count(*)::integer FROM deleted) AS written,
       EXISTS(SELECT 1 FROM wave) AS wave_open,
       EXISTS(SELECT 1 FROM actor) AS actor_employed
` } };
""".strip()

WITHDRAW_FORMAT = r"""
const prev = $('Build Withdraw Query').first().json;
if (prev.http_status) return { json: prev };
const row = $input.all().map(i => i.json).find(r => r.written !== undefined);
const truthy = v => v === true || v === 't';
if (!row || !truthy(row.actor_employed)) return { json: { http_status: 403,
  body: { success: false, error: 'ACTOR_TERMINATED', message: 'Учётная запись неактивна' } } };
if (!truthy(row.wave_open)) return { json: { http_status: 409,
  body: { success: false, error: 'TALK_WAVE_CLOSED', message: 'Срок ответа завершён' } } };
if (Number(row.written) !== 1) return { json: { http_status: 404,
  body: { success: false, error: 'TALK_RESPONSE_NOT_FOUND', message: 'Ответа нет' } } };
return { json: { http_status: 200,
  body: { success: true, withdrawn: true, message: 'Ответ снят' } } };
""".strip()

LIST_BUILD = r"""
const guard = $('Run Auth Guard LIST').first().json;
if (!guard.ok) return { json: { http_status: guard.status,
  body: { success: false, error: guard.code, message: guard.message },
  sql: 'SELECT NULL::integer AS wave_id WHERE false' } };
return { json: { sql: `
WITH wave AS (
  SELECT w.id, w.wave_key, w.opens_at, w.closes_at,
         clock_timestamp() BETWEEN w.opens_at AND w.closes_at AS is_open
  FROM (SELECT * FROM performance_db.management_talk_waves ORDER BY id DESC LIMIT 1) w
), employed AS (
  SELECT u.id, (u.password_hash IS NOT NULL) AS is_registered
  FROM performance_db.users u WHERE u.terminated_at IS NULL
), responses AS (
  SELECT r.* FROM performance_db.management_talk_responses r JOIN wave w ON w.id = r.wave_id
), topic_counts AS (
  SELECT t.topic_key, t.label, count(r.responder_id)::integer AS response_count
  FROM performance_db.management_talk_topics t LEFT JOIN responses r ON r.topic_key = t.topic_key
  GROUP BY t.topic_key, t.label
), response_rows AS (
  SELECT r.responder_id, u.full_name AS responder_name, u.role,
         r.answer_key, r.topic_key, t.label AS topic_label, r.counterpart_mode,
         r.urgency_key, r.group_readiness_key,
         to_char(r.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
         to_char(r.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at,
         COALESCE(json_agg(json_build_object('id', cp.counterpart_id, 'full_name', cu.full_name)
           ORDER BY cu.full_name, cp.counterpart_id)
           FILTER (WHERE cp.counterpart_id IS NOT NULL), '[]'::json) AS counterparts
  FROM responses r JOIN performance_db.users u ON u.id = r.responder_id
  LEFT JOIN performance_db.management_talk_topics t ON t.topic_key = r.topic_key
  LEFT JOIN performance_db.management_talk_counterparts cp
    ON cp.wave_id = r.wave_id AND cp.responder_id = r.responder_id
  LEFT JOIN performance_db.users cu ON cu.id = cp.counterpart_id
  GROUP BY r.responder_id, u.full_name, u.role, r.answer_key, r.topic_key, t.label,
           r.counterpart_mode, r.urgency_key, r.group_readiness_key, r.created_at, r.updated_at
)
SELECT w.id AS wave_id, w.wave_key, w.is_open,
  to_char(w.opens_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS opens_at,
  to_char(w.closes_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS closes_at,
  (SELECT count(*)::integer FROM employed) AS employed,
  (SELECT count(*)::integer FROM responses WHERE answer_key = 'all_good') AS all_good,
  (SELECT count(*)::integer FROM responses WHERE answer_key = 'topic_only') AS topic_only,
  (SELECT count(*)::integer FROM responses WHERE answer_key = 'conversation') AS conversation,
  (SELECT count(*)::integer FROM employed e WHERE e.is_registered
    AND NOT EXISTS (SELECT 1 FROM responses r WHERE r.responder_id = e.id)) AS registered_unanswered,
  (SELECT count(*)::integer FROM employed e WHERE NOT e.is_registered) AS never_registered,
  COALESCE((SELECT json_agg(row_to_json(tc) ORDER BY tc.topic_key) FROM topic_counts tc), '[]'::json) AS topics,
  COALESCE((SELECT json_agg(row_to_json(rr) ORDER BY rr.updated_at DESC, rr.responder_id)
            FROM response_rows rr), '[]'::json) AS responses
FROM wave w
` } };
""".strip()

LIST_FORMAT = r"""
const prev = $('Build Admin Query').first().json;
if (prev.http_status) return { json: prev };
const row = $input.all().map(i => i.json).find(r => r.wave_id !== undefined);
if (!row) return { json: { http_status: 404,
  body: { success: false, error: 'TALK_WAVE_NOT_FOUND', message: 'Волна не найдена' } } };
const parse = (v, fallback) => {
  if (v === null || v === undefined) return fallback;
  if (typeof v !== 'string') return v;
  try { return JSON.parse(v); } catch { return fallback; }
};
const truthy = v => v === true || v === 't';
const answers = __ANSWERS__;
const urgencies = __URGENCIES__;
const groups = __GROUPS__;
const responses = parse(row.responses, []).map(r => ({
  ...r, responder_id: Number(r.responder_id), answer_label: answers[r.answer_key],
  urgency_label: r.urgency_key ? urgencies[r.urgency_key] : null,
  group_readiness_label: r.group_readiness_key ? groups[r.group_readiness_key] : null,
  counterparts: parse(r.counterparts, []).map(c => ({ ...c, id: Number(c.id) })),
}));
return { json: { http_status: 200, body: {
  success: true,
  wave: { id: Number(row.wave_id), key: row.wave_key, is_open: truthy(row.is_open),
          opens_at: row.opens_at, closes_at: row.closes_at },
  counts: { employed: Number(row.employed), all_good: Number(row.all_good),
    topic_only: Number(row.topic_only), conversation: Number(row.conversation),
    registered_unanswered: Number(row.registered_unanswered),
    never_registered: Number(row.never_registered) },
  topics: parse(row.topics, []).map(t => ({ ...t, response_count: Number(t.response_count) })),
  responses,
} } };
""".strip().replace(
    "__ANSWERS__", json.dumps(ANSWER_LABELS, ensure_ascii=False)
).replace(
    "__URGENCIES__", json.dumps(URGENCY_LABELS, ensure_ascii=False)
).replace(
    "__GROUPS__", json.dumps(GROUP_LABELS, ensure_ascii=False)
)


def build_talk_channel(credential_id: str, guard_workflow_id: str) -> dict[str, Any]:
    def pg(node_id: str, name: str, position: list[int], empty: str) -> dict[str, Any]:
        return _node(
            node_id, name, "n8n-nodes-base.postgres", position,
            {"operation": "executeQuery",
             "query": f"={{{{ $json.sql || 'SELECT NULL::integer AS {empty} WHERE false' }}}}",
             "options": {}},
            type_version=2.6,
            credentials={"postgres": {"id": credential_id, "name": "EPE 2026 Postgres"}},
            alwaysOutputData=True,
        )

    nodes = [
        _node("talk-webhook-form", "Webhook FORM", "n8n-nodes-base.webhook", [-700, 0],
              {"httpMethod": "GET", "path": "api/talk/form", "responseMode": "responseNode", "options": {}},
              type_version=2.1, webhookId="epe-talk-form"),
        _node("talk-guard-form", "Prepare Guard Input FORM", "n8n-nodes-base.code", [-480, 0],
              {"jsCode": _guard_input([])}),
        _run_guard("talk-run-form", "Run Auth Guard FORM", [-250, 0], guard_workflow_id),
        _node("talk-form-build", "Build Form Query", "n8n-nodes-base.code", [0, 0], {"jsCode": FORM_BUILD}),
        pg("talk-form-load", "Load Form", [250, 0], "actor_id"),
        _node("talk-form-format", "Format Form Response", "n8n-nodes-base.code", [500, 0], {"jsCode": FORM_FORMAT}),
        _respond("talk-form-respond", "Respond FORM", [740, 0]),

        _node("talk-webhook-save", "Webhook SAVE", "n8n-nodes-base.webhook", [-700, 300],
              {"httpMethod": "POST", "path": "api/talk/save", "responseMode": "responseNode", "options": {}},
              type_version=2.1, webhookId="epe-talk-save"),
        _node("talk-guard-save", "Prepare Guard Input SAVE", "n8n-nodes-base.code", [-480, 300],
              {"jsCode": _guard_input([])}),
        _run_guard("talk-run-save", "Run Auth Guard SAVE", [-250, 300], guard_workflow_id),
        _node("talk-save-validate", "Validate Save", "n8n-nodes-base.code", [0, 300], {"jsCode": SAVE_VALIDATE}),
        pg("talk-save-check", "Load Save Target", [250, 300], "actor_id"),
        _node("talk-save-build", "Build Save SQL", "n8n-nodes-base.code", [500, 300], {"jsCode": SAVE_BUILD}),
        pg("talk-save-execute", "Execute Save", [750, 300], "written"),
        _node("talk-save-format", "Format Save Response", "n8n-nodes-base.code", [1000, 300], {"jsCode": SAVE_FORMAT}),
        _respond("talk-save-respond", "Respond SAVE", [1240, 300]),

        _node("talk-webhook-withdraw", "Webhook WITHDRAW", "n8n-nodes-base.webhook", [-700, 600],
              {"httpMethod": "POST", "path": "api/talk/withdraw", "responseMode": "responseNode", "options": {}},
              type_version=2.1, webhookId="epe-talk-withdraw"),
        _node("talk-guard-withdraw", "Prepare Guard Input WITHDRAW", "n8n-nodes-base.code", [-480, 600],
              {"jsCode": _guard_input([])}),
        _run_guard("talk-run-withdraw", "Run Auth Guard WITHDRAW", [-250, 600], guard_workflow_id),
        _node("talk-withdraw-build", "Build Withdraw Query", "n8n-nodes-base.code", [0, 600],
              {"jsCode": WITHDRAW_BUILD}),
        pg("talk-withdraw-execute", "Execute Withdraw", [250, 600], "written"),
        _node("talk-withdraw-format", "Format Withdraw Response", "n8n-nodes-base.code", [500, 600],
              {"jsCode": WITHDRAW_FORMAT}),
        _respond("talk-withdraw-respond", "Respond WITHDRAW", [740, 600]),

        _node("talk-webhook-list", "Webhook LIST", "n8n-nodes-base.webhook", [-700, 900],
              {"httpMethod": "GET", "path": "api/talk/list", "responseMode": "responseNode", "options": {}},
              type_version=2.1, webhookId="epe-talk-list"),
        _node("talk-guard-list", "Prepare Guard Input LIST", "n8n-nodes-base.code", [-480, 900],
              {"jsCode": _guard_input(["admin"])}),
        _run_guard("talk-run-list", "Run Auth Guard LIST", [-250, 900], guard_workflow_id),
        _node("talk-list-build", "Build Admin Query", "n8n-nodes-base.code", [0, 900], {"jsCode": LIST_BUILD}),
        pg("talk-list-load", "Load Admin Results", [250, 900], "wave_id"),
        _node("talk-list-format", "Format Admin Response", "n8n-nodes-base.code", [500, 900],
              {"jsCode": LIST_FORMAT}),
        _respond("talk-list-respond", "Respond LIST", [740, 900]),
    ]
    names = [n["name"] for n in nodes]
    # Respond nodes end each independent route, so they have no outgoing edge.
    connections = {
        name: _connect(names[i + 1])
        for i, name in enumerate(names[:-1])
        if not name.startswith("Respond ")
    }
    return {
        "name": "API: Management Talk",
        "nodes": nodes,
        "connections": connections,
        "settings": {
            "executionOrder": "v1", "saveDataErrorExecution": "none",
            "saveDataSuccessExecution": "none", "saveManualExecutions": False,
            "callerPolicy": "workflowsFromSameOwner", "availableInMCP": False,
        },
        "active": False,
    }
