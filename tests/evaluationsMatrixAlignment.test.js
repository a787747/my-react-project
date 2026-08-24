/**
 * evaluationsMatrixAlignment.test.js
 *
 * BUG-051 (browser walkthrough 2026-08-24): the admin evaluations-matrix
 * header rendered all catalogue criteria as columns while each body row
 * emitted <td>s only for its OWN criteria. After D-0822-3 the server stops
 * emitting non-applicable project criteria for general subjects, so a general
 * row produced 8 cells under a 10-column header — every cell after the general
 * group shifted two columns left, and C-level scores displayed under project
 * headers on the screen calibration decisions are read from.
 *
 * The fix renders every row against ONE shared column list (the union of all
 * rows' criteria — buildSharedCriteriaGroups), emitting a placeholder cell for
 * a criterion the row does not carry, the same approach the final-scores
 * screen already used. React sources, so the assertions are made against the
 * source text — the same approach moneyScreenGuards.test.js uses. The pure
 * union/grouping logic is tested directly in matrixUtils.test.js.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const table = readFileSync(
  join(root, 'src/components/admin/EvaluationsMatrixTable.jsx'),
  'utf8',
);

test('header derives from the union of all rows, not employees[0]', () => {
  assert.match(
    table,
    /const headerGroups = buildSharedCriteriaGroups\(employees\)/,
    'the header must be built from every row (a general employees[0] would drop the project columns)',
  );
  assert.ok(
    !table.includes('employees[0].criteria'),
    'no header source may read employees[0] alone',
  );
});

test('body rows map the HEADER column list, never their own criteria list', () => {
  for (const group of ['self', 'general', 'project', 'management', 'c_level']) {
    assert.match(
      table,
      new RegExp(String.raw`headerGroups\.${group}\.map\(`),
      `row cells for "${group}" must iterate the header's columns`,
    );
  }
  assert.ok(
    !/groups\.(self|general|project|management|c_level)\.map\(/.test(table),
    'a row iterating its own groupCriteria() output is exactly the BUG-051 shift',
  );
});

test('a criterion missing from the row renders a placeholder cell in its own column', () => {
  assert.match(
    table,
    /rowCriteria\.get\(hc\.criteria_id\)/,
    'row cells are looked up by the header criterion id',
  );
  assert.match(
    table,
    /renderMissingCell\('proj',[^)]*'N\/A'\)/,
    'non-applicable project columns show N/A (brief item 1), not a skipped <td>',
  );
});

test('header criterion objects never render as data cells', () => {
  // The union keeps the first-seen criterion OBJECT (another row's data). Any
  // data renderer must receive the row's own criterion, found via rowCriteria.
  for (const renderer of ['renderSelfCell', 'renderScoreCell', 'renderProjectCell', 'renderManagementCell']) {
    assert.ok(
      !new RegExp(String.raw`${renderer}\(emp, hc`).test(table),
      `${renderer} must not be handed a header criterion object`,
    );
  }
});
