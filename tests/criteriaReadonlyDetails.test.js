/**
 * CRITERIA_READONLY_DETAILS — a reader of /admin can open a criterion and
 * read its description plus the ten level texts without any write control.
 * The texts come from the manage-criteria GET payload (c.*); this brief
 * does not add fields to that payload.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const read = (p) => readFileSync(join(REPO_ROOT, p), "utf8");

const table = read("src/components/admin/CriteriaTable.jsx");
const readout = read("src/components/admin/CriteriaReadout.jsx");
const form = read("src/components/admin/CriteriaForm.jsx");
const settings = read("src/pages/AdminSettings.jsx");
const route = read("scripts/build_route_guard_deferred.py");

test("manage-criteria GET already selects every catalogue column, including the ten levels", () => {
  const getSql = route.slice(route.indexOf("if (action === 'get')"), route.indexOf("mode: 'write'"));
  assert.match(getSql, /SELECT\s+c\.\*/);
  assert.match(getSql, /FROM performance_db\.criteria c/);
  assert.doesNotMatch(getSql, /level_\d+_desc/,
    "GET must not list level columns one by one — c.* already carries them; do not extend the route");
});

test("the readout renders description and levels 1–10 from the payload, with no write control", () => {
  assert.match(readout, /criterion\?\.description/);
  assert.match(readout, /showDescription = true/);
  assert.match(readout, /LEVELS = \[1, 2, 3, 4, 5, 6, 7, 8, 9, 10\]/);
  assert.match(readout, /level_\$\{level\}_desc/);
  assert.doesNotMatch(readout, /<input|<textarea|<select|onSave|onDelete|Сохранить|Удалить|Добавить|Редактировать/);
});

test("the catalogue table opens the readout for every role; write controls stay admin-only", () => {
  assert.match(table, /Показать шкалу \(1–10\)/);
  assert.match(table, /<CriteriaReadout criterion=\{crit\} \/>/);
  assert.match(table, /\{canEdit && <th[^>]*>Действия<\/th>\}/);
  assert.match(settings, /const canEdit = user\?\.role === 'admin';/);
  assert.match(settings, /\{canEdit && \([\s\S]{0,400}Добавить критерий/);
});

test("admin editing is still the existing CriteriaForm with save", () => {
  assert.match(form, /onClick=\{onSave\}/);
  assert.match(form, /Сохранить/);
  assert.match(form, /<LevelDescriptions/);
  assert.match(table, /editingId === crit\.id \? \(/);
  assert.match(table, /<CriteriaForm/);
});
