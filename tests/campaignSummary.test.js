/**
 * Campaign counters on /admin/users must name each population and never
 * fold an out-of-scope person or one of the six evaluated-by-nobody into
 * a completion denominator.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  buildCampaignSummary,
  finishedAssignedTasks,
  formatCampaignSummaryLines,
  hasAssignedTask,
  isEvaluatedSubject,
  isFullyEvaluatedByOwed,
} from '../src/utils/campaignSummary.js';

const adminUsers = readFileSync(
  join(resolve(dirname(fileURLToPath(import.meta.url)), '..'), 'src/pages/AdminUsers.jsx'),
  'utf8',
);

const person = (patch) => ({
  id: 1,
  role: 'employee',
  terminated_at: null,
  period_id: 2,
  period_name: 'H1-2026',
  period_is_in_scope: true,
  can_evaluate: true,
  can_be_evaluated: true,
  is_registered: false,
  manager_id: 10,
  manager_role: 'manager',
  manager_can_evaluate: true,
  self_review_done: false,
  has_evaluated_manager: false,
  assigned_subordinate_count: 0,
  completed_subordinate_count: 0,
  received_manager_eval_complete: false,
  expected_upward_count: 0,
  received_upward_count: 0,
  ...patch,
});

const roster = [
  person({ id: 1, full_name: 'Everyone' }),
  person({ id: 2, full_name: 'Terminated', terminated_at: '2026-08-01T00:00:00Z', period_is_in_scope: false }),
  person({
    id: 25,
    full_name: 'Out of scope',
    period_is_in_scope: false,
    can_be_evaluated: true,
    self_review_done: true,
    received_manager_eval_complete: true,
  }),
  person({
    id: 21,
    full_name: 'One of the six',
    role: 'c_level',
    can_evaluate: false,
    can_be_evaluated: false,
    manager_id: null,
    manager_role: null,
    manager_can_evaluate: false,
  }),
  person({
    id: 52,
    full_name: 'Registered employed',
    role: 'hr',
    is_registered: true,
    self_review_done: true,
    has_evaluated_manager: true,
    received_manager_eval_complete: true,
  }),
  person({
    id: 88,
    full_name: 'Tasks done, not yet evaluated',
    self_review_done: true,
    has_evaluated_manager: true,
    received_manager_eval_complete: false,
  }),
  person({
    id: 89,
    full_name: 'Evaluated, tasks unfinished',
    self_review_done: false,
    has_evaluated_manager: false,
    received_manager_eval_complete: true,
  }),
];

test('the four populations stay distinct on a mixed roster', () => {
  const s = buildCampaignSummary(roster);
  assert.equal(s.everyone, 7);
  assert.equal(s.employed, 6);
  assert.equal(s.terminated, 1);
  assert.equal(s.inScope, 5);
  assert.equal(s.evaluatedBySomeone, 4);
  assert.equal(s.invited, 6);
  assert.equal(s.registeredInvited, 1);
});

test('an out-of-scope person is not a completion denominator', () => {
  const out = roster.find((u) => u.id === 25);
  assert.equal(isEvaluatedSubject(out), false);
  assert.equal(hasAssignedTask(out), false);
  assert.equal(isFullyEvaluatedByOwed(out), false);
  const s = buildCampaignSummary(roster);
  assert.equal(s.tasksAssigned, 4);
  assert.equal(s.evaluationOwed, 4);
});

test('one of the six is in scope but never in the evaluated-BY denominator', () => {
  const six = roster.find((u) => u.id === 21);
  assert.equal(six.period_is_in_scope, true);
  assert.equal(isEvaluatedSubject(six), false);
  assert.equal(hasAssignedTask(six), false);
  assert.equal(isFullyEvaluatedByOwed(six), false);
  const s = buildCampaignSummary(roster);
  assert.ok(s.inScope > s.evaluatedBySomeone);
  assert.equal(s.evaluationOwed, s.evaluatedBySomeone);
});

test('the two campaign directions are not the same count', () => {
  const tasksDone = roster.find((u) => u.id === 88);
  const received = roster.find((u) => u.id === 89);
  assert.equal(finishedAssignedTasks(tasksDone), true);
  assert.equal(isFullyEvaluatedByOwed(tasksDone), false);
  assert.equal(finishedAssignedTasks(received), false);
  assert.equal(isFullyEvaluatedByOwed(received), true);
  const s = buildCampaignSummary(roster);
  assert.equal(s.tasksDone, 2);
  assert.equal(s.fullyEvaluated, 2);
  assert.equal(finishedAssignedTasks(tasksDone) && isFullyEvaluatedByOwed(tasksDone), false);
  assert.equal(finishedAssignedTasks(received) && isFullyEvaluatedByOwed(received), false);
});

test('registration is counted against employed, not against everyone or in-scope', () => {
  const withTerminatedRegistered = [
    ...roster,
    person({
      id: 39,
      terminated_at: '2026-01-01T00:00:00Z',
      is_registered: true,
      period_is_in_scope: false,
    }),
  ];
  const s = buildCampaignSummary(withTerminatedRegistered);
  assert.equal(s.everyone, 8);
  assert.equal(s.employed, 6);
  assert.equal(s.registeredInvited, 1);
  assert.equal(s.invited, s.employed);
});

test('the rendered lines name each population in Russian', () => {
  const lines = formatCampaignSummaryLines(buildCampaignSummary(roster));
  assert.deepEqual(lines, [
    'H1-2026: в охвате 5 · оцениваются кем-то 4',
    'Зарегистрировались 1 из 6 работающих',
    'Свои задачи закрыли 2 из 4 · их оценили все, кто должен 2 из 4',
  ]);
});

test('AdminUsers renders the named campaign lines from the full roster', () => {
  assert.match(adminUsers, /buildCampaignSummary\(users\)/);
  assert.match(adminUsers, /formatCampaignSummaryLines/);
  assert.match(adminUsers, /data-testid="campaign-summary"/);
  assert.match(adminUsers, /isFullAccess \? formatCampaignSummaryLines/);
});

test('no active period is said, not counted as zero of something', () => {
  const lines = formatCampaignSummaryLines(buildCampaignSummary([
    person({ period_id: null, period_name: null, period_is_in_scope: false }),
  ]));
  assert.deepEqual(lines, ['Нет активного периода — прогресс кампании не считается']);
});
