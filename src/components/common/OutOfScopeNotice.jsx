import React from 'react';
import { CalendarClock } from 'lucide-react';
import { WELCOME_TITLE, welcomeExclusionText } from '../../utils/scopeExclusion';

/**
 * D-0825-11: the body now depends on WHY the person is out of scope. Until
 * 2026-08-25 one sentence — «ваш первый цикл начнётся со следующего периода» —
 * was shown whatever had happened, which is false for somebody employed since
 * April who is simply out of THIS half-year. `reason` absent ⇒ that same
 * sentence, so an old payload degrades to the previous behaviour.
 */
const OutOfScopeNotice = ({ embedded = false, reason = null }) => {
  const card = (
    <div className={`card p-8 text-center border border-info-200 ${embedded ? 'shadow-none' : ''}`}>
      <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-info-100 flex items-center justify-center">
        <CalendarClock className="w-8 h-8 text-info-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-3">{WELCOME_TITLE}</h1>
      <p className="text-slate-600 leading-relaxed" data-testid="out-of-scope-body">
        {welcomeExclusionText(reason)}
      </p>
    </div>
  );

  if (embedded) {
    return card;
  }

  return (
    <div className="min-h-screen bg-surface-raised p-6 lg:p-8">
      <div className="max-w-2xl mx-auto pt-12">{card}</div>
    </div>
  );
};

export default OutOfScopeNotice;
