import React from 'react';
import { CalendarClock } from 'lucide-react';

/**
 * PeriodNotice — period-aware banner above the Welcome task area.
 * Title and scope render only when name + dates arrived from the API.
 */
const PeriodNotice = ({ notice }) => {
  if (!notice) return null;

  return (
    <div className="card p-5 border-l-4 border-l-info-500" data-testid="period-notice">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 bg-info-100 rounded-xl flex items-center justify-center flex-shrink-0">
          <CalendarClock className="w-5 h-5 text-info-600" />
        </div>
        <div className="flex-1 min-w-0">
          {notice.showTitle && notice.title && (
            <h2 className="text-xl font-bold text-slate-900 mb-2">{notice.title}</h2>
          )}
          <p className="text-slate-700 leading-relaxed mb-3">{notice.body}</p>
          {notice.showScope && notice.scope && (
            <p className="text-slate-700 leading-relaxed mb-3">{notice.scope}</p>
          )}
          <p className="text-sm font-medium text-slate-800">{notice.stateLine}</p>
        </div>
      </div>
    </div>
  );
};

export default PeriodNotice;
