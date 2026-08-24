import React from 'react';
import { CalendarClock } from 'lucide-react';

const OutOfScopeNotice = ({ embedded = false }) => {
  const card = (
    <div className={`card p-8 text-center border border-info-200 ${embedded ? 'shadow-none' : ''}`}>
      <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-info-100 flex items-center justify-center">
        <CalendarClock className="w-8 h-8 text-info-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-3">
        Вы вне охвата текущего периода оценки
      </h1>
      <p className="text-slate-600 leading-relaxed">
        Ваш первый цикл оценки начнётся со следующего периода. Сейчас от вас не требуется никаких действий.
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
