import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = mkdtempSync(join(tmpdir(), 'epe-talk-'));
execSync(`python3 scripts/build_route_guard_workflows.py --output-directory "${OUT}"`, {
  cwd: ROOT,
});

const workflow = JSON.parse(readFileSync(join(OUT, 'talk-channel.json'), 'utf8'));
const migration = readFileSync(join(ROOT, 'migrations/019_add_management_talk.sql'), 'utf8');
const concept = readFileSync(join(ROOT, 'CONVERSATION_CHANNEL_CONCEPT.md'), 'utf8');
const page = readFileSync(join(ROOT, 'src/pages/TalkChannel.jsx'), 'utf8');
const copy = readFileSync(join(ROOT, 'src/content/talkCopy.js'), 'utf8');
const app = readFileSync(join(ROOT, 'src/App.jsx'), 'utf8');
const js = workflow.nodes
  .filter((node) => node.type === 'n8n-nodes-base.code')
  .map((node) => node.parameters?.jsCode || '')
  .join('\n');

test('TALK exposes four guarded routes and reader is admin alone', () => {
  const paths = workflow.nodes
    .filter((node) => node.type === 'n8n-nodes-base.webhook')
    .map((node) => `${node.parameters.httpMethod} ${node.parameters.path}`)
    .sort();
  assert.deepEqual(paths, [
    'GET api/talk/form',
    'GET api/talk/list',
    'POST api/talk/save',
    'POST api/talk/withdraw',
  ]);
  const listGuard = workflow.nodes.find((node) => node.name === 'Prepare Guard Input LIST');
  assert.match(listGuard.parameters.jsCode, /required_roles: \["admin"\]/);
  assert.match(app, /path="\/admin\/talk"[\s\S]*?<AdminOnlyRoute/);
});

test('migration is wave-based, structured, and isolated from campaign tables', () => {
  const ddl = migration.replace(/^--.*$/gm, '');
  assert.doesNotMatch(ddl, /^\s*period_id\s+/im);
  assert.doesNotMatch(migration, /\b(score|weight|coefficient|rating|rank|count)\w*\s+(numeric|decimal|real|double)/i);
  assert.doesNotMatch(
    migration,
    /REFERENCES\s+performance_db\.(evaluations|evaluation_scores|score_corrections|period_results)/i,
  );
  assert.match(migration, /responder_id\s+integer[\s\S]*REFERENCES performance_db\.users\(id\)/);
  assert.match(migration, /counterpart_id\s+integer[\s\S]*REFERENCES performance_db\.users\(id\)/);
  assert.match(migration, /PRIMARY KEY \(wave_id, responder_id\)/);
  assert.match(migration, /BEGIN;[\s\S]*COMMIT;/);
});

test('save is an upsert, close is clock-driven, and topic 10 alone excludes own manager', () => {
  assert.match(js, /ON CONFLICT \(wave_id, responder_id\) DO UPDATE/);
  assert.match(js, /clock_timestamp\(\) BETWEEN w\.opens_at AND w\.closes_at/);
  assert.match(js, /TALK_WAVE_CLOSED/);
  assert.match(js, /prev\.topic_key === 't10_manager'/);
  assert.match(js, /topics 9, 11 and 12 deliberately may concern anyone/);
  assert.match(js, /r\.counterpart_id = a\.manager_id/);
  assert.match(js, /DELETE FROM performance_db\.management_talk_responses/);
  assert.doesNotMatch(js, /performance_db\.(evaluations|evaluation_scores|score_corrections|period_results)/);
});

test('normative topics keep their exact order and form has no free-text control', () => {
  const expected = [
    'Хочу понять позицию руководства по ситуации или решению',
    'Нагрузка и объём работы',
    'Ресурсы или организация работы на проекте',
    'Моя роль, ответственность или рабочие приоритеты',
    'Карьерный рост и развитие',
    'Обучение и развитие компетенций',
    'Оплата или признание моего вклада',
    'Есть идея или предложение по улучшению работы',
    'Отношения в команде, конфликт или токсичная атмосфера',
    'Действия моего непосредственного руководителя',
    'Считаю ситуацию или решение несправедливым',
    'Есть личный вопрос, который хочу обсудить напрямую',
  ];
  const positions = expected.map((label) => migration.indexOf(label));
  assert.ok(positions.every((position) => position >= 0));
  assert.deepEqual([...positions].sort((a, b) => a - b), positions);
  assert.doesNotMatch(page, /<textarea|type="text"/);
});

test('deadline is rendered from closes_at and agrees with approved copy', () => {
  assert.match(migration, /2026-09-10 23:59:59\.999999\+05:00/);
  assert.match(concept, /Ответить можно до 10 сентября\./);
  assert.match(page, /Ответить можно до \{wave\.deadline_text\}\./);
  assert.doesNotMatch(page, /Ответить можно до 10 сентября/);
  assert.match(js, /deadline_text/);
});

test('employee explanation uses the revised owner copy verbatim', () => {
  assert.match(
    copy,
    /Сейчас во многих направлениях компании сохраняется высокая рабочая нагрузка: продолжаются проекты оснащения клиник, поставки расходных материалов, установка оборудования, обучение конечных пользователей и другие текущие задачи\./,
  );
  assert.match(
    copy,
    /Этот раздел не является частью процедуры оценки сотрудников и рассматривается отдельно от неё\./,
  );
  assert.doesNotMatch(copy, /Сейчас у многих высокая нагрузка: проекты оснащения клиник в самых острых фазах/);
  assert.doesNotMatch(copy, /Открытый и добросовестный разговор сам по себе/);
});

test('admin denominator separates registered unanswered from never registered', () => {
  assert.match(js, /registered_unanswered/);
  assert.match(js, /never_registered/);
  assert.match(js, /u\.password_hash IS NOT NULL/);
  assert.match(copy, /Ответ получен|Поговорить с руководством/);
});

test('counterpart selector is restricted to the owner-approved user ids', () => {
  assert.match(js, /u\.id IN \(2,18,21,40,47,61\)/);
  assert.doesNotMatch(js, /'role', u\.role/);
});
