import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const apiConfig = readFileSync(join(root, 'src/config/api.js'), 'utf8');
const apiClient = readFileSync(join(root, 'src/api/client.js'), 'utf8');

test('API endpoint constants own the same-origin webhook prefix', () => {
  assert.match(
    apiConfig,
    /const API_BASE_URL = import\.meta\.env\.VITE_API_URL \|\| '\/webhook'/,
  );
  assert.match(apiConfig, /CRITERIA: `\$\{API_BASE_URL\}\/api\/criteria`/);
});

test('shared axios client does not prepend API_BASE_URL a second time', () => {
  assert.doesNotMatch(apiClient, /baseURL\s*:/);
  assert.doesNotMatch(apiClient, /import\s+\{\s*API_BASE_URL\s*\}/);
});
