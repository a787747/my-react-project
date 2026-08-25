import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ALL,
  NONE,
  INITIAL_FILTERS,
  FILTER_KEYS,
  ROLE_ORDER,
  buildCounts,
  buildFacets,
  countActiveFilters,
  filterUsers,
  matchesFilters,
} from '../src/utils/userFilters.js';

// Shape mirrors the live payload of `API: Admin Get Users Data`: role is the raw
// DB value, department_id / manager_id are integers or NULL, terminated_at is a
// string or NULL, and manager_name rides along on the report's own row.
const roster = [
  { id: 1, full_name: 'Admin One',    email: 'admin@x.tm',  role: 'admin',    work_category: 'general', department_id: 14, department_name: 'C-level',  manager_id: null, manager_name: null,          terminated_at: null },
  { id: 2, full_name: 'Clevel Two',   email: 'cl@x.tm',     role: 'c_level',  work_category: 'general', department_id: 14, department_name: 'C-level',  manager_id: 1,    manager_name: 'Admin One',   terminated_at: null },
  { id: 3, full_name: 'Manager Son',  email: 'son@x.tm',    role: 'manager',  work_category: 'project', department_id: 2,  department_name: 'Project',  manager_id: 2,    manager_name: 'Clevel Two',  terminated_at: null },
  { id: 4, full_name: 'Hr Person',    email: 'hr@x.tm',     role: 'hr',       work_category: 'general', department_id: 9,  department_name: 'HR',       manager_id: 2,    manager_name: 'Clevel Two',  terminated_at: null },
  { id: 5, full_name: 'Emp Alpha',    email: 'alpha@x.tm',  role: 'employee', work_category: 'project', department_id: 2,  department_name: 'Project',  manager_id: 3,    manager_name: 'Manager Son', terminated_at: null },
  { id: 6, full_name: 'Emp Beta',     email: 'beta@x.tm',   role: 'employee', work_category: 'project', department_id: 2,  department_name: 'Project',  manager_id: 3,    manager_name: 'Manager Son', terminated_at: null },
  { id: 7, full_name: 'Emp Gone',     email: 'gone@x.tm',   role: 'employee', work_category: 'project', department_id: 2,  department_name: 'Project',  manager_id: 3,    manager_name: 'Manager Son', terminated_at: '2026-08-25T15:54:23Z' },
  { id: 8, full_name: 'Emp Nodept',   email: 'nodept@x.tm', role: 'employee', work_category: 'general', department_id: null, department_name: null,     manager_id: 1,    manager_name: 'Admin One',   terminated_at: null },
];

const withFilters = (patch) => ({ ...INITIAL_FILTERS, ...patch });
const ids = (list) => list.map((u) => u.id);
const facetFor = (facets, key, value) =>
  facets[key].find((option) => String(option.value) === String(value));

test('defaults: employment is the only filter that is not «все»', () => {
  assert.deepEqual(INITIAL_FILTERS, {
    search: '',
    role: ALL,
    department_id: ALL,
    manager_id: ALL,
    work_category: ALL,
    employment: 'active',
    // D-0825-11: the period-state control defaults to «любое состояние», so the
    // page still opens on every employed person and the exclusions are visible
    // rather than filtered away.
    evaluation_state: ALL,
  });
  assert.deepEqual(FILTER_KEYS.slice().sort(), [
    'department_id', 'employment', 'evaluation_state', 'manager_id', 'role',
    'search', 'work_category',
  ]);
});

test('default view hides the terminated person and nobody else', () => {
  assert.deepEqual(ids(filterUsers(roster, INITIAL_FILTERS)), [1, 2, 3, 4, 5, 6, 8]);
});

test('«Уволены» shows exactly the terminated person', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ employment: 'terminated' }))), [7]);
});

test('«Все (вкл. уволенных)» shows everybody', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ employment: ALL }))), [1, 2, 3, 4, 5, 6, 7, 8]);
});

test('role filter matches the raw DB value, not the display casing', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ role: 'c_level' }))), [2]);
  assert.deepEqual(ids(filterUsers(roster, withFilters({ role: 'C-Level' }))), []);
});

test('hr is a filterable role', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ role: 'hr' }))), [4]);
  assert.ok(ROLE_ORDER.includes('hr'));
  const facets = buildFacets(roster, INITIAL_FILTERS);
  assert.equal(facetFor(facets, 'role', 'hr').count, 1);
});

test('department and manager compare as strings, so 2 and "2" agree', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ department_id: '2' }))), [3, 5, 6]);
  assert.deepEqual(ids(filterUsers(roster, withFilters({ department_id: 2 }))), [3, 5, 6]);
  assert.deepEqual(ids(filterUsers(roster, withFilters({ manager_id: '3' }))), [5, 6]);
});

test('people with no department and no manager are reachable', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ department_id: NONE }))), [8]);
  assert.deepEqual(ids(filterUsers(roster, withFilters({ manager_id: NONE }))), [1]);
});

test('every combination is an AND, in any order of selection', () => {
  const a = withFilters({ manager_id: '3', work_category: 'project', employment: ALL });
  const b = withFilters({ work_category: 'project', employment: ALL, manager_id: '3' });
  assert.deepEqual(ids(filterUsers(roster, a)), [5, 6, 7]);
  assert.deepEqual(ids(filterUsers(roster, a)), ids(filterUsers(roster, b)));
});

test('a combination that must return everybody', () => {
  const all = withFilters({ employment: ALL, role: ALL, department_id: ALL, manager_id: ALL, work_category: ALL, search: '' });
  assert.equal(filterUsers(roster, all).length, roster.length);
});

test('a combination that must return nobody', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ manager_id: '3', role: 'manager', employment: ALL }))), []);
});

test('search trims and is case-insensitive over name and e-mail', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ search: '  ALPHA  ' }))), [5]);
  assert.deepEqual(ids(filterUsers(roster, withFilters({ search: 'nodept@' }))), [8]);
});

test('search for a terminated person finds nobody by default, and finds them under «Все»', () => {
  assert.deepEqual(ids(filterUsers(roster, withFilters({ search: 'gone' }))), []);
  assert.deepEqual(ids(filterUsers(roster, withFilters({ search: 'gone', employment: ALL }))), [7]);
});

test('the hidden-by-employment count explains that empty result', () => {
  const counts = buildCounts(roster, withFilters({ search: 'gone' }));
  assert.equal(counts.found, 0);
  assert.equal(counts.hiddenTerminated, 1);
});

test('facet counts are computed over the other active filters', () => {
  // Manager Son selected: all three of her reports are employees on a project.
  const filters = withFilters({ manager_id: '3' });
  const facets = buildFacets(roster, filters);
  assert.equal(facetFor(facets, 'role', 'employee').count, 2); // one of the three is terminated
  assert.equal(facetFor(facets, 'role', 'manager').count, 0);
  assert.equal(facetFor(facets, 'work_category', 'general').count, 0);
  assert.equal(facetFor(facets, 'employment', 'terminated').count, 1);
  assert.equal(facetFor(facets, 'employment', ALL).count, 3);
});

test('option membership stays stable while composing; only counts move', () => {
  const wide = buildFacets(roster, INITIAL_FILTERS);
  const narrow = buildFacets(roster, withFilters({ manager_id: '3' }));
  assert.deepEqual(wide.role.map((o) => o.value), narrow.role.map((o) => o.value));
  assert.deepEqual(wide.department_id.map((o) => o.value), narrow.department_id.map((o) => o.value));
});

test('no option is offered that nobody in the population carries', () => {
  const facets = buildFacets(roster, withFilters({ employment: ALL }));
  assert.deepEqual(facets.work_category.map((o) => o.value), ['general', 'project']);
  assert.equal(facets.work_category.some((o) => o.value === 'tender'), false);
  assert.deepEqual(
    facets.manager_id.map((o) => o.label),
    ['Admin One', 'Clevel Two', 'Manager Son', 'Без руководителя'],
  );
});

test('a terminated manager keeps their option and is labelled', () => {
  const withTerminatedManager = roster.map((u) =>
    u.id === 3 ? { ...u, terminated_at: '2026-08-25T16:00:00Z' } : u,
  );
  const facets = buildFacets(withTerminatedManager, withFilters({ employment: ALL }));
  assert.equal(facetFor(facets, 'manager_id', '3').label, 'Manager Son (уволен)');
});

test('a selection the population no longer offers stays visible instead of reading «Все»', () => {
  const facets = buildFacets(roster, withFilters({ manager_id: '999' }));
  const orphan = facetFor(facets, 'manager_id', '999');
  assert.ok(orphan);
  assert.equal(orphan.orphan, true);
  assert.equal(orphan.count, 0);
});

test('counts: found is the filtered set, total/active/terminated the population', () => {
  const filters = withFilters({ employment: ALL, department_id: '2' });
  const counts = buildCounts(roster, filters);
  assert.equal(counts.total, 8);
  assert.equal(counts.active, 7);
  assert.equal(counts.terminated, 1);
  assert.equal(counts.found, 4); // Manager Son + three reports in department «Project»
  assert.equal(counts.foundActive, 3);
  assert.equal(counts.foundTerminated, 1);
  assert.equal(counts.foundActive + counts.foundTerminated, counts.found);
});

test('«Уволены» reports how many working people that one control hides', () => {
  const counts = buildCounts(roster, withFilters({ employment: 'terminated' }));
  assert.equal(counts.found, 1);
  assert.equal(counts.hiddenActive, 7);
  assert.equal(counts.hiddenTerminated, 0);
});

test('active-filter count: the default state is zero, employment counts when moved', () => {
  assert.equal(countActiveFilters(INITIAL_FILTERS), 0);
  assert.equal(countActiveFilters(withFilters({ employment: ALL })), 1);
  assert.equal(countActiveFilters(withFilters({ search: '   ' })), 0);
  assert.equal(countActiveFilters(withFilters({ role: 'hr', manager_id: '3' })), 2);
});

test('matchesFilters can skip one key, which is what facet counting needs', () => {
  const filters = withFilters({ role: 'manager' });
  const employee = roster[4];
  assert.equal(matchesFilters(employee, filters), false);
  assert.equal(matchesFilters(employee, filters, 'role'), true);
});
