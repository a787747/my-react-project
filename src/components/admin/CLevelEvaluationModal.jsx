/**
 * CLevelEvaluationModal - C-level evaluation form
 *
 * Same untouched-criterion rule as the ordinary forms (D-0827-2 / D-0827-3):
 * the slider thumb may rest at the left end, but until the evaluator touches
 * it the criterion shows a dash and no zone, and submit stays blocked.
 * An existing actor score is a prior choice — it is shown and is editable.
 * The payload omits untouched keys; it never invents a 5.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { groupCriteria } from '../../utils/matrixUtils';
import { getScoreZone } from '../../utils/evaluationUtils';
import {
  gradesPayloadFromState,
  isCriterionTouched,
  untouchedCriterionIds,
} from '../../utils/evaluationGrades';
import CriterionScaleToggle from '../CriterionScaleToggle';

const CLevelEvaluationModal = ({ isOpen, employee, submitting, onClose, onSubmit }) => {
  const [grades, setGrades] = useState({});

  useEffect(() => {
    if (isOpen && employee) {
      const cLevelCriteria = groupCriteria(employee.criteria).c_level;
      const initialGrades = {};
      cLevelCriteria.forEach((c) => {
        const raw = c.actor_c_level_score;
        if (isCriterionTouched(raw)) {
          initialGrades[c.criteria_id] = parseInt(raw, 10);
        }
      });
      setGrades(initialGrades);
    }
  }, [isOpen, employee]);

  const cLevelCriteria = employee ? groupCriteria(employee.criteria).c_level : [];
  const visibleCriteria = useMemo(
    () => cLevelCriteria.map((c) => ({ id: c.criteria_id })),
    [cLevelCriteria],
  );
  const unevaluated = untouchedCriterionIds(grades, visibleCriteria);
  const allCriteriaEvaluated = visibleCriteria.length > 0 && unevaluated.length === 0;

  if (!isOpen || !employee) return null;

  const handleSliderChange = (criteriaId, value) => {
    setGrades((prev) => ({
      ...prev,
      [criteriaId]: parseInt(value, 10),
    }));
  };

  const handleSubmit = () => {
    if (untouchedCriterionIds(grades, visibleCriteria).length > 0) return;
    onSubmit(gradesPayloadFromState(grades, visibleCriteria));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">

        <div className="bg-gradient-to-r from-orange-600 to-red-600 text-white p-4 flex justify-between items-start shrink-0">
          <div>
            <h2 className="text-xl font-bold">
              {employee.actor_c_level_evaluation_id ? '👑 Изменить C-level оценку' : '👑 C-level оценка'}
            </h2>
            <p className="text-orange-100 text-sm">{employee.full_name}</p>
            {(employee.grade_code || employee.department_name) && (
              <p className="text-orange-200 text-xs">{employee.grade_code}{employee.department_name && ` • ${employee.department_name}`}</p>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-white/20 rounded-full transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 overflow-y-auto flex-1 min-h-0 space-y-4">
          {cLevelCriteria.map((criterion) => {
            const raw = grades[criterion.criteria_id];
            const isSelected = isCriterionTouched(raw);
            const currentScore = isSelected ? parseInt(raw, 10) : null;
            const zone = isSelected ? getScoreZone(currentScore, criterion) : null;
            const levelDesc = isSelected ? criterion[`level_${currentScore}_desc`] : null;

            return (
              <div key={criterion.criteria_id} className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1 pr-3">
                    <h3 className="text-base font-bold text-gray-900">{criterion.criteria_title}</h3>
                    {criterion.criteria_description && (
                      <p className="text-xs text-gray-500 mt-0.5 leading-relaxed whitespace-pre-wrap">
                        {criterion.criteria_description}
                      </p>
                    )}
                  </div>
                  <span
                    data-testid="clevel-score-badge"
                    className={`text-2xl font-bold ${isSelected ? 'text-orange-600' : 'text-gray-400'}`}
                  >
                    {isSelected ? currentScore : '—'}
                  </span>
                </div>

                <input
                  type="range"
                  min="1"
                  max="10"
                  value={currentScore ?? 1}
                  onChange={(e) => handleSliderChange(criterion.criteria_id, e.target.value)}
                  className="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-orange-600"
                  aria-label={`Оценка по критерию ${criterion.criteria_title}`}
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1 px-0.5">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <span key={n} className={`w-3 text-center ${currentScore === n ? 'text-orange-600 font-bold' : ''}`}>
                      {n}
                    </span>
                  ))}
                </div>

                {isSelected && zone && (
                  <div className={`mt-2 p-2 rounded-lg border ${zone.bg} ${zone.border}`}>
                    <p className={`text-xs ${zone.text}`}>
                      <span className="font-semibold">{zone.label}</span>
                      {levelDesc ? ` — Уровень ${currentScore}: ${levelDesc}` : ''}
                    </p>
                  </div>
                )}
                <CriterionScaleToggle
                  criterion={{
                    ...criterion,
                    description: criterion.criteria_description,
                  }}
                />
              </div>
            );
          })}
        </div>

        <div className="p-3 border-t border-gray-100 bg-gray-50 flex gap-3 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-white transition-colors text-sm"
          >
            Отмена
          </button>
          <button
            data-testid="clevel-submit"
            onClick={handleSubmit}
            disabled={submitting || !allCriteriaEvaluated}
            className={`flex-1 px-4 py-2.5 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 text-sm ${
              allCriteriaEvaluated
                ? 'bg-orange-600 text-white hover:bg-orange-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Сохранение...
              </>
            ) : allCriteriaEvaluated ? (
              <>
                <Save className="w-4 h-4" />
                Сохранить
              </>
            ) : (
              `Оцените все критерии (${unevaluated.length})`
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CLevelEvaluationModal;
