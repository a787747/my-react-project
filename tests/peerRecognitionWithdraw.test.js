/**
 * Static checks for the peer-recognition withdraw route.
 * Generates the working-tree builder and asserts the withdraw path exists,
 * deletes by token actor, and does not touch a campaign table.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = mkdtempSync(join(tmpdir(), 'epe-recog-wd-'));

execSync(
  `python3 scripts/build_route_guard_workflows.py --output-directory "${OUT_DIR}"`,
  { cwd: REPO_ROOT },
);

const wf = JSON.parse(readFileSync(join(OUT_DIR, 'peer-recognition.json'), 'utf8'));
const webhooks = (wf.nodes || []).filter((n) => n.type === 'n8n-nodes-base.webhook');
const js = (wf.nodes || [])
  .filter((n) => n.type === 'n8n-nodes-base.code')
  .map((n) => n.parameters?.jsCode || '')
  .join('\n');

test('peer-recognition exposes form, save, list and withdraw', () => {
  const paths = webhooks
    .map((n) => `${n.parameters.httpMethod} ${n.parameters.path}`)
    .sort();
  assert.deepEqual(paths, [
    'GET api/recognition/form',
    'GET api/recognition/list',
    'POST api/recognition/save',
    'POST api/recognition/withdraw',
  ]);
});

test('withdraw deletes the actor\'s own row and refuses a closed period', () => {
  assert.match(js, /DELETE FROM performance_db\.peer_recognitions/);
  assert.match(js, /r\.author_id = \$\{actorId\}/);
  assert.match(js, /RECOGNITION_NOT_OWN/);
  assert.match(js, /NO_ACTIVE_PERIOD/);
  assert.match(js, /Отметка снята/);
  assert.doesNotMatch(js, /DELETE FROM performance_db\.evaluations/);
  assert.doesNotMatch(js, /UPDATE performance_db\.evaluation_scores/);
  assert.doesNotMatch(js, /INSERT INTO performance_db\.period_results/);
});

test('frontend page keeps the owner\'s three intro sentences and adds the disclosure verbatim', () => {
  const page = readFileSync(join(REPO_ROOT, 'src/pages/PeerRecognition.jsx'), 'utf8');
  assert.match(
    page,
    /Необязательно\. Можно отметить одного человека, чья помощь реально повлияла на вашу работу или на результат для клиента\./,
  );
  assert.match(
    page,
    /Это не голосование и не рейтинг\. Количество отметок нигде не подсчитывается и ни на чью премию не влияет\./,
  );
  assert.match(
    page,
    /Не нужно отмечать за то, что с человеком приятно работать или он выручил по мелочи\./,
  );
  assert.match(
    page,
    /Отметку читает только высшее руководство компании\. Отмеченный человек и его руководитель её не видят\./,
  );
  assert.match(page, /Снять отметку\? Текст будет удалён, и вы снова будете без отметки\./);
  const hook = readFileSync(join(REPO_ROOT, 'src/hooks/usePeerRecognition.js'), 'utf8');
  assert.match(hook, /RECOGNITION_WITHDRAW/);
});
