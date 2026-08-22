import React from 'react';
import { Hourglass } from 'lucide-react';

/**
 * CampaignNotStartedNotice — no running campaign (D-0822-1).
 *
 * Two distinct states share this surface, and the wording separates them:
 *  - inPreparation: a period IS active, but the evaluation has not been started.
 *    The admin is still finishing the criteria catalogue and the coefficients.
 *  - otherwise: there is no active period at all.
 *
 * In both cases the server returns no tasks and refuses every submit, so the
 * form must say why instead of rendering an empty or dead surface.
 */
const CampaignNotStartedNotice = ({ inPreparation = false, embedded = false }) => {
  const title = inPreparation ? 'Оценка ещё не началась' : 'Период оценки не открыт';
  const text = inPreparation
    ? 'Период открыт, но оценка пока в подготовке. Как только она начнётся, задачи появятся здесь автоматически — ничего делать не нужно.'
    : 'Сейчас нет идущего периода оценки. Задачи появятся, когда администратор откроет период и запустит оценку.';

  const card = (
    <div className={`card p-8 text-center border border-info-200 ${embedded ? 'shadow-none border-0 p-4' : ''}`}>
      <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-info-100 flex items-center justify-center">
        <Hourglass className="w-8 h-8 text-info-600" />
      </div>
      <h1 className={`font-bold text-slate-900 mb-3 ${embedded ? 'text-lg' : 'text-2xl'}`}>{title}</h1>
      <p className="text-slate-600 leading-relaxed">{text}</p>
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

export default CampaignNotStartedNotice;
