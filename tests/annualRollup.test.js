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
  coverageSummary,
  coverageLabel,
  formatDateRange,
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

// ── M4: the roll-up must say how much of the container it actually summed ──

test("coverage counts closed children and the ones that carry results", () => {
  const children = [
    { id: 1, status: "closed", has_results: true },
    { id: 2, status: "closed", has_results: false },
    { id: 3, status: "draft", has_results: false },
  ];
  assert.deepEqual(coverageSummary(children), { total: 3, closed: 2, contributing: 1 });
});

test("one closed child of two reads as partial, never as a full year", () => {
  const children = [
    { id: 1, name: "H1-2026", status: "closed", has_results: true },
    { id: 2, name: "H2-2026", status: "draft", has_results: false },
  ];
  assert.equal(coverageLabel(children), "закрыто 1 из 2 дочерних периодов");
  const { contributing, total } = coverageSummary(children);
  assert.ok(contributing < total, "partial coverage must be detectable by the page");
});

test("the live-today shape — one child, unclosed — reports 0 of 1", () => {
  assert.equal(
    coverageLabel([{ id: 2, name: "H1-2026", status: "draft", has_results: false }]),
    "закрыто 0 из 1 дочернего периода"
  );
});

test("coverage of an empty or missing child list does not throw", () => {
  assert.deepEqual(coverageSummary(), { total: 0, closed: 0, contributing: 0 });
  assert.deepEqual(coverageSummary(null), { total: 0, closed: 0, contributing: 0 });
});

test("child date ranges render as ДД.ММ.ГГГГ, missing dates as a dash", () => {
  assert.equal(
    formatDateRange({ start_date: "2026-01-01", end_date: "2026-06-30" }),
    "01.01.2026 — 30.06.2026"
  );
  assert.equal(
    formatDateRange({ start_date: "2026-07-01T00:00:00.000Z", end_date: "2026-12-31T00:00:00.000Z" }),
    "01.07.2026 — 31.12.2026"
  );
  assert.equal(formatDateRange({ start_date: null, end_date: "2026-12-31" }), "—");
  assert.equal(formatDateRange(undefined), "—");
});
