export const calculateFinalScore = (evaluations, gradeCoefficient = 1.0) => {
  const scores = Object.values(evaluations).filter(score => typeof score === 'number' && !isNaN(score));
  if (scores.length === 0) return '0.00';
  const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  return (average * gradeCoefficient).toFixed(2);
};

export const filterCriteriaByEmployee = (criteria, employee) => {
  if (!employee) return [];
  return criteria.filter(c => {
    const isActive = c.is_active === true;
    const audience = c.target_audience?.toLowerCase() || 'all';
    const category = employee.work_category?.toLowerCase() || 'general';
    return isActive && (audience === 'all' || audience === category);
  });
};

