/**
 * CriteriaReadout — read-only criterion detail.
 *
 * Shows the description and the ten level texts already present on the
 * manage-criteria GET payload. No inputs, no save/delete/add. Used by the
 * criteria catalogue so a reader who cannot open CriteriaForm can still
 * read the scale (CRITERIA_READONLY_DETAILS).
 */

import React from 'react';

const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export const criterionLevelTexts = (criterion) =>
  LEVELS.map((level) => {
    const raw = criterion?.[`level_${level}_desc`];
    return {
      level,
      text: raw == null ? '' : String(raw),
    };
  });

const CriteriaReadout = ({ criterion }) => {
  const levels = criterionLevelTexts(criterion);
  const description = criterion?.description == null ? '' : String(criterion.description);

  return (
    <div data-testid="criteria-readout" className="space-y-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-1">
          Описание
        </p>
        <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
          {description || '—'}
        </p>
      </div>
      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">
          Описания уровней (1–10)
        </p>
        <ol className="space-y-2">
          {levels.map(({ level, text }) => (
            <li
              key={level}
              data-testid={`criteria-level-${level}`}
              className="flex gap-3 p-2 bg-white rounded border border-slate-100"
            >
              <span className="flex-shrink-0 w-8 h-8 bg-slate-100 rounded flex items-center justify-center text-xs font-bold text-slate-700">
                {level}
              </span>
              <span className="flex-1 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {text || '—'}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
};

export default CriteriaReadout;
