/**
 * PeriodBanner - one named period, or the empty-state that refuses mixed rows.
 */
import React from 'react';
import { AlertCircle } from 'lucide-react';

const PeriodBanner = ({ period, campaignActive, emptyCopy, draftName }) => {
  if (period) {
    return (
      <div className={`mb-4 p-3 rounded-lg border text-sm ${
        campaignActive
          ? 'bg-indigo-50 border-indigo-200 text-indigo-800'
          : 'bg-amber-50 border-amber-200 text-amber-800'
      }`}>
        Период: <strong>{period.name}</strong>
        {period.status === 'active' && period.is_active ? ' — активен' : ` — ${period.status}`}
      </div>
    );
  }

  return (
    <div className="mb-4 p-4 rounded-lg border border-amber-200 bg-amber-50 text-amber-900">
      <div className="flex items-start gap-2">
        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">{emptyCopy}</p>
          <p className="text-sm mt-1">
            {draftName
              ? `${draftName} сейчас черновик. Числа появятся после активации.`
              : 'Активируйте период, чтобы увидеть оценки этого цикла.'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default PeriodBanner;
