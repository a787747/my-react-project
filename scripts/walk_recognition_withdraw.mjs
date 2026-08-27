#!/usr/bin/env node
/**
 * Browser walkthrough for PEER_RECOGNITION_DISCLOSURE_AND_WITHDRAW.
 * Drives headless Chrome via CDP against the local vite → stand proxy.
 * Stand-local passwords only. Live is never opened.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const BASE = process.env.EPE_WALK_BASE || 'http://localhost:5199';
const PASS = process.env.EPE_STAND_PASSWORD || 'Wd2026-Recog!';
const OUT = process.env.EPE_WALK_OUT
  || join(process.cwd(), 'backups/2026-08-27-peer-recognition/walk');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9223;

const ACTORS = {
  employee: { email: 'oksana@sedamedical.com', name: 'Oksana' },
  other: { email: 'esenova@sedamedical.com', name: 'Aysoltan' },
  c_level: { email: 'jemal@sedamedical.com', name: 'Jemal' },
  nominee: { email: 'arslan@sedamedical.com', name: 'Arslan' },
  manager: { email: 'yelena@sedamedical.com', name: 'Yelena' },
  admin: { email: 'alexander@sedamedical.com', name: 'Alexander' },
};

const DISCLOSURE =
  'Отметку читает только высшее руководство компании. Отмеченный человек и его руководитель её не видят.';
const TEXTS = {
  sit: 'Срочная поставка вечером UI-70-SIT',
  act: 'Нашёл ошибку в накладной UI-70-ACT',
  out: 'Клиент получил комплект UI-70-OUT',
};
const TEXTS2 = {
  sit: 'Сложный монтаж UI-70B-SIT',
  act: 'Довёл пусконаладку UI-70B-ACT',
  out: 'Сдали без переноса UI-70B-OUT',
};

mkdirSync(OUT, { recursive: true });
const report = { steps: [], failed: 0 };

function log(name, ok, extra = {}) {
  report.steps.push({ step: name, pass: !!ok, ...extra });
  console.log(`${ok ? 'ok   ' : 'FAIL '} ${name}${extra.note ? ' — ' + extra.note : ''}`);
  if (!ok) report.failed += 1;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    };
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP timeout ${method}`));
        }
      }, 30000);
    });
  }
  async eval(expression, awaitPromise = false) {
    const r = await this.send('Runtime.evaluate', {
      expression, awaitPromise, returnByValue: true,
    });
    if (r.exceptionDetails) {
      throw new Error(r.exceptionDetails.text || 'eval exception');
    }
    return r.result?.value;
  }
}

async function connectChrome(child) {
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const targets = await res.json();
      const page = (targets || []).find((t) => t.type === 'page') || targets[0];
      if (!page?.webSocketDebuggerUrl) throw new Error('no page target');
      const ws = new WebSocket(page.webSocketDebuggerUrl);
      await new Promise((resolve, reject) => {
        ws.onopen = resolve;
        ws.onerror = reject;
      });
      return new Cdp(ws);
    } catch {
      await sleep(250);
    }
  }
  child.kill();
  throw new Error('Chrome CDP did not come up');
}

async function waitText(cdp, needle, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const text = await cdp.eval('document.body ? document.body.innerText : ""');
    if (text && text.includes(needle)) return text;
    await sleep(250);
  }
  throw new Error(`timeout waiting for: ${needle}`);
}

async function screenshot(cdp, name) {
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(OUT, `${name}.png`), Buffer.from(data, 'base64'));
}

async function navigate(cdp, url) {
  await cdp.send('Page.navigate', { url });
  const start = Date.now();
  while (Date.now() - start < 20000) {
    try {
      const href = await cdp.eval('location.href');
      const ready = await cdp.eval('document.readyState');
      if (typeof href === 'string' && href.startsWith(url.split('?')[0]) && ready === 'complete') {
        await sleep(300);
        return;
      }
    } catch {
      // frame not ready yet
    }
    await sleep(250);
  }
  let href = '';
  let body = '';
  try {
    href = await cdp.eval('location.href');
    body = await cdp.eval('document.body && document.body.innerText.slice(0, 400)');
  } catch { /* ignore */ }
  throw new Error(`navigate timeout ${url} href=${href} body=${JSON.stringify(body)}`);
}

async function login(cdp, email) {
  await navigate(cdp, `${BASE}/login`);
  await waitText(cdp, 'Пароль', 20000);
  await sleep(400);
  await cdp.eval(`
    const email = document.querySelector('#email, input[type="email"], input[name="email"]');
    const pass = document.querySelector('#password, input[type="password"], input[name="password"]');
    const set = (el, v) => {
      const last = el.value;
      el.value = v;
      const tracker = el._valueTracker;
      if (tracker) tracker.setValue(last);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    set(email, ${JSON.stringify(email)});
    set(pass, ${JSON.stringify(PASS)});
    const btn = document.querySelector('button[type="submit"]');
    btn.click();
  `);
  await waitText(cdp, 'Отметить коллегу', 20000);
}

async function logout(cdp) {
  await cdp.eval(`
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    sessionStorage.clear();
  `);
}

async function go(cdp, path, waitFor) {
  await navigate(cdp, `${BASE}${path}`);
  if (waitFor) await waitText(cdp, waitFor, 20000);
}

/** The admin list heading is in the DOM immediately; the cards arrive later. */
async function waitListSettled(cdp) {
  const start = Date.now();
  while (Date.now() - start < 20000) {
    const text = await pageText(cdp);
    const loading = text.includes('Загрузка...');
    const ready = text.includes('отметил(а)')
      || text.includes('Пока никто никого не отметил')
      || text.includes('Не удалось загрузить отметки');
    if (!loading && ready) return text;
    await sleep(250);
  }
  throw new Error('admin list did not settle');
}

async function pageText(cdp) {
  return cdp.eval('document.body ? document.body.innerText : ""');
}

async function main() {
  const profile = join(tmpdir(), `epe-chrome-wd-${Date.now()}`);
  const child = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,1600',
    'about:blank',
  ], { stdio: 'ignore' });

  const cdp = await connectChrome(child);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  try {
    // ── 1. Oksana: disclosure before fields, then nominate ───────────────
    await login(cdp, ACTORS.employee.email);
    await go(cdp, '/recognition', 'Кто помог вам в этом полугодии');
    const formText = await pageText(cdp);
    const discAt = formText.indexOf(DISCLOSURE);
    const fieldsAt = formText.indexOf('Кого вы отмечаете');
    log('disclosure line present verbatim', discAt >= 0);
    log('disclosure appears before the fields', discAt >= 0 && fieldsAt > discAt,
      { discAt, fieldsAt });
    const intro1 = 'Необязательно. Можно отметить одного человека';
    log('existing intro texts still present', formText.includes(intro1)
      && formText.includes('Это не голосование и не рейтинг')
      && formText.includes('Не нужно отмечать за то, что с человеком приятно работать'));
    await screenshot(cdp, '01-oksana-disclosure');

    await cdp.eval(`
      const search = document.querySelector('input[aria-label="Поиск коллеги"]');
      const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
      proto.set.call(search, 'Arslan');
      search.dispatchEvent(new Event('input', { bubbles: true }));
    `);
    await sleep(300);
    await cdp.eval(`
      const btn = [...document.querySelectorAll('button')]
        .find(b => (b.innerText || '').includes('Arslan Annayev'));
      if (!btn) throw new Error('Arslan not in picker');
      btn.click();
    `);
    await sleep(200);
    await cdp.eval(`
      const set = (el, v) => {
        const proto = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
        proto.set.call(el, v);
        el.dispatchEvent(new Event('input', { bubbles: true }));
      };
      set(document.querySelector('#recognition-situation'), ${JSON.stringify(TEXTS.sit)});
      set(document.querySelector('#recognition-action'), ${JSON.stringify(TEXTS.act)});
      set(document.querySelector('#recognition-outcome'), ${JSON.stringify(TEXTS.out)});
      document.querySelector('button[type="submit"]').click();
    `);
    await waitText(cdp, 'Вы уже отметили', 20000);
    await screenshot(cdp, '02-oksana-nominated');
    log('oksana nominated Arslan', (await pageText(cdp)).includes('Arslan Annayev'));

    // ── 2. C-level sees it ──────────────────────────────────────────────
    await logout(cdp);
    await login(cdp, ACTORS.c_level.email);
    await go(cdp, '/admin/recognition', 'Отметки коллег');
    const listBefore = await waitListSettled(cdp);
    log('c_level sees oksana nomination before withdraw',
      listBefore.includes(TEXTS.sit) && listBefore.includes('Oksana'));
    log('c_level still sees the other employee nomination',
      listBefore.includes('UI-31-SIT'));
    log('c_level list has no tally words',
      !/\d+\s+(отметок|отметки|раз|шт)\b/.test(listBefore));
    await screenshot(cdp, '03-clevel-before-withdraw');

    // ── 3. Oksana withdraws ─────────────────────────────────────────────
    await logout(cdp);
    await login(cdp, ACTORS.employee.email);
    await go(cdp, '/recognition', 'Снять отметку');
    await cdp.eval('window.confirm = () => true;');
    await cdp.eval(`
      const btn = [...document.querySelectorAll('button')]
        .find(b => (b.innerText || '').trim() === 'Снять отметку');
      if (!btn) throw new Error('withdraw button missing');
      btn.click();
    `);
    await sleep(1500);
    const afterWd = await pageText(cdp);
    log('after withdraw: no «Вы уже отметили»', !afterWd.includes('Вы уже отметили'));
    log('after withdraw: submit is «Отметить», not replace',
      afterWd.includes('Отметить') && !afterWd.includes('Заменить отметку'));
    await screenshot(cdp, '04-oksana-after-withdraw');

    // ── 4. C-level no longer sees oksana's text ─────────────────────────
    await logout(cdp);
    await login(cdp, ACTORS.c_level.email);
    await go(cdp, '/admin/recognition', 'Отметки коллег');
    const listAfter = await waitListSettled(cdp);
    log('c_level does not see withdrawn texts',
      !listAfter.includes(TEXTS.sit) && !listAfter.includes('UI-70-SIT'));
    log('c_level still sees the other employee nomination',
      listAfter.includes('UI-31-SIT'));
    await screenshot(cdp, '05-clevel-after-withdraw');

    // ── 5. Oksana nominates again ───────────────────────────────────────
    await logout(cdp);
    await login(cdp, ACTORS.employee.email);
    await go(cdp, '/recognition', 'Кто помог вам в этом полугодии');
    await cdp.eval(`
      const search = document.querySelector('input[aria-label="Поиск коллеги"]');
      const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
      proto.set.call(search, 'Anton');
      search.dispatchEvent(new Event('input', { bubbles: true }));
    `);
    await sleep(300);
    await cdp.eval(`
      const btn = [...document.querySelectorAll('button')]
        .find(b => (b.innerText || '').includes('Anton Markin'));
      if (!btn) throw new Error('Anton not in picker');
      btn.click();
    `);
    await sleep(200);
    await cdp.eval(`
      const set = (el, v) => {
        const proto = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
        proto.set.call(el, v);
        el.dispatchEvent(new Event('input', { bubbles: true }));
      };
      set(document.querySelector('#recognition-situation'), ${JSON.stringify(TEXTS2.sit)});
      set(document.querySelector('#recognition-action'), ${JSON.stringify(TEXTS2.act)});
      set(document.querySelector('#recognition-outcome'), ${JSON.stringify(TEXTS2.out)});
      document.querySelector('button[type="submit"]').click();
    `);
    await waitText(cdp, 'Вы уже отметили', 20000);
    const again = await pageText(cdp);
    log('oksana nominated again — exactly one shown',
      again.includes('Anton Markin') && (again.match(/Вы уже отметили/g) || []).length === 1);
    await screenshot(cdp, '06-oksana-renominated');

    // ── 6. Nominee / manager / admin surfaces have no trace ─────────────
    const needles = ['UI-70-SIT', 'UI-70B-SIT', 'UI-31-SIT', 'Снять отметку'];
    async function clean(who, email, paths) {
      await logout(cdp);
      await login(cdp, email);
      const hits = [];
      for (const path of paths) {
        await go(cdp, path, null);
        await sleep(600);
        const text = await pageText(cdp);
        const found = needles.filter((n) => text.includes(n));
        if (found.length) hits.push({ path, found });
        await screenshot(cdp, `07-${who}${path.replaceAll('/', '-') || '-root'}`);
      }
      log(`${who} surfaces contain no nomination text`, hits.length === 0, { hits });
    }
    await clean('nominee', ACTORS.nominee.email, ['/profile', '/history', '/welcome']);
    await clean('manager', ACTORS.manager.email, ['/dashboard', '/team', '/team-scores']);
    await clean('admin', ACTORS.admin.email, [
      '/admin/users', '/admin/periods', '/admin', '/admin/scoring',
      '/analytics', '/admin/all-evaluations', '/admin/evaluations-matrix',
      '/admin/final-scores', '/admin/bonus-calculation', '/admin/annual-rollup',
      '/admin/score-calculator', '/dashboard', '/team-scores', '/profile', '/history',
    ]);
  } finally {
    try { cdp.ws.close(); } catch { /* ignore */ }
    child.kill();
  }

  report.verdict = report.failed === 0 ? 'PASS' : 'FAIL';
  writeFileSync(join(OUT, 'walk.json'), JSON.stringify(report, null, 2));
  console.log(`\n${report.verdict}  (${report.steps.length} steps, ${report.failed} failed)`);
  process.exit(report.failed === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
