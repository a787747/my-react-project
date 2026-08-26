/**
 * RatingGuide — in-product H1 rating rules.
 * Text is verbatim from src/content/ratingGuideH1.js; markup only.
 */

import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import {
  RATING_GUIDE_TITLE,
  RATING_GUIDE_STANDING_NOTE,
  getRatingGuideRules,
} from '../content/ratingGuideH1';

/** Display-only: keep words, put each "A → B." sentence on its own line. */
const bodyLines = (body) => {
  if (!body.includes('→')) return [body];
  const lines = body.split(/(?<=\.)\s+/).filter(Boolean);
  return lines.length > 1 ? lines : [body];
};

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
        <h2 className="text-xl md:text-xl font-bold text-slate-900 leading-normal">
          {variant === 'employee' ? 'Краткая инструкция' : RATING_GUIDE_TITLE}
        </h2>
        {variant === 'employee' && (
          <p className="text-sm text-slate-500 mt-0.5 leading-normal">
            3 правила — для оценки руководителя и самооценки
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
        <p
          className="px-5 pt-4 text-sm text-slate-700 leading-normal"
          data-testid="rating-guide-standing-note"
        >
          {RATING_GUIDE_STANDING_NOTE}
        </p>
      )}

      {showBody && (
        <ol className="px-5 pb-5 pt-4 space-y-4 list-none">
          {rules.map((rule, index) => {
            const lines = bodyLines(rule.body);
            const colonLead = rule.lead.endsWith(':');
            const displayNumber = variant === 'employee' ? index + 1 : rule.n;
            return (
              <li key={rule.n} className="flex gap-2.5 text-sm leading-normal">
                <span className="font-semibold text-slate-900 tabular-nums w-7 shrink-0 text-right">
                  {displayNumber}.
                </span>
                <div className="min-w-0 flex-1">
                  {colonLead ? (
                    <p className="text-slate-700">
                      <span className="font-semibold text-slate-900">{rule.lead}</span>{' '}
                      {rule.body}
                    </p>
                  ) : (
                    <>
                      <p className="font-semibold text-slate-900">{rule.lead}</p>
                      {lines.length === 1 ? (
                        <p className="mt-0.5 text-slate-700">{lines[0]}</p>
                      ) : (
                        <ul className="mt-1 space-y-0.5 text-slate-700 list-none">
                          {lines.map((line) => (
                            <li key={line}>{line}</li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
};

export default RatingGuide;
