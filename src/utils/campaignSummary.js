/**
 * Named campaign counters for Admin → Сотрудники.
 *
 * Every number names its own population. The four that must never be mixed:
 *   everyone            — every row the roster route returns
 *   employed            — still employed (terminated_at is empty)
 *   inScope             — in the current period
 *   evaluatedBySomeone  — in scope AND can_be_evaluated
 *                         (the six the owner declared evaluated by nobody
 *                         are in scope and are excluded here)
 *
 * Registration is counted against employed people — that is who the
 * company-wide invitation is for. Terminated people are not invited.
 *
 * Campaign progress is two directions, never one mixed "completion":
 *   tasks TO them   — people who have at least one assigned Welcome task
 *                     (self-review, upward, or evaluate all in-scope
 *                     evaluable subordinates) and have finished every one
 *   evaluated BY    — people who can be evaluated, and every assigned
 *                     incoming evaluation has arrived (complete manager-path
 *                     from their manager if that manager can evaluate, and
 *                     every in-scope subordinate's upward if they are owed)
 *
 * C-level_direct is a shared channel, not a 1:1 assigned debt. It is not
 * in either counter. If a number cannot be derived from the roster fields
 * this module reads, the caller must not invent it.
 */

export const asBool = (value) =>
  value === true || value === 't' || value === 'true';

export const asInt = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

export const isTerminated = (user) => Boolean(user?.terminated_at);

export const isInScope = (user) => asBool(user?.period_is_in_scope);

export const isEvaluatedSubject = (user) =>
  isInScope(user) && asBool(user?.can_be_evaluated);

export const owesSelfReview = (user) => {
  if (!isInScope(user)) return false;
  const role = String(user?.role ?? '');
  return role !== 'admin' && role !== 'c_level';
};

export const owesUpward = (user) => {
  if (!isInScope(user)) return false;
  if (user?.manager_id === null || user?.manager_id === undefined || user?.manager_id === '') {
    return false;
  }
  const managerRole = String(user?.manager_role ?? '');
  return managerRole !== 'admin' && managerRole !== 'c_level';
};

export const owesSubordinateEvals = (user) => {
  if (!isInScope(user)) return false;
  if (!asBool(user?.can_evaluate)) return false;
  return asInt(user?.assigned_subordinate_count) > 0;
};

export const hasAssignedTask = (user) =>
  owesSelfReview(user) || owesUpward(user) || owesSubordinateEvals(user);

export const finishedAssignedTasks = (user) => {
  if (!hasAssignedTask(user)) return false;
  if (owesSelfReview(user) && !asBool(user?.self_review_done)) return false;
  if (owesUpward(user) && !asBool(user?.has_evaluated_manager)) return false;
  if (
    owesSubordinateEvals(user)
    && asInt(user?.completed_subordinate_count) < asInt(user?.assigned_subordinate_count)
  ) {
    return false;
  }
  return true;
};

export const managerOwesEvaluation = (user) => {
  if (!isEvaluatedSubject(user)) return false;
  if (user?.manager_id === null || user?.manager_id === undefined || user?.manager_id === '') {
    return false;
  }
  return asBool(user?.manager_can_evaluate);
};

export const isFullyEvaluatedByOwed = (user) => {
  if (!isEvaluatedSubject(user)) return false;
  if (managerOwesEvaluation(user) && !asBool(user?.received_manager_eval_complete)) {
    return false;
  }
  if (asInt(user?.expected_upward_count) > asInt(user?.received_upward_count)) {
    return false;
  }
  return true;
};

export const buildCampaignSummary = (users = []) => {
  const roster = Array.isArray(users) ? users : [];
  const hasPeriod = roster.some(
    (user) => user?.period_id !== null && user?.period_id !== undefined && user?.period_id !== '',
  );
  const named = roster.find((user) => user?.period_name);
  const periodName = named?.period_name || null;

  const everyone = roster.length;
  const terminated = roster.filter(isTerminated).length;
  const employed = everyone - terminated;
  const inScope = roster.filter(isInScope).length;
  const evaluatedBySomeone = roster.filter(isEvaluatedSubject).length;
  const registeredInvited = roster.filter(
    (user) => asBool(user?.is_registered) && !isTerminated(user),
  ).length;

  const withTasks = roster.filter(hasAssignedTask);
  const tasksDone = withTasks.filter(finishedAssignedTasks).length;
  const fullyEvaluated = roster.filter(isFullyEvaluatedByOwed).length;

  return {
    hasPeriod,
    periodName,
    everyone,
    employed,
    terminated,
    inScope,
    evaluatedBySomeone,
    invited: employed,
    registeredInvited,
    tasksDone,
    tasksAssigned: withTasks.length,
    fullyEvaluated,
    evaluationOwed: evaluatedBySomeone,
  };
};

export const formatCampaignSummaryLines = (summary) => {
  if (!summary || !summary.hasPeriod) {
    return ['Нет активного периода — прогресс кампании не считается'];
  }
  const name = summary.periodName || 'текущий период';
  return [
    `${name}: в охвате ${summary.inScope} · оцениваются кем-то ${summary.evaluatedBySomeone}`,
    `Зарегистрировались ${summary.registeredInvited} из ${summary.invited} работающих`,
    `Свои задачи закрыли ${summary.tasksDone} из ${summary.tasksAssigned} · их оценили все, кто должен ${summary.fullyEvaluated} из ${summary.evaluationOwed}`,
  ];
};
