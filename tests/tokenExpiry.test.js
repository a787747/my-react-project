import test from 'node:test';
import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import { getTokenExpiryMs } from '../src/utils/tokenExpiry.js';

const encode = (value) => Buffer.from(JSON.stringify(value))
  .toString('base64url');

test('reads exp from a JWT payload for UI warnings', () => {
  const token = `${encode({ alg: 'HS256' })}.${encode({ exp: 1234 })}.signature`;
  assert.equal(getTokenExpiryMs(token), 1_234_000);
});

test('returns null for malformed or expiry-free tokens', () => {
  assert.equal(getTokenExpiryMs('not-a-jwt'), null);
  assert.equal(
    getTokenExpiryMs(`${encode({})}.${encode({ sub: '1' })}.signature`),
    null,
  );
  assert.equal(getTokenExpiryMs(null), null);
});
