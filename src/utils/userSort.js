/**
 * Client-side sort for Admin → Сотрудники.
 * Orders the already-filtered «Найдено» set. Does not change counts.
 */

export const USER_SORT_FIELDS = [
  'name',
  'role',
  'category',
  'department',
  'grade',
  'manager',
  'registered',
];

/**
 * D-0825-11: the roster opens sorted by name, A→Z. Exported rather than inlined
 * in the hook so the default and the comparator cannot drift apart.
 */
export const DEFAULT_SORT_FIELD = 'name';
export const DEFAULT_SORT_DIRECTION = 'asc';

const COLLATOR = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });

function text(value) {
  if (value == null) return '';
  return String(value).trim();
}

function sortValue(user, field) {
  switch (field) {
    case 'name':
      return text(user.full_name);
    case 'role':
      return text(user.role);
    case 'category':
      return text(user.work_category);
    case 'department':
      return text(user.department_name);
    case 'grade':
      return text(user.grade_name);
    case 'manager':
      return text(user.manager_name);
    case 'registered':
      return user.is_registered ? 1 : 0;
    default:
      return '';
  }
}

export function compareUsers(a, b, field, direction = 'asc') {
  const dir = direction === 'desc' ? -1 : 1;
  const av = sortValue(a, field);
  const bv = sortValue(b, field);

  const cmp = field === 'registered'
    ? av - bv
    : COLLATOR.compare(av, bv);

  if (cmp === 0) {
    return (a.id ?? 0) - (b.id ?? 0);
  }
  return cmp * dir;
}

export function sortUsers(users, field, direction = 'asc') {
  if (!Array.isArray(users)) return [];
  if (!field || !USER_SORT_FIELDS.includes(field)) {
    return users;
  }
  return [...users].sort((a, b) => compareUsers(a, b, field, direction));
}
