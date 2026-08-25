/**
 * Pure filtering logic for the employee list (Admin → Сотрудники, Моя команда).
 *
 * Kept out of the hook so it can be tested without React, and so the filter row,
 * the counters and the option lists are all derived from ONE definition of
 * "does this person match".
 *
 * Two rules this module exists to enforce:
 *
 * 1. Every control narrows the SAME set — the predicate is a plain AND over all
 *    six keys, in any order of selection.
 * 2. An option is offered only if somebody in the population carries that value,
 *    and it is offered with the count it would produce given the OTHER active
 *    filters. A control can therefore never silently return zero: the zero is on
 *    the option, before the click.
 */

import {
  EVALUATION_STATE_LABELS,
  EVALUATION_STATE_ORDER,
  evaluationStateOf,
} from './evaluationState.js';

export const ALL = 'all';

// Sentinel for "this person has no department / no manager at all". Without it
// the 1 person with department_id NULL and the 3 with manager_id NULL are
// unreachable from the filter row: no option matches a NULL.
export const NONE = '__none__';

export const FILTER_KEYS = [
  'employment',
  'search',
  'role',
  'work_category',
  'department_id',
  'manager_id',
  // D-0825-11: the person's state in the current period — terminated, hired
  // after the period end, taken out by hand, hire date missing, or in
  // evaluation. Each is distinct from the others and from «в оценке».
  'evaluation_state',
];

// employment is the only filter whose default is not «все» — it is `active`, so
// the working list hides terminated people (D-0825-7), and reset returns to
// `active` rather than `all`.
export const INITIAL_FILTERS = {
  search: '',
  role: ALL,
  department_id: ALL,
  manager_id: ALL,
  work_category: ALL,
  employment: 'active',
  evaluation_state: ALL,
};

export const EMPLOYMENT_OPTIONS = [
  { value: 'active', label: 'Работают' },
  { value: 'terminated', label: 'Уволены' },
  { value: ALL, label: 'Все (вкл. уволенных)' },
];

// Canonical order and display casing. The values are the DB values verbatim —
// performance_db.user_role_type. `hr` was missing from the filter row until
// 2026-08-25: two people (role='hr') could not be isolated at all.
export const ROLE_ORDER = ['admin', 'c_level', 'manager', 'hr', 'employee'];
export const ROLE_LABELS = {
  admin: 'Admin',
  c_level: 'C-Level',
  manager: 'Manager',
  hr: 'HR',
  employee: 'Employee',
};

// performance_db.work_category_type. `tender` and `hybrid` exist as enum labels
// and nobody carries them; they are offered only if somebody does.
export const CATEGORY_ORDER = ['general', 'project', 'tender', 'hybrid'];
export const CATEGORY_LABELS = {
  general: 'General',
  project: 'Project',
  tender: 'Tender',
  hybrid: 'Hybrid',
};

const COLLATOR = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' });

export const isTerminated = (user) => Boolean(user?.terminated_at);

/** NULL / undefined / '' all collapse onto the NONE sentinel. */
const idKey = (value) =>
  value === null || value === undefined || value === '' ? NONE : String(value);

const normalizeSearch = (value) => String(value ?? '').trim().toLowerCase();

const MATCHERS = {
  employment: (user, filters) => {
    if (filters.employment === ALL) return true;
    return filters.employment === 'terminated' ? isTerminated(user) : !isTerminated(user);
  },
  search: (user, filters) => {
    const query = normalizeSearch(filters.search);
    if (!query) return true;
    return (
      String(user?.full_name ?? '').toLowerCase().includes(query) ||
      String(user?.email ?? '').toLowerCase().includes(query)
    );
  },
  role: (user, filters) =>
    filters.role === ALL || String(user?.role ?? '') === String(filters.role),
  work_category: (user, filters) =>
    filters.work_category === ALL ||
    String(user?.work_category ?? '') === String(filters.work_category),
  department_id: (user, filters) =>
    filters.department_id === ALL ||
    idKey(user?.department_id) === String(filters.department_id),
  manager_id: (user, filters) =>
    filters.manager_id === ALL || idKey(user?.manager_id) === String(filters.manager_id),
  evaluation_state: (user, filters) =>
    filters.evaluation_state === ALL
    || evaluationStateOf(user) === String(filters.evaluation_state),
};

/**
 * @param {object} user
 * @param {object} filters
 * @param {string|null} except - filter key to ignore (used to build facet counts)
 */
export function matchesFilters(user, filters, except = null) {
  return FILTER_KEYS.every((key) => key === except || MATCHERS[key](user, filters));
}

export function filterUsers(users = [], filters = INITIAL_FILTERS) {
  if (!Array.isArray(users)) return [];
  return users.filter((user) => matchesFilters(user, filters));
}

export function countActiveFilters(filters = INITIAL_FILTERS) {
  return FILTER_KEYS.filter((key) => {
    if (key === 'search') return normalizeSearch(filters.search) !== '';
    return filters[key] !== INITIAL_FILTERS[key];
  }).length;
}

/** Options for one key: what exists in the population, counted over the rest. */
function facetFor(users, filters, key, describe, order) {
  const base = users.filter((user) => matchesFilters(user, filters, key));

  const present = new Map();
  users.forEach((user) => {
    const entry = describe(user);
    if (entry && !present.has(entry.value)) present.set(entry.value, entry);
  });

  const counts = new Map();
  base.forEach((user) => {
    const entry = describe(user);
    if (!entry) return;
    counts.set(entry.value, (counts.get(entry.value) ?? 0) + 1);
  });

  const list = Array.from(present.values()).map((entry) => ({
    ...entry,
    count: counts.get(entry.value) ?? 0,
  }));

  list.sort(order);

  // A selection the population no longer offers must stay visible: otherwise the
  // <select> falls back to displaying «Все …» while the filter is still applied.
  const selected = filters[key];
  if (selected !== ALL && !list.some((entry) => String(entry.value) === String(selected))) {
    list.push({ value: String(selected), label: '— недоступен —', count: 0, orphan: true });
  }

  return list;
}

const byLabelNoneLast = (a, b) => {
  if (a.value === NONE) return 1;
  if (b.value === NONE) return -1;
  return COLLATOR.compare(a.label, b.label);
};

const byFixedOrder = (order) => (a, b) => {
  const ai = order.indexOf(a.value);
  const bi = order.indexOf(b.value);
  if (ai === -1 && bi === -1) return COLLATOR.compare(a.label, b.label);
  if (ai === -1) return 1;
  if (bi === -1) return -1;
  return ai - bi;
};

/**
 * Option lists for every control, with live counts.
 * Membership is computed over the whole population so the lists do not shift
 * under the owner while he composes; only the counts move.
 */
export function buildFacets(users = [], filters = INITIAL_FILTERS) {
  const roster = Array.isArray(users) ? users : [];
  const byId = new Map(roster.map((user) => [String(user?.id), user]));

  const employmentBase = roster.filter((user) => matchesFilters(user, filters, 'employment'));
  const employmentTerminated = employmentBase.filter(isTerminated).length;

  return {
    employment: EMPLOYMENT_OPTIONS.map((option) => ({
      ...option,
      count:
        option.value === ALL
          ? employmentBase.length
          : option.value === 'terminated'
            ? employmentTerminated
            : employmentBase.length - employmentTerminated,
    })),

    role: facetFor(
      roster,
      filters,
      'role',
      (user) => {
        const value = String(user?.role ?? '');
        if (!value) return null;
        return { value, label: ROLE_LABELS[value] ?? value };
      },
      byFixedOrder(ROLE_ORDER),
    ),

    work_category: facetFor(
      roster,
      filters,
      'work_category',
      (user) => {
        const value = String(user?.work_category ?? '');
        if (!value) return null;
        return { value, label: CATEGORY_LABELS[value] ?? value };
      },
      byFixedOrder(CATEGORY_ORDER),
    ),

    department_id: facetFor(
      roster,
      filters,
      'department_id',
      (user) => {
        const value = idKey(user?.department_id);
        if (value === NONE) return { value: NONE, label: 'Без отдела' };
        return { value, label: String(user?.department_name ?? `#${value}`) };
      },
      byLabelNoneLast,
    ),

    manager_id: facetFor(
      roster,
      filters,
      'manager_id',
      (user) => {
        const value = idKey(user?.manager_id);
        if (value === NONE) return { value: NONE, label: 'Без руководителя' };
        const name = String(user?.manager_name ?? `#${value}`);
        // A terminated manager keeps their reports; the option has to stay, and
        // has to say why the people under it look odd.
        const label = isTerminated(byId.get(value)) ? `${name} (уволен)` : name;
        return { value, label };
      },
      byLabelNoneLast,
    ),

    // Derived, not a column: the state is computed from four fields the route
    // returns. Only states somebody actually carries are offered, each with the
    // count it will produce given the other active filters — same contract as
    // every other control (D-0825-8).
    evaluation_state: facetFor(
      roster,
      filters,
      'evaluation_state',
      (user) => {
        const value = evaluationStateOf(user);
        return { value, label: EVALUATION_STATE_LABELS[value] ?? value };
      },
      byFixedOrder(EVALUATION_STATE_ORDER),
    ),
  };
}

/**
 * Every number the header shows, each over a named population.
 *
 * total / active / terminated  -> the whole visible population, never filtered
 * found / foundActive / foundTerminated -> the filtered set
 * hiddenTerminated / hiddenActive -> people the employment control alone removed
 */
export function buildCounts(users = [], filters = INITIAL_FILTERS, filtered = null) {
  const roster = Array.isArray(users) ? users : [];
  const found = filtered ?? filterUsers(roster, filters);

  const terminated = roster.filter(isTerminated).length;
  const foundTerminated = found.filter(isTerminated).length;

  const employmentBase = roster.filter((user) => matchesFilters(user, filters, 'employment'));

  return {
    total: roster.length,
    active: roster.length - terminated,
    terminated,
    found: found.length,
    foundActive: found.length - foundTerminated,
    foundTerminated,
    hiddenTerminated:
      filters.employment === 'active' ? employmentBase.filter(isTerminated).length : 0,
    hiddenActive:
      filters.employment === 'terminated'
        ? employmentBase.filter((user) => !isTerminated(user)).length
        : 0,
  };
}
