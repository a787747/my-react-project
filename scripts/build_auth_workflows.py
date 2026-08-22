#!/usr/bin/env python3
"""Generate inactive n8n authentication-core workflow payloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


POSTGRES_CREDENTIAL_PLACEHOLDER = "__EPE_POSTGRES_CREDENTIAL_ID__"
GUARD_WORKFLOW_PLACEHOLDER = "__EPE_AUTH_GUARD_WORKFLOW_ID__"
SMTP_CREDENTIAL_ID = "Owjl0MaDCmpyOksi"

AUTH_SETTINGS = {
    "executionOrder": "v1",
    "saveDataErrorExecution": "none",
    "saveDataSuccessExecution": "none",
    "saveManualExecutions": False,
}


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
    return {
        "postgres": {
            "id": credential_id,
            "name": "EPE 2026 Postgres",
        }
    }


def smtp_credentials(credential_id: str) -> dict[str, Any]:
    return {
        "smtp": {
            "id": credential_id,
            "name": "SMTP account",
        }
    }


def connect(*targets: str) -> dict[str, Any]:
    return {
        "main": [[
            {"node": target, "type": "main", "index": 0}
            for target in targets
        ]]
    }


def workflow(
    name: str,
    nodes: list[dict[str, Any]],
    connections: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "settings": AUTH_SETTINGS,
    }


LOGIN_NORMALIZE = r"""
const body = $input.first().json.body || $input.first().json;
const email = String(body.email || '').trim().toLowerCase();
const password = String(body.password || '');

if (!email || email.length > 150 || !email.endsWith('@sedamedical.com')) {
  return { json: { email: '', password, input_valid: false } };
}

return {
  json: {
    email,
    safe_email: email.replace(/'/g, "''"),
    password,
    input_valid: password.length > 0,
  },
};
""".strip()

LOGIN_LOAD_SQL = r"""
=WITH input(email) AS (VALUES ('{{ $json.safe_email }}'))
SELECT
  input.email AS attempted_email,
  u.id,
  u.full_name,
  u.email,
  u.password_hash,
  u.role,
  u.department_id,
  u.grade_id,
  u.manager_id,
  u.job_title,
  u.work_category,
  u.is_project_participant,
  u.has_subordinates,
  u.can_evaluate,
  u.can_be_evaluated,
  u.token_version,
  attempts.failed_count,
  attempts.window_started_at,
  attempts.locked_until
FROM input
LEFT JOIN performance_db.users u
  ON lower(u.email) = input.email
LEFT JOIN performance_db.auth_login_attempts attempts
  ON attempts.email = input.email
""".strip()

LOGIN_VERIFY = r"""
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const row = $input.first().json;
const input = $('Normalize Login').first().json;
const now = Date.now();
const lockedUntil = row.locked_until ? Date.parse(row.locked_until) : 0;
const isLocked = Number.isFinite(lockedUntil) && lockedUntil > now;

const scryptOptions = { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };

function verifyScrypt(password, stored) {
  let salt = Buffer.alloc(16, 0);
  let expected = Buffer.alloc(64, 0);
  let formatValid = false;

  if (typeof stored === 'string') {
    const parts = stored.split('$');
    if (
      parts.length === 5
      && parts[1] === 'scrypt'
      && parts[2] === 'N=16384,r=8,p=1'
    ) {
      try {
        salt = Buffer.from(parts[3], 'base64url');
        expected = Buffer.from(parts[4], 'base64url');
        formatValid = salt.length === 16 && expected.length === 64;
      } catch {
        formatValid = false;
      }
    }
  }

  const actual = crypto.scryptSync(password, salt, 64, scryptOptions);
  const matches = expected.length === actual.length
    && crypto.timingSafeEqual(actual, expected);
  return formatValid && matches;
}

const passwordMatches = verifyScrypt(input.password, row.password_hash);
const authenticated = Boolean(
  input.input_valid
  && row.id
  && !isLocked
  && passwordMatches
);

if (!authenticated) {
  let sql;
  if (isLocked && input.email) {
    sql = `
      SELECT failed_count, locked_until
      FROM performance_db.auth_login_attempts
      WHERE email = '${input.safe_email}'
    `;
  } else if (input.email) {
    sql = `
      INSERT INTO performance_db.auth_login_attempts (
        email, window_started_at, failed_count, locked_until,
        last_failed_at, updated_at
      )
      VALUES ('${input.safe_email}', now(), 1, NULL, now(), now())
      ON CONFLICT (email) DO UPDATE
      SET failed_count = CASE
            WHEN auth_login_attempts.window_started_at < now() - interval '15 minutes'
              OR auth_login_attempts.locked_until <= now()
            THEN 1
            ELSE auth_login_attempts.failed_count + 1
          END,
          window_started_at = CASE
            WHEN auth_login_attempts.window_started_at < now() - interval '15 minutes'
              OR auth_login_attempts.locked_until <= now()
            THEN now()
            ELSE auth_login_attempts.window_started_at
          END,
          locked_until = CASE
            WHEN auth_login_attempts.window_started_at < now() - interval '15 minutes'
              OR auth_login_attempts.locked_until <= now()
            THEN NULL
            WHEN auth_login_attempts.failed_count + 1 >= 5
            THEN now() + interval '15 minutes'
            ELSE auth_login_attempts.locked_until
          END,
          last_failed_at = now(),
          updated_at = now()
      RETURNING failed_count, locked_until
    `;
  } else {
    sql = 'SELECT 0 AS failed_count, NULL::timestamptz AS locked_until';
  }

  return {
    json: {
      authenticated: false,
      is_locked: isLocked,
      sql,
      http_status: 401,
      body: {
        success: false,
        message: 'Неверный email или пароль',
      },
    },
  };
}

const jti = crypto.randomUUID();
const secret = $env.JWT_SIGNING_SECRET;
if (!secret) throw new Error('JWT_SIGNING_SECRET is unavailable');

const token = jwt.sign(
  {},
  secret,
  {
    algorithm: 'HS256',
    subject: String(row.id),
    issuer: 'epe',
    audience: 'epe-api',
    jwtid: jti,
    expiresIn: '4h',
  },
);
const decoded = jwt.decode(token);

const sql = `
  WITH cleared AS (
    DELETE FROM performance_db.auth_login_attempts
    WHERE email = '${input.safe_email}'
  )
  INSERT INTO performance_db.auth_sessions (
    jti, user_id, token_version, issued_at, expires_at
  )
  VALUES (
    '${jti}'::uuid,
    ${row.id},
    ${row.token_version},
    to_timestamp(${decoded.iat}),
    to_timestamp(${decoded.exp})
  )
  RETURNING jti
`;

const {
  password_hash,
  failed_count,
  window_started_at,
  locked_until,
  token_version,
  ...safeUser
} = row;

return {
  json: {
    authenticated: true,
    sql,
    token,
    user: safeUser,
    http_status: 200,
    body: {
      success: true,
      user: safeUser,
      token,
    },
  },
};
""".strip()

LOGIN_FORMAT = r"""
const auth = $('Verify Password').first().json;
return {
  json: {
    http_status: auth.http_status,
    body: auth.body,
  },
};
""".strip()


def build_login(credential_id: str) -> dict[str, Any]:
    nodes = [
        node(
            "login-webhook",
            "Webhook",
            "n8n-nodes-base.webhook",
            [-700, 0],
            {
                "httpMethod": "POST",
                "path": "auth/login",
                "responseMode": "responseNode",
                "options": {},
            },
            type_version=2.1,
            webhook_id="cecacd34-0c91-4cd0-b1e9-f4c2cc4c883d",
        ),
        node(
            "login-normalize",
            "Normalize Login",
            "n8n-nodes-base.code",
            [-480, 0],
            {"jsCode": LOGIN_NORMALIZE},
        ),
        node(
            "login-load",
            "Load User and Attempts",
            "n8n-nodes-base.postgres",
            [-250, 0],
            {
                "operation": "executeQuery",
                "query": LOGIN_LOAD_SQL,
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "login-verify",
            "Verify Password",
            "n8n-nodes-base.code",
            [0, 0],
            {"jsCode": LOGIN_VERIFY},
        ),
        node(
            "login-persist",
            "Persist Auth Result",
            "n8n-nodes-base.postgres",
            [250, 0],
            {
                "operation": "executeQuery",
                "query": "={{ $json.sql }}",
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "login-format",
            "Format Login Response",
            "n8n-nodes-base.code",
            [500, 0],
            {"jsCode": LOGIN_FORMAT},
        ),
        node(
            "login-respond",
            "Respond",
            "n8n-nodes-base.respondToWebhook",
            [740, 0],
            {
                "respondWith": "json",
                "responseBody": "={{ $json.body }}",
                "options": {
                    "responseCode": "={{ $json.http_status }}",
                },
            },
            type_version=1.4,
        ),
    ]
    connections = {
        "Webhook": connect("Normalize Login"),
        "Normalize Login": connect("Load User and Attempts"),
        "Load User and Attempts": connect("Verify Password"),
        "Verify Password": connect("Persist Auth Result"),
        "Persist Auth Result": connect("Format Login Response"),
        "Format Login Response": connect("Respond"),
    }
    return workflow("API: Auth Login (No Params)", nodes, connections)


REGISTER_VALIDATE = r"""
const body = $input.first().json.body || $input.first().json;
const token = String(body.token || '').trim();
const email = String(body.email || '').trim().toLowerCase();
const password = String(body.password || '');
const verificationCode = String(body.verification_code || '').trim();

if (
  !/^[A-Za-z0-9_-]{16,128}$/.test(token)
  || !email.endsWith('@sedamedical.com')
  || email.length > 150
  || password.length < 8
  || !/^\d{6}$/.test(verificationCode)
) {
  return {
    json: {
      input_valid: false,
      safe_email: '',
      safe_token: '',
      safe_code: '',
      password,
    },
  };
}

return {
  json: {
    input_valid: true,
    email,
    safe_email: email.replace(/'/g, "''"),
    safe_token: token.replace(/'/g, "''"),
    safe_code: verificationCode,
    password,
  },
};
""".strip()

REGISTER_LOAD_SQL = r"""
=SELECT
  users.id AS user_id,
  users.full_name,
  users.email,
  users.role,
  users.password_hash,
  invites.id AS invite_id,
  codes.id AS code_id
FROM performance_db.users users
JOIN performance_db.invite_tokens invites
  ON invites.token = '{{ $json.safe_token }}'
  AND invites.expires_at > now()
JOIN performance_db.email_verification_codes codes
  ON lower(codes.email) = lower(users.email)
  AND codes.code = '{{ $json.safe_code }}'
  AND codes.expires_at > now()
  AND codes.is_verified = true
WHERE lower(users.email) = lower('{{ $json.safe_email }}')
  AND users.password_hash IS NULL
ORDER BY codes.verified_at DESC NULLS LAST
LIMIT 1
""".strip()

REGISTER_HASH = r"""
const crypto = require('crypto');
const input = $('Validate Registration').first().json;
const row = $input.first().json;

if (!input.input_valid || !row.user_id || row.password_hash) {
  return {
    json: {
      sql: 'SELECT false AS registered',
      http_status: 400,
      body: {
        success: false,
        message: 'Ссылка для регистрации или код подтверждения недействительны',
      },
    },
  };
}

const salt = crypto.randomBytes(16);
const derived = crypto.scryptSync(
  input.password,
  salt,
  64,
  { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 },
);
const passwordHash = [
  '',
  'scrypt',
  'N=16384,r=8,p=1',
  salt.toString('base64url'),
  derived.toString('base64url'),
].join('$');

const sql = `
  WITH updated_user AS (
    UPDATE performance_db.users
    SET password_hash = '${passwordHash}'
    WHERE id = ${row.user_id}
      AND password_hash IS NULL
    RETURNING id, full_name, email, role
  ),
  used_invite AS (
    SELECT id FROM performance_db.invite_tokens
    WHERE id = ${row.invite_id}
      AND expires_at > now()
  ),
  consumed_code AS (
    DELETE FROM performance_db.email_verification_codes
    WHERE id = ${row.code_id}
    RETURNING id
  )
  SELECT
    updated_user.id,
    updated_user.full_name,
    updated_user.email,
    updated_user.role,
    EXISTS(SELECT 1 FROM used_invite) AS invite_used,
    EXISTS(SELECT 1 FROM consumed_code) AS code_consumed
  FROM updated_user
`;

return {
  json: {
    sql,
    http_status: 200,
  },
};
""".strip()

REGISTER_FORMAT = r"""
const prepared = $('Hash Password').first().json;
const row = $input.first().json;
const registered = Boolean(
  row.id
  && row.invite_used
  && row.code_consumed
);

return {
  json: registered
    ? {
        http_status: 200,
        body: {
          success: true,
          message: 'Регистрация завершена. Теперь вы можете войти в систему.',
          data: {
            user_id: row.id,
            full_name: row.full_name,
            email: row.email,
            role: row.role,
          },
        },
      }
    : {
        http_status: prepared.http_status || 400,
        body: prepared.body || {
          success: false,
          message: 'Ссылка для регистрации или код подтверждения недействительны',
        },
      },
};
""".strip()


def build_register(credential_id: str) -> dict[str, Any]:
    nodes = [
        node(
            "register-webhook",
            "Webhook",
            "n8n-nodes-base.webhook",
            [-700, 0],
            {
                "httpMethod": "POST",
                "path": "api/register",
                "responseMode": "responseNode",
                "options": {},
            },
            type_version=2.1,
            webhook_id="register-webhook",
        ),
        node(
            "register-validate",
            "Validate Registration",
            "n8n-nodes-base.code",
            [-480, 0],
            {"jsCode": REGISTER_VALIDATE},
        ),
        node(
            "register-load",
            "Load Registration Context",
            "n8n-nodes-base.postgres",
            [-240, 0],
            {
                "operation": "executeQuery",
                "query": REGISTER_LOAD_SQL,
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "register-hash",
            "Hash Password",
            "n8n-nodes-base.code",
            [0, 0],
            {"jsCode": REGISTER_HASH},
        ),
        node(
            "register-persist",
            "Persist Registration",
            "n8n-nodes-base.postgres",
            [250, 0],
            {
                "operation": "executeQuery",
                "query": "={{ $json.sql }}",
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "register-format",
            "Format Registration Response",
            "n8n-nodes-base.code",
            [500, 0],
            {"jsCode": REGISTER_FORMAT},
        ),
        node(
            "register-respond",
            "Respond",
            "n8n-nodes-base.respondToWebhook",
            [740, 0],
            {
                "respondWith": "json",
                "responseBody": "={{ $json.body }}",
                "options": {
                    "responseCode": "={{ $json.http_status }}",
                },
            },
            type_version=1.4,
        ),
    ]
    connections = {
        "Webhook": connect("Validate Registration"),
        "Validate Registration": connect("Load Registration Context"),
        "Load Registration Context": connect("Hash Password"),
        "Hash Password": connect("Persist Registration"),
        "Persist Registration": connect("Format Registration Response"),
        "Format Registration Response": connect("Respond"),
    }
    return workflow("API: Register", nodes, connections)


RESET_REQUEST_NORMALIZE = r"""
const body = $input.first().json.body || $input.first().json;
const email = String(body.email || '').trim().toLowerCase();
const valid = email.length <= 150 && email.endsWith('@sedamedical.com');
return {
  json: {
    email: valid ? email : '',
    safe_email: valid ? email.replace(/'/g, "''") : '',
  },
};
""".strip()

RESET_REQUEST_LOAD_SQL = r"""
=WITH input(email) AS (VALUES ('{{ $json.safe_email }}'))
SELECT
  input.email AS attempted_email,
  users.id AS user_id,
  users.full_name,
  users.email,
  latest.created_at AS latest_reset_at
FROM input
LEFT JOIN performance_db.users users
  ON lower(users.email) = input.email
LEFT JOIN LATERAL (
  SELECT created_at
  FROM performance_db.password_reset_tokens
  WHERE user_id = users.id
  ORDER BY created_at DESC
  LIMIT 1
) latest ON true
""".strip()

RESET_REQUEST_GENERATE = r"""
const crypto = require('crypto');
const row = $input.first().json;
const now = Date.now();
const latest = row.latest_reset_at ? Date.parse(row.latest_reset_at) : 0;
const cooldownPassed = !Number.isFinite(latest) || now - latest >= 5 * 60 * 1000;
const shouldSend = Boolean(row.user_id && row.email && cooldownPassed);

if (!shouldSend) {
  return {
    json: {
      should_send: false,
      sql: 'SELECT false AS reset_created',
    },
  };
}

const rawToken = crypto.randomBytes(32).toString('base64url');
const tokenHash = crypto.createHash('sha256').update(rawToken).digest('hex');
const safeName = String(row.full_name || '').replace(/'/g, "''");
const frontendUrl = String($env.EPE_FRONTEND_URL || '').replace(/\/$/, '');
if (!/^https:\/\/[^/]+/i.test(frontendUrl)) {
  throw new Error('EPE_FRONTEND_URL must be configured with an HTTPS origin');
}
const resetUrl = `${frontendUrl}/reset-password?token=${encodeURIComponent(rawToken)}`;
const sql = `
  WITH invalidated AS (
    UPDATE performance_db.password_reset_tokens
    SET used_at = now()
    WHERE user_id = ${row.user_id}
      AND used_at IS NULL
  )
  INSERT INTO performance_db.password_reset_tokens (
    user_id, token_hash, expires_at
  )
  VALUES (
    ${row.user_id},
    '${tokenHash}',
    now() + interval '30 minutes'
  )
  RETURNING id
`;

return {
  json: {
    should_send: true,
    sql,
    email: row.email,
    full_name: safeName,
    reset_url: resetUrl,
  },
};
""".strip()

RESET_REQUEST_RESPONSE = r"""
return {
  json: {
    http_status: 200,
    body: {
      success: true,
      message: 'If the account exists, a reset link has been sent.',
    },
  },
};
""".strip()


def build_reset_request(
    credential_id: str,
    smtp_credential_id: str,
) -> dict[str, Any]:
    nodes = [
        node(
            "reset-request-webhook",
            "Webhook",
            "n8n-nodes-base.webhook",
            [-800, 0],
            {
                "httpMethod": "POST",
                "path": "api/request-password-reset",
                "responseMode": "responseNode",
                "options": {},
            },
            type_version=2.1,
            webhook_id="epe-request-password-reset",
        ),
        node(
            "reset-request-normalize",
            "Normalize Email",
            "n8n-nodes-base.code",
            [-600, 0],
            {"jsCode": RESET_REQUEST_NORMALIZE},
        ),
        node(
            "reset-request-load",
            "Load Reset Context",
            "n8n-nodes-base.postgres",
            [-390, 0],
            {
                "operation": "executeQuery",
                "query": RESET_REQUEST_LOAD_SQL,
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "reset-request-generate",
            "Generate Reset Token",
            "n8n-nodes-base.code",
            [-170, 0],
            {"jsCode": RESET_REQUEST_GENERATE},
        ),
        node(
            "reset-request-persist",
            "Persist Reset Token",
            "n8n-nodes-base.postgres",
            [50, 0],
            {
                "operation": "executeQuery",
                "query": "={{ $json.sql }}",
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "reset-request-if",
            "Should Send Email?",
            "n8n-nodes-base.if",
            [270, 0],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [{
                        "id": "reset-should-send",
                        "leftValue": "={{ $('Generate Reset Token').first().json.should_send }}",
                        "rightValue": True,
                        "operator": {
                            "type": "boolean",
                            "operation": "equals",
                        },
                    }],
                    "combinator": "and",
                },
                "options": {},
            },
            type_version=2,
        ),
        node(
            "reset-request-email",
            "Send Reset Email",
            "n8n-nodes-base.emailSend",
            [500, -100],
            {
                "fromEmail": "noreply@sedamedical.com",
                "toEmail": "={{ $('Generate Reset Token').first().json.email }}",
                "subject": "Сброс пароля — SEDA Medical",
                "html": (
                    "=<p>Здравствуйте, "
                    "{{ $('Generate Reset Token').first().json.full_name }}.</p>"
                    "<p>Для создания нового пароля перейдите по ссылке:</p>"
                    "<p><a href=\"{{ $('Generate Reset Token').first().json.reset_url }}\">"
                    "Создать новый пароль</a></p>"
                    "<p>Ссылка одноразовая и действует 30 минут.</p>"
                ),
                "options": {
                    "appendAttribution": False,
                },
            },
            type_version=2.1,
            credentials=smtp_credentials(smtp_credential_id),
        ),
        node(
            "reset-request-response",
            "Format Generic Response",
            "n8n-nodes-base.code",
            [720, 0],
            {"jsCode": RESET_REQUEST_RESPONSE},
        ),
        node(
            "reset-request-respond",
            "Respond",
            "n8n-nodes-base.respondToWebhook",
            [950, 0],
            {
                "respondWith": "json",
                "responseBody": "={{ $json.body }}",
                "options": {
                    "responseCode": "={{ $json.http_status }}",
                },
            },
            type_version=1.4,
        ),
    ]
    connections = {
        "Webhook": connect("Normalize Email"),
        "Normalize Email": connect("Load Reset Context"),
        "Load Reset Context": connect("Generate Reset Token"),
        "Generate Reset Token": connect("Persist Reset Token"),
        "Persist Reset Token": connect("Should Send Email?"),
        "Should Send Email?": {
            "main": [
                [{"node": "Send Reset Email", "type": "main", "index": 0}],
                [{"node": "Format Generic Response", "type": "main", "index": 0}],
            ]
        },
        "Send Reset Email": connect("Format Generic Response"),
        "Format Generic Response": connect("Respond"),
    }
    return workflow("API: Request Password Reset", nodes, connections)


RESET_VALIDATE = r"""
const crypto = require('crypto');
const body = $input.first().json.body || $input.first().json;
const token = String(body.token || '').trim();
const password = String(body.password || '');
const tokenValid = /^[A-Za-z0-9_-]{40,128}$/.test(token);
const passwordValid = password.length >= 8;

if (!tokenValid || !passwordValid) {
  return {
    json: {
      input_valid: false,
      token_hash: '0'.repeat(64),
      password,
    },
  };
}

return {
  json: {
    input_valid: true,
    token_hash: crypto.createHash('sha256').update(token).digest('hex'),
    password,
  },
};
""".strip()

RESET_LOAD_SQL = r"""
=SELECT
  reset.id AS reset_id,
  reset.user_id,
  users.email,
  users.token_version
FROM performance_db.password_reset_tokens reset
JOIN performance_db.users users ON users.id = reset.user_id
WHERE reset.token_hash = '{{ $json.token_hash }}'
  AND reset.used_at IS NULL
  AND reset.expires_at > now()
LIMIT 1
""".strip()

RESET_HASH = r"""
const crypto = require('crypto');
const input = $('Validate Reset').first().json;
const row = $input.first().json;

if (!input.input_valid || !row.reset_id || !row.user_id) {
  return {
    json: {
      sql: 'SELECT false AS password_reset',
      http_status: 400,
      body: {
        success: false,
        message: 'Ссылка для сброса пароля недействительна или истекла',
      },
    },
  };
}

const salt = crypto.randomBytes(16);
const derived = crypto.scryptSync(
  input.password,
  salt,
  64,
  { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 },
);
const passwordHash = [
  '',
  'scrypt',
  'N=16384,r=8,p=1',
  salt.toString('base64url'),
  derived.toString('base64url'),
].join('$');

const sql = `
  WITH updated_user AS (
    UPDATE performance_db.users
    SET password_hash = '${passwordHash}',
        token_version = token_version + 1
    WHERE id = ${row.user_id}
    RETURNING id, token_version
  ),
  used_token AS (
    UPDATE performance_db.password_reset_tokens
    SET used_at = now()
    WHERE id = ${row.reset_id}
      AND used_at IS NULL
    RETURNING id
  ),
  revoked_sessions AS (
    UPDATE performance_db.auth_sessions
    SET revoked_at = now()
    WHERE user_id = ${row.user_id}
      AND revoked_at IS NULL
    RETURNING jti
  )
  SELECT
    updated_user.id,
    updated_user.token_version,
    EXISTS(SELECT 1 FROM used_token) AS token_used,
    (SELECT count(*) FROM revoked_sessions) AS sessions_revoked
  FROM updated_user
`;

return {
  json: {
    sql,
    http_status: 200,
  },
};
""".strip()

RESET_FORMAT = r"""
const prepared = $('Hash New Password').first().json;
const row = $input.first().json;
const success = Boolean(row.id && row.token_used);
return {
  json: success
    ? {
        http_status: 200,
        body: {
          success: true,
          message: 'Пароль изменён. Войдите в систему снова.',
        },
      }
    : {
        http_status: prepared.http_status || 400,
        body: prepared.body || {
          success: false,
          message: 'Ссылка для сброса пароля недействительна или истекла',
        },
      },
};
""".strip()


def build_reset_password(credential_id: str) -> dict[str, Any]:
    nodes = [
        node(
            "reset-password-webhook",
            "Webhook",
            "n8n-nodes-base.webhook",
            [-700, 0],
            {
                "httpMethod": "POST",
                "path": "api/reset-password",
                "responseMode": "responseNode",
                "options": {},
            },
            type_version=2.1,
            webhook_id="epe-reset-password",
        ),
        node(
            "reset-password-validate",
            "Validate Reset",
            "n8n-nodes-base.code",
            [-480, 0],
            {"jsCode": RESET_VALIDATE},
        ),
        node(
            "reset-password-load",
            "Load Reset Token",
            "n8n-nodes-base.postgres",
            [-250, 0],
            {
                "operation": "executeQuery",
                "query": RESET_LOAD_SQL,
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "reset-password-hash",
            "Hash New Password",
            "n8n-nodes-base.code",
            [0, 0],
            {"jsCode": RESET_HASH},
        ),
        node(
            "reset-password-persist",
            "Persist Password Reset",
            "n8n-nodes-base.postgres",
            [250, 0],
            {
                "operation": "executeQuery",
                "query": "={{ $json.sql }}",
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "reset-password-format",
            "Format Reset Response",
            "n8n-nodes-base.code",
            [500, 0],
            {"jsCode": RESET_FORMAT},
        ),
        node(
            "reset-password-respond",
            "Respond",
            "n8n-nodes-base.respondToWebhook",
            [740, 0],
            {
                "respondWith": "json",
                "responseBody": "={{ $json.body }}",
                "options": {
                    "responseCode": "={{ $json.http_status }}",
                },
            },
            type_version=1.4,
        ),
    ]
    connections = {
        "Webhook": connect("Validate Reset"),
        "Validate Reset": connect("Load Reset Token"),
        "Load Reset Token": connect("Hash New Password"),
        "Hash New Password": connect("Persist Password Reset"),
        "Persist Password Reset": connect("Format Reset Response"),
        "Format Reset Response": connect("Respond"),
    }
    return workflow("API: Reset Password", nodes, connections)


GUARD_VERIFY = r"""
const jwt = require('jsonwebtoken');
const input = $input.first().json;
const authorization = String(
  input.authorization
  || input.request?.headers?.authorization
  || '',
);
const requiredRoles = Array.isArray(input.required_roles)
  ? input.required_roles
  : [];
const requiredCapability = String(input.required_capability || '');

const rejected = (code, message) => ({
  token_valid: false,
  sub: 0,
  jti: '00000000-0000-0000-0000-000000000000',
  required_roles: requiredRoles,
  required_capability: requiredCapability,
  request: input.request || {},
  rejection: { ok: false, status: 401, code, message },
});

if (!authorization.startsWith('Bearer ')) {
  return { json: rejected('TOKEN_MISSING', 'Bearer token is required') };
}

try {
  const decoded = jwt.verify(
    authorization.slice(7),
    $env.JWT_SIGNING_SECRET,
    {
      algorithms: ['HS256'],
      issuer: 'epe',
      audience: 'epe-api',
    },
  );
  const allowedClaims = ['aud', 'exp', 'iat', 'iss', 'jti', 'sub'];
  const unexpected = Object.keys(decoded)
    .filter(key => !allowedClaims.includes(key));
  if (
    unexpected.length
    || !/^\d+$/.test(String(decoded.sub || ''))
    || !/^[0-9a-f-]{36}$/i.test(String(decoded.jti || ''))
  ) {
    return { json: rejected('TOKEN_INVALID', 'Token claims are invalid') };
  }

  return {
    json: {
      token_valid: true,
      sub: Number(decoded.sub),
      jti: decoded.jti,
      required_roles: requiredRoles,
      required_capability: requiredCapability,
      request: input.request || {},
      rejection: null,
    },
  };
} catch (error) {
  const code = error.name === 'TokenExpiredError'
    ? 'TOKEN_EXPIRED'
    : 'TOKEN_INVALID';
  return { json: rejected(code, 'Token is invalid or expired') };
}
""".strip()

GUARD_IDENTITY_SQL = r"""
=SELECT
  users.id,
  users.full_name,
  users.email,
  users.role,
  users.can_evaluate,
  users.can_be_evaluated,
  users.token_version
FROM performance_db.users users
JOIN performance_db.auth_sessions sessions
  ON sessions.user_id = users.id
  AND sessions.jti = '{{ $json.jti }}'::uuid
  AND sessions.token_version = users.token_version
  AND sessions.revoked_at IS NULL
  AND sessions.expires_at > now()
WHERE users.id = {{ $json.sub }}
LIMIT 1
""".strip()

GUARD_AUTHORIZE = r"""
const parsed = $('Verify JWT').first().json;
const identity = $input.first().json;

if (!parsed.token_valid) {
  return { json: { ...parsed.rejection, request: parsed.request } };
}
if (!identity.id) {
  return {
    json: {
      ok: false,
      status: 401,
      code: 'SESSION_INVALID',
      message: 'Session is invalid or revoked',
      request: parsed.request,
    },
  };
}

if (
  parsed.required_roles.length
  && !parsed.required_roles.includes(String(identity.role))
) {
  return {
    json: {
      ok: false,
      status: 403,
      code: 'ROLE_FORBIDDEN',
      message: 'Required role is missing',
      request: parsed.request,
    },
  };
}

const allowedCapabilities = ['can_evaluate', 'can_be_evaluated'];
if (
  parsed.required_capability
  && (
    !allowedCapabilities.includes(parsed.required_capability)
    || identity[parsed.required_capability] !== true
  )
) {
  return {
    json: {
      ok: false,
      status: 403,
      code: 'CAPABILITY_FORBIDDEN',
      message: 'Required capability is disabled',
      request: parsed.request,
    },
  };
}

return {
  json: {
    ok: true,
    status: 200,
    identity: {
      id: identity.id,
      full_name: identity.full_name,
      email: identity.email,
      role: identity.role,
      can_evaluate: identity.can_evaluate,
      can_be_evaluated: identity.can_be_evaluated,
    },
    request: parsed.request,
  },
};
""".strip()


def build_guard(credential_id: str) -> dict[str, Any]:
    nodes = [
        node(
            "guard-trigger",
            "Guard Input",
            "n8n-nodes-base.executeWorkflowTrigger",
            [-450, 0],
            {},
            type_version=1,
        ),
        node(
            "guard-verify",
            "Verify JWT",
            "n8n-nodes-base.code",
            [-220, 0],
            {"jsCode": GUARD_VERIFY},
        ),
        node(
            "guard-load",
            "Load Live Identity",
            "n8n-nodes-base.postgres",
            [20, 0],
            {
                "operation": "executeQuery",
                "query": GUARD_IDENTITY_SQL,
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "guard-authorize",
            "Authorize",
            "n8n-nodes-base.code",
            [270, 0],
            {"jsCode": GUARD_AUTHORIZE},
        ),
    ]
    connections = {
        "Guard Input": connect("Verify JWT"),
        "Verify JWT": connect("Load Live Identity"),
        "Load Live Identity": connect("Authorize"),
    }
    return workflow("EPE: Auth Guard", nodes, connections)


EMPLOYEES_GUARD_INPUT = r"""
const request = $input.first().json;
return {
  json: {
    authorization: request.headers?.authorization || '',
    required_roles: [],
    required_capability: '',
    request,
  },
};
""".strip()

EMPLOYEES_SQL = r"""
const guard = $input.first().json;
if (!guard.ok) return { json: guard };
const actorId = Number(guard.identity.id);
const actorCanEvaluate = guard.identity.can_evaluate === true || guard.identity.can_evaluate === 't';
return {
  json: {
    ...guard,
    sql: `
      WITH current_period AS (
        SELECT id, status, is_active, evaluation_started_at
        FROM performance_db.evaluation_periods
        WHERE (is_active = true AND status = 'active')
           OR status = 'draft'
        ORDER BY
          CASE WHEN is_active = true AND status = 'active' THEN 0 ELSE 1 END,
          start_date DESC NULLS LAST,
          id DESC
        LIMIT 1
      ),
      -- The campaign period is active AND started (D-0822-1). During the
      -- preparation window current_period is still H1, so actor_is_in_scope
      -- stays truthful, but active_period is empty: no tasks, no flags.
      active_period AS (
        SELECT id
        FROM current_period
        WHERE is_active = true AND status = 'active'
          AND evaluation_started_at IS NOT NULL
      ),
      actor_scope AS (
        SELECT epp.is_in_scope
        FROM current_period cp
        LEFT JOIN performance_db.evaluation_period_participants epp
          ON epp.period_id = cp.id
         AND epp.user_id = ${actorId}
      ),
      scoped AS (
        SELECT
          users.id,
          users.full_name,
          users.email,
          users.job_title,
          users.work_category,
          users.is_project_participant,
          users.manager_id,
          users.has_subordinates,
          departments.name AS department_name,
          grades.code AS grade_code,
          grades.coefficient AS grade_coefficient,
          EXISTS (
            SELECT 1
            FROM performance_db.evaluations self_eval
            WHERE self_eval.subject_id = users.id
              AND self_eval.is_self_evaluation = true
              AND self_eval.period_id = ap.id
          ) AS has_self_review,
          EXISTS (
            SELECT 1
            FROM performance_db.evaluations upward_eval
            WHERE upward_eval.evaluator_id = users.id
              AND upward_eval.subject_id = ${actorId}
              AND upward_eval.evaluation_source = 'subordinate'
              AND upward_eval.period_id = ap.id
          ) AS has_evaluated_manager,
          EXISTS (
            SELECT 1
            FROM performance_db.evaluations actor_eval
            WHERE actor_eval.evaluator_id = ${actorId}
              AND actor_eval.subject_id = users.id
              AND actor_eval.is_self_evaluation = false
              AND actor_eval.period_id = ap.id
          ) AS evaluated_by_actor
        FROM performance_db.users users
        LEFT JOIN performance_db.departments departments
          ON users.department_id = departments.id
        LEFT JOIN performance_db.grades grades
          ON users.grade_id = grades.id
        JOIN active_period ap ON true
        JOIN performance_db.evaluation_period_participants epp
          ON epp.period_id = ap.id
         AND epp.user_id = users.id
         AND epp.is_in_scope = true
        WHERE users.manager_id = ${actorId}
          AND ${actorCanEvaluate}
          AND COALESCE((SELECT is_in_scope FROM actor_scope), false)
      )
      SELECT
        EXISTS(SELECT 1 FROM active_period) AS campaign_active,
        (SELECT id FROM current_period) AS current_period_id,
        (SELECT status FROM current_period) AS current_period_status,
        EXISTS(
          SELECT 1 FROM current_period
          WHERE is_active = true AND status = 'active'
            AND evaluation_started_at IS NULL
        ) AS period_in_preparation,
        CASE
          WHEN EXISTS(SELECT 1 FROM current_period)
          THEN COALESCE((SELECT is_in_scope FROM actor_scope), false)
          ELSE NULL
        END AS actor_is_in_scope,
        COALESCE(
          (SELECT json_agg(row_to_json(scoped) ORDER BY scoped.full_name) FROM scoped),
          '[]'::json
        ) AS employees
    `,
  },
};
""".strip()

EMPLOYEES_FORMAT = r"""
const guard = $('Run Auth Guard').first().json;
if (!guard.ok) {
  return {
    json: {
      http_status: guard.status,
      body: {
        success: false,
        error: guard.code,
        message: guard.message,
      },
    },
  };
}

const row = $input.first().json || {};
let employees = row.employees || [];
if (typeof employees === 'string') {
  try { employees = JSON.parse(employees); } catch { employees = []; }
}
if (!Array.isArray(employees)) employees = [];
const canSeeGradeCoefficient = ['admin', 'c_level'].includes(String(guard.identity.role || ''));
employees = employees.map(employee => {
  const safeEmployee = { ...employee };
  if (!canSeeGradeCoefficient) delete safeEmployee.grade_coefficient;
  return safeEmployee;
});
// campaign_active now means "active AND started" (D-0822-1). An active period
// that has not been started reports campaign_active=false with
// period_in_preparation=true, so the client can say why there are no tasks.
const campaignActive = row.campaign_active === true || row.campaign_active === 't';
const periodInPreparation = row.period_in_preparation === true || row.period_in_preparation === 't';
const actorIsInScope = row.actor_is_in_scope === null || row.actor_is_in_scope === undefined
  ? null
  : row.actor_is_in_scope === true || row.actor_is_in_scope === 't';

return {
  json: {
    http_status: 200,
    body: {
      success: true,
      actor_user_id: guard.identity.id,
      campaign_active: campaignActive,
      period_in_preparation: periodInPreparation,
      current_period_id: row.current_period_id || null,
      current_period_status: row.current_period_status || null,
      actor_is_in_scope: actorIsInScope,
      data: employees,
    },
  },
};
""".strip()


def build_protected_employees(
    credential_id: str,
    guard_workflow_id: str,
) -> dict[str, Any]:
    nodes = [
        node(
            "employees-webhook",
            "Webhook",
            "n8n-nodes-base.webhook",
            [-700, 0],
            {
                "httpMethod": "GET",
                "path": "api/employees",
                "responseMode": "responseNode",
                "options": {},
            },
            type_version=2.1,
            webhook_id="ba63a094-956c-49a9-8284-b06a1d243d37",
        ),
        node(
            "employees-guard-input",
            "Prepare Guard Input",
            "n8n-nodes-base.code",
            [-480, 0],
            {"jsCode": EMPLOYEES_GUARD_INPUT},
        ),
        node(
            "employees-run-guard",
            "Run Auth Guard",
            "n8n-nodes-base.executeWorkflow",
            [-250, 0],
            {
                "workflowId": guard_workflow_id,
                "options": {},
            },
            type_version=1,
        ),
        node(
            "employees-build",
            "Build Identity-Bound Query",
            "n8n-nodes-base.code",
            [0, 0],
            {"jsCode": EMPLOYEES_SQL},
        ),
        node(
            "employees-query",
            "Load Actor Subordinates",
            "n8n-nodes-base.postgres",
            [250, 0],
            {
                "operation": "executeQuery",
                "query": (
                    "={{ $json.ok ? $json.sql "
                    ": 'SELECT NULL::integer AS id WHERE false' }}"
                ),
                "options": {},
            },
            type_version=2.6,
            credentials=postgres_credentials(credential_id),
            always_output=True,
        ),
        node(
            "employees-format",
            "Format Response",
            "n8n-nodes-base.code",
            [500, 0],
            {"jsCode": EMPLOYEES_FORMAT},
        ),
        node(
            "employees-respond",
            "Respond",
            "n8n-nodes-base.respondToWebhook",
            [740, 0],
            {
                "respondWith": "json",
                "responseBody": "={{ $json.body }}",
                "options": {
                    "responseCode": "={{ $json.http_status }}",
                },
            },
            type_version=1.4,
        ),
    ]
    connections = {
        "Webhook": connect("Prepare Guard Input"),
        "Prepare Guard Input": connect("Run Auth Guard"),
        "Run Auth Guard": connect("Build Identity-Bound Query"),
        "Build Identity-Bound Query": connect("Load Actor Subordinates"),
        "Load Actor Subordinates": connect("Format Response"),
        "Format Response": connect("Respond"),
    }
    return workflow(
        "API: Get Employees (Smart Role Based)",
        nodes,
        connections,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--postgres-credential-id",
        default=POSTGRES_CREDENTIAL_PLACEHOLDER,
    )
    parser.add_argument(
        "--guard-workflow-id",
        default=GUARD_WORKFLOW_PLACEHOLDER,
    )
    parser.add_argument(
        "--smtp-credential-id",
        default=SMTP_CREDENTIAL_ID,
    )
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)

    workflows = {
        "login.json": build_login(args.postgres_credential_id),
        "register.json": build_register(args.postgres_credential_id),
        "request-password-reset.json": build_reset_request(
            args.postgres_credential_id,
            args.smtp_credential_id,
        ),
        "reset-password.json": build_reset_password(
            args.postgres_credential_id
        ),
        "auth-guard.json": build_guard(args.postgres_credential_id),
        "protected-employees.json": build_protected_employees(
            args.postgres_credential_id,
            args.guard_workflow_id,
        ),
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
                "postgres_credential_id": args.postgres_credential_id,
                "guard_workflow_id": args.guard_workflow_id,
                "smtp_credential_id": args.smtp_credential_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
