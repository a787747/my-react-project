/**
 * Format a period calendar date as «1 января 2026».
 *
 * Uses the YYYY-MM-DD prefix when present so a UTC-midnight Date (the n8n
 * Postgres node serialisation) cannot shift a day backward in Europe/Moscow.
 */

const MONTHS_RU = [
  'января',
  'февраля',
  'марта',
  'апреля',
  'мая',
  'июня',
  'июля',
  'августа',
  'сентября',
  'октября',
  'ноября',
  'декабря',
];

const ymdPrefix = (value) => {
  if (value == null || value === '') return null;
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const y = value.getUTCFullYear();
    const m = String(value.getUTCMonth() + 1).padStart(2, '0');
    const d = String(value.getUTCDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : null;
};

export const formatPeriodDateRu = (value) => {
  const ymd = ymdPrefix(value);
  if (!ymd) return null;
  const [yearStr, monthStr, dayStr] = ymd.split('-');
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  if (!Number.isInteger(year) || month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }
  return `${day} ${MONTHS_RU[month - 1]} ${year}`;
};
