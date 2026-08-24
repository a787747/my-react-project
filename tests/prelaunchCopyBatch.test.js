/**
 * PRELAUNCH_COPY_BATCH_2026-08-24
 *
 * Pins the four frontend copy/gate bugs (034–037) and the 401 session-expiry
 * interceptor that must stay unchanged when handleApiError starts passing the
 * server message through.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { handleApiError, isAuthError } from '../src/utils/errorHandler.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');

const card = read('src/components/self-review/SelfReviewStatusCard.jsx');
const welcome = read('src/pages/Welcome.jsx');
const login = read('src/pages/Login.jsx');
const session = read('src/components/SessionExpiryWarning.jsx');
const managerEval = read('src/pages/ManagerEvaluation.jsx');
const adminUsers = read('src/pages/AdminUsers.jsx');
const userTable = read('src/components/admin/UserTable.jsx');
const client = read('src/api/client.js');
const errorHandlerSrc = read('src/utils/errorHandler.js');

const apiError = (status, data) => ({ response: { status, data } });

// ── BUG-035: 401 / 403 / 429 pass the server message through ───────────────

test('handleApiError surfaces the server message on 401, 403 and 429', () => {
  assert.equal(
    handleApiError(apiError(401, { message: 'TOKEN_EXPIRED' })),
    'TOKEN_EXPIRED',
  );
  assert.equal(
    handleApiError(apiError(403, { message: 'CAPABILITY_FORBIDDEN' })),
    'CAPABILITY_FORBIDDEN',
  );
  assert.equal(
    handleApiError(apiError(429, { message: 'RATE_LIMITED' })),
    'RATE_LIMITED',
  );
});

test('handleApiError keeps the fixed Russian fallback when the server sent no message', () => {
  assert.equal(
    handleApiError(apiError(401, {})),
    'Сессия истекла. Пожалуйста, войдите снова',
  );
  assert.equal(
    handleApiError(apiError(403, {})),
    'Доступ запрещен. Недостаточно прав',
  );
  assert.equal(
    handleApiError(apiError(429, {})),
    'Слишком много запросов. Попробуйте позже',
  );
});

test('401 session-expiry / redirect behaviour is unchanged', () => {
  assert.equal(isAuthError(apiError(401, { message: 'anything' })), true);
  assert.equal(isAuthError(apiError(403, { message: 'CAPABILITY_FORBIDDEN' })), false);
  assert.match(errorHandlerSrc, /return error\?\.response\?\.status === 401;/);
  assert.match(client, /if \(isAuthError\(error\)\) \{/);
  assert.match(client, /localStorage\.removeItem\('user'\);/);
  assert.match(client, /localStorage\.removeItem\('token'\);/);
  assert.match(client, /window\.location\.href = '\/login'/);
  assert.doesNotMatch(
    client,
    /localStorage\.removeItem\('epe:evaluation-draft/,
    '401 must not sweep draft keys (D-0820-15)',
  );
});

// ── BUG-036: button gone; five strings corrected ───────────────────────────

test('SelfReviewStatusCard no longer offers the mid-period add-criteria control', () => {
  assert.doesNotMatch(card, /Оценить новые критерии/);
  assert.doesNotMatch(card, /Появились новые критерии оценки/);
  assert.match(card, /if \(hasReview\) \{/);
});

test('Welcome visibility sentence is the owner wording (D-0824-3)', () => {
  assert.match(
    welcome,
    /Оценка вашего менеджера остается <strong>анонимной<\/strong> - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса\. Все данные видят только C-level менеджеры\./,
  );
  assert.match(
    welcome,
    /Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности\./,
  );
  assert.doesNotMatch(welcome, /остальные результаты откроются отдельным решением/);
});

test('Welcome uses the real criterion title', () => {
  assert.doesNotMatch(welcome, /Критерий для оценки руководителя/);
  assert.match(welcome, /Качество управления и развитие команды/);
});

test('C-level / admin see a role-appropriate no-manager notice', () => {
  assert.match(managerEval, /isCLevelOrAdmin/);
  assert.match(managerEval, /Оценка руководителя не предусмотрена/);
  assert.match(
    managerEval,
    /Для руководителей C-level и администратора оценка непосредственного руководителя/,
  );
  assert.match(managerEval, /Руководитель не назначен/);
});

test('draft notice says the draft is browser-local and expires in 7 days', () => {
  assert.match(
    session,
    /незавершённая оценка сохранится в этом браузере и истечёт через 7 дней/,
  );
  assert.doesNotMatch(session, /сохранится локально\./);
});

test('login placeholder matches the @sedamedical.com registration rule', () => {
  assert.match(login, /placeholder="name@sedamedical.com"/);
  assert.doesNotMatch(login, /name@company\.com/);
});

// ── BUG-037: create sits behind canManage ──────────────────────────────────

test('«Создать период» is behind the same canManage gate as the other write controls', () => {
  const periods = read('src/pages/AdminPeriods.jsx');
  assert.match(periods, /\{canManage && \(\s*<button[\s\S]{0,400}Создать период/);
});

// ── BUG-034: no unhandled rejection; circles removed ───────────────────────

test('AdminUsers no longer calls an undeclared setLoadingStatuses', () => {
  assert.doesNotMatch(adminUsers, /setLoadingStatuses/);
  assert.doesNotMatch(adminUsers, /HR_EVALUATION_STATUS/);
  assert.doesNotMatch(adminUsers, /CHECK_SELF_REVIEWS/);
  assert.match(adminUsers, /showEvaluationStatus=\{false\}/);
  assert.match(userTable, /showEvaluationStatus = true/);
});
