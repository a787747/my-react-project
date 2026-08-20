import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

function loadWorkflow(filename) {
  return JSON.parse(readFileSync(join(ROOT, 'n8n_workflows', filename), 'utf8'));
}

function allJs(wf) {
  return (wf.nodes || [])
    .filter((n) => n.type === 'n8n-nodes-base.code')
    .map((n) => n.parameters?.jsCode || '')
    .join('\n');
}

function allSql(wf) {
  return (wf.nodes || [])
    .filter((n) => n.type === 'n8n-nodes-base.postgres')
    .map((n) => n.parameters?.query || '')
    .join('\n');
}

test('send-verification-code enforces a 60-second resend cooldown per email', () => {
  const wf = loadWorkflow('API_ Send Verification Code.json');
  const js = allJs(wf);
  const sql = allSql(wf);
  assert.ok(
    sql.includes('last_code_at_ms') && sql.includes('email_verification_codes'),
    'must read the latest verification-code timestamp for the email',
  );
  assert.ok(
    js.includes('resend_cooldown') && js.includes('60 * 1000'),
    'must reject a resend inside a 60-second window',
  );
});

test('verify-invite throttles to 600 requests per IP per 5 minutes', () => {
  const wf = loadWorkflow('API_ Verify Invite.json');
  const js = allJs(wf);
  const sql = allSql(wf);
  assert.ok(
    sql.includes('epe-throttle:verify-invite:') && sql.includes("interval '5 minutes'"),
    'must persist a per-IP 5-minute window',
  );
  assert.ok(
    js.includes('RATE_LIMITED') && js.includes('throttleCount > 600'),
    'must reject a 601st request inside the window',
  );
  assert.equal(js.includes('throttleCount > 30'), false);
});
