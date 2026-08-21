/**
 * annualRollup.test.js
 *
 * Client-side semantics of the annual roll-up cells (src/utils/annualRollup.js):
 * marker precedence, no-zero-fill display, formatting.
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  cellState,
  cellLabel,
  formatRating,
  formatIndex,
  CELL_STATES,
} from "../src/utils/annualRollup.js";

const closedChild = { id: 11, status: "closed", has_results: true };

test("unclosed child contributes nothing regardless of results", () => {
  const cell = cellState({ id: 12, status: "active", has_results: false }, { in_scope: true, final_rating: "8.0" });
  assert.equal(cell.state, CELL_STATES.NOT_CLOSED);
  assert.equal(cell.final_rating, null);
  assert.equal(cellLabel(cell.state), "период не закрыт");
});

test("closed child without persisted results is marked honestly, never live numbers", () => {
  const cell = cellState({ id: 13, status: "closed", has_results: false }, undefined);
  assert.equal(cell.state, CELL_STATES.CLOSED_NO_RESULTS);
  assert.equal(cellLabel(cell.state), "нет сохранённых результатов");
});

test("missing result row renders «вне охвата», not a zero", () => {
  const cell = cellState(closedChild, undefined);
  assert.equal(cell.state, CELL_STATES.OUT_OF_SCOPE);
  assert.equal(cell.final_rating, null);
  assert.equal(cellLabel(cell.state), "вне охвата");
});

test("stored out-of-scope row renders «вне охвата»", () => {
  const cell = cellState(closedChild, { in_scope: false, has_data: false, final_rating: null });
  assert.equal(cell.state, CELL_STATES.OUT_OF_SCOPE);
});

test("in scope but never evaluated renders «нет данных», not a zero", () => {
  const cell = cellState(closedChild, { in_scope: true, has_data: false, final_rating: null, bonus_index: null });
  assert.equal(cell.state, CELL_STATES.NO_DATA);
  assert.equal(cell.final_rating, null);
  assert.equal(cellLabel(cell.state), "нет данных");
});

test("persisted final passes through numerically", () => {
  const cell = cellState(closedChild, {
    in_scope: true, has_data: true, final_rating: "8.0000", bonus_index: "27.0000",
  });
  assert.equal(cell.state, CELL_STATES.OK);
  assert.equal(cell.final_rating, 8);
  assert.equal(cell.bonus_index, 27);
});

test("half-year employee: single in-scope period displays its own value — no dilution to half", () => {
  // Employee B from the acceptance: in scope P2 only, final 8.0.
  // The client renders the server's mean untouched: 8.00, NOT 4.00.
  const p1 = cellState(closedChild, undefined); // out of scope
  const p2 = cellState({ id: 14, status: "closed", has_results: true }, {
    in_scope: true, has_data: true, final_rating: "8.0000", bonus_index: "13.5000",
  });
  assert.equal(p1.state, CELL_STATES.OUT_OF_SCOPE);
  assert.equal(p2.final_rating, 8);
  assert.equal(formatRating("8.0000"), "8.00");
});

test("missing annual values format as a dash, never 0", () => {
  assert.equal(formatRating(null), "—");
  assert.equal(formatRating(undefined), "—");
  assert.equal(formatIndex(null), "—");
  assert.notEqual(formatIndex(null), "0,00");
});

test("index formats with two decimals", () => {
  assert.equal(formatIndex("27.0000").endsWith("27,00"), true);
});
