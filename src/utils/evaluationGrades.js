/**
 * Touched vs untouched scores on the evaluation forms.
 *
 * An HTML range input cannot be empty, so the thumb may sit at 1 while the
 * criterion is still untouched. Only an explicit onChange writes a number
 * into form state. The submit payload therefore omits untouched keys —
 * it never invents a 1.
 */

export const isCriterionTouched = (value) =>
  value !== undefined && value !== null && value !== '';

export const gradesPayloadFromState = (evaluations, visibleCriteria) => {
  const visibleIds = new Set(
    (visibleCriteria || []).map((item) => Number(
      item && typeof item === 'object' ? item.id : item
    ))
  );
  const submitted = {};
  Object.entries(evaluations || {}).forEach(([criteriaId, value]) => {
    if (!visibleIds.has(Number(criteriaId))) return;
    if (!isCriterionTouched(value)) return;
    submitted[String(criteriaId)] = parseInt(value, 10);
  });
  return submitted;
};

export const untouchedCriterionIds = (evaluations, visibleCriteria) =>
  (visibleCriteria || [])
    .filter((criterion) => {
      const raw = evaluations?.[criterion.id] ?? evaluations?.[String(criterion.id)];
      return !isCriterionTouched(raw);
    })
    .map((criterion) => Number(criterion.id));
