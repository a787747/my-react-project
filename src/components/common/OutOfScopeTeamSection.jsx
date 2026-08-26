/**
 * OutOfScopeTeamSection — the manager's own people who are EMPLOYED but out of
 * this period's scope (D-0825-11).
 *
 * Why it exists: before 2026-08-25 such a person simply vanished from their
 * manager's list, which reads as a fault — the manager works with them daily.
 * This is the opposite of termination (D-0825-7), where the person disappears
 * on purpose; the server never puts a terminated person in this array, and the
 * two states are deliberately not merged.
 *
 * The rows arrive on their own key (`out_of_scope_data`), never mixed into the
 * task list, so nothing here can be counted as a task, produce a task badge, or
 * be clicked into an evaluation form. The section renders nothing at all when
 * the array is empty, so a manager with a whole team in scope sees no change.
 *
 * Text: owner's words, verbatim, from src/utils/scopeExclusion.js.
 */

import React from 'react';
import { UserX } from 'lucide-react';
import { teamExclusionText } from '../../utils/scopeExclusion';

const OutOfScopeTeamSection = ({ employees = [], className = '' }) => {
  const rows = Array.isArray(employees) ? employees : [];
  if (rows.length === 0) return null;

  return (
    <section
      className={`card p-5 border border-slate-200 ${className}`}
      data-testid="out-of-scope-team"
    >
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
          <UserX className="w-5 h-5 text-slate-500" />
        </div>
        <div className="min-w-0">
          <h2 className="text-lg font-bold text-slate-900 leading-normal">
            Не оцениваются в этом периоде
          </h2>
          <p className="text-sm text-slate-500 leading-normal">
            Эти сотрудники работают и остаются вашими подчинёнными. Оценивать их в этом
            периоде не нужно — задач по ним не будет.
          </p>
        </div>
      </div>

      <ul className="space-y-3 list-none">
        {rows.map((employee) => (
          <li
            key={employee.id}
            className="rounded-lg border border-slate-200 bg-slate-50 p-3"
            data-testid="out-of-scope-team-row"
            data-employee-id={employee.id}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-slate-900">{employee.full_name}</span>
              {employee.job_title && (
                <span className="text-sm text-slate-500">· {employee.job_title}</span>
              )}
              <span className="inline-flex items-center px-1.5 py-0 rounded text-[10px] font-semibold border bg-slate-100 text-slate-600 border-slate-300">
                Без оценки в периоде
              </span>
            </div>
            <p className="text-sm text-slate-700 leading-normal mt-1">
              {teamExclusionText(
                employee.exclusion_reason,
                employee.join_date,
                employee.scope_override
              )}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default OutOfScopeTeamSection;
