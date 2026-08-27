/**
 * Collapsed ten-level scale for an evaluation form card.
 * Reuses the read-only catalogue readout (levels only — the card already
 * shows the criterion description). Closed by default so the form stays
 * one-score-at-a-time.
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import CriteriaReadout from './admin/CriteriaReadout';

const CriterionScaleToggle = ({ criterion }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3" data-testid="criterion-scale-toggle">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
        aria-expanded={open}
      >
        {open ? (
          <>
            <ChevronUp className="w-4 h-4" />
            Скрыть шкалу
          </>
        ) : (
          <>
            <ChevronDown className="w-4 h-4" />
            Показать шкалу (1–10)
          </>
        )}
      </button>
      {open && (
        <div className="mt-2 p-3 bg-slate-50 border border-slate-100 rounded-xl">
          <CriteriaReadout criterion={criterion} showDescription={false} />
        </div>
      )}
    </div>
  );
};

export default CriterionScaleToggle;
