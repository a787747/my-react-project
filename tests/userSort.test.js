import test from 'node:test';
import assert from 'node:assert/strict';
import { sortUsers, USER_SORT_FIELDS } from '../src/utils/userSort.js';

const roster = [
  { id: 3, full_name: 'Cem Durukan', role: 'c_level', work_category: 'general', department_name: 'C-level', grade_name: 'S1', manager_name: null, is_registered: false },
  { id: 1, full_name: 'Akmyrat Annayev', role: 'employee', work_category: 'project', department_name: 'Projects', grade_name: 'A10', manager_name: 'Bayram Urayev', is_registered: false },
  { id: 2, full_name: 'Alexander Petrosov', role: 'admin', work_category: 'project', department_name: 'C-level', grade_name: 'A2', manager_name: null, is_registered: true },
  { id: 4, full_name: 'Alina Naubatova', role: 'employee', work_category: 'general', department_name: 'HR', grade_name: 'A1', manager_name: 'Alexander Petrosov', is_registered: false },
];

test('known sort fields are the classification columns', () => {
  assert.deepEqual(USER_SORT_FIELDS, [
    'name',
    'role',
    'category',
    'department',
    'grade',
    'manager',
    'registered',
  ]);
});

test('no field leaves order and reference unchanged', () => {
  assert.equal(sortUsers(roster, null), roster);
  assert.equal(sortUsers(roster, ''), roster);
});

test('does not mutate the input array', () => {
  const copy = roster.map((u) => ({ ...u }));
  sortUsers(roster, 'name', 'asc');
  assert.deepEqual(roster, copy);
});

test('sorts by name ascending then descending', () => {
  const asc = sortUsers(roster, 'name', 'asc').map((u) => u.full_name);
  const desc = sortUsers(roster, 'name', 'desc').map((u) => u.full_name);
  assert.deepEqual(asc, [
    'Akmyrat Annayev',
    'Alexander Petrosov',
    'Alina Naubatova',
    'Cem Durukan',
  ]);
  assert.deepEqual(desc, [...asc].reverse());
});

test('category puts general before project on asc', () => {
  const cats = sortUsers(roster, 'category', 'asc').map((u) => u.work_category);
  assert.deepEqual(cats, ['general', 'general', 'project', 'project']);
});

test('grade uses alphanumeric order (A1, A2, A10, S1)', () => {
  const grades = sortUsers(roster, 'grade', 'asc').map((u) => u.grade_name);
  assert.deepEqual(grades, ['A1', 'A2', 'A10', 'S1']);
});

test('registered false comes before true on asc', () => {
  const flags = sortUsers(roster, 'registered', 'asc').map((u) => Boolean(u.is_registered));
  assert.deepEqual(flags, [false, false, false, true]);
});

test('empty manager names sort before assigned managers on asc', () => {
  const names = sortUsers(roster, 'manager', 'asc').map((u) => u.manager_name || '');
  assert.equal(names[0], '');
  assert.equal(names[1], '');
  assert.equal(names[2], 'Alexander Petrosov');
  assert.equal(names[3], 'Bayram Urayev');
});

test('equal values stay stable by id', () => {
  const twins = [
    { id: 20, full_name: 'Same', work_category: 'project' },
    { id: 8, full_name: 'Same', work_category: 'project' },
    { id: 15, full_name: 'Same', work_category: 'project' },
  ];
  assert.deepEqual(
    sortUsers(twins, 'name', 'asc').map((u) => u.id),
    [8, 15, 20]
  );
  assert.deepEqual(
    sortUsers(twins, 'name', 'desc').map((u) => u.id),
    [8, 15, 20]
  );
});

test('sort composes with a filtered set and does not change its count', () => {
  const found = roster.filter((u) => u.work_category === 'project');
  const sorted = sortUsers(found, 'name', 'desc');
  assert.equal(sorted.length, found.length);
  assert.deepEqual(
    sorted.map((u) => u.full_name),
    ['Alexander Petrosov', 'Akmyrat Annayev']
  );
});
