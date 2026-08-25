/**
 * RatingGuide — in-product H1 rating rules.
 * Text is verbatim from src/content/ratingGuideH1.js; markup only.
 */

import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import {
  RATING_GUIDE_TITLE,
  getRatingGuideRules,
} from '../content/ratingGuideH1';

const RatingGuide = ({
  variant = 'full',
  collapsible = false,
  defaultOpen = true,
}) => {
  const [open, setOpen] = useState(collapsible ? defaultOpen : true);
  const rules = getRatingGuideRules(variant);
  const showBody = !collapsible || open;

  const titleRow = (
    <div className="flex items-start gap-3">
      <div className="w-10 h-10 bg-brand-100 rounded-xl flex items-center justify-center flex-shrink-0">
        <BookOpen className="w-5 h-5 text-brand-600" />
      </div>
      <div className="min-w-0">
        <h2 className="text-xl font-bold text-slate-900">
          {RATING_GUIDE_TITLE}
        </h2>
        {variant === 'employee' && (
          <p className="text-sm text-slate-500 mt-0.5">
            Правила 1, 7 и 8 — для оценки руководителя и самооценки
          </p>
        )}
      </div>
    </div>
  );

  return (
    <div
      className="rounded-xl border border-brand-200 bg-white"
      data-testid="rating-guide"
      data-guide-variant={variant}
    >
      {collapsible ? (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-brand-50/60 rounded-xl transition-colors"
          aria-expanded={open}
        >
          {titleRow}
          {open ? (
            <ChevronUp className="w-5 h-5 text-slate-500 flex-shrink-0" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-500 flex-shrink-0" />
          )}
        </button>
      ) : (
        <div className="p-5 pb-0">{titleRow}</div>
      )}

      {showBody && (
        <ol className="px-5 pb-5 pt-4 space-y-3 list-none">
          {rules.map((rule) => (
            <li key={rule.n} className="text-sm text-slate-800 leading-relaxed">
              <span className="font-semibold text-slate-900">
                {rule.n}. {rule.lead}
              </span>{' '}
              {rule.body}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};

export default RatingGuide;
