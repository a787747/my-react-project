/**
 * CriterionSlider - Слайдер для оценки по критерию
 * 
 * Назначение: UI-компонент для выставления оценки от 1 до 10 с описанием уровня
 * Используется в: EvaluationModal, SelfReviewModal
 * 
 * Props:
 * - criterion: object - критерий оценки с полями title, description, level_X_desc
 * - value: number | undefined - текущее значение оценки (undefined = не выбрано)
 * - onChange: function(criterionId, value) - колбэк изменения оценки
 * - employeeSelfReview: object | null - самооценка сотрудника для сравнения
 * - selfComment: string | null - комментарий сотрудника из самооценки
 * - managerComment: string - текущий комментарий руководителя
 * - onCommentChange: function(criterionId, comment) - колбэк изменения комментария
 * - showCommentField: boolean - показывать ли поле комментария (по умолчанию true)
 */

import React, { useState } from 'react';
import { Star, MessageSquare, AlertCircle } from 'lucide-react';
import { getScoreZone, getLevelDescription } from '../utils/evaluationUtils';
import { isCriterionTouched } from '../utils/evaluationGrades';
import CriterionScaleToggle from './CriterionScaleToggle';

// Значения слайдера
const SCORE_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const CriterionSlider = ({ 
  criterion, 
  value, 
  onChange, 
  employeeSelfReview,
  selfComment,
  managerComment = '',
  onCommentChange,
  showCommentField = true
}) => {
  // Состояние undefined означает "не выбрано". The range thumb may sit at 1
  // while this is still false — that is not a submitted score.
  const isSelected = isCriterionTouched(value);
  const currentScore = isSelected ? parseInt(value, 10) : null;
  
  // Состояние для анимации при изменении
  const [isAnimating, setIsAnimating] = useState(false);

  // Получаем стили и описание из общих утилит
  const zone = isSelected ? getScoreZone(currentScore, criterion) : null;
  const description = isSelected ? getLevelDescription(criterion, currentScore) : null;

  // Логика получения самооценки
  let selfReviewScore = undefined;
  if (employeeSelfReview && employeeSelfReview.grades) {
    selfReviewScore = employeeSelfReview.grades[criterion.id] ?? employeeSelfReview.grades[criterion.title];
    if (selfReviewScore !== undefined) {
      selfReviewScore = parseInt(selfReviewScore, 10);
    }
  }

  // Обработчик изменения слайдера
  const handleSliderChange = (e) => {
    setIsAnimating(true);
    onChange(criterion.id, e.target.value);
    setTimeout(() => setIsAnimating(false), 300);
  };

  return (
    <div className={`
      card-interactive p-5 transition-all duration-300
      ${isAnimating ? 'scale-[1.01]' : ''}
      ${!isSelected ? 'border-warning-200 bg-warning-50/30' : ''}
    `}>
      {/* Заголовок и текущая цифра */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1 min-w-0 pr-4">
          <h3 className="text-base font-bold text-slate-900 mb-1">{criterion.title}</h3>
          {criterion.description && (
            <p className="text-sm text-slate-500 leading-relaxed whitespace-pre-wrap">
              {criterion.description}
            </p>
          )}
        </div>
        <div className={`
          flex flex-col items-center px-4 py-2 rounded-xl transition-all duration-300
          ${isSelected 
            ? 'bg-brand-50 border border-brand-100' 
            : 'bg-slate-100 border border-slate-200'
          }
        `}>
          <span className={`
            text-3xl font-bold leading-none transition-all duration-300
            ${isSelected ? 'text-brand-600' : 'text-slate-400'}
          `}>
            {isSelected ? currentScore : '—'}
          </span>
          <span className="text-xs text-slate-400 mt-0.5">/10</span>
        </div>
      </div>
      
      {/* Слайдер как в самооценке */}
      <div className="mb-4">
        <input
          type="range"
          min="1"
          max="10"
          step="1"
          value={currentScore ?? 1}
          onChange={handleSliderChange}
          className={`w-full h-2 rounded-lg appearance-none cursor-pointer accent-brand-600 ${
            isSelected ? 'bg-gray-200' : 'bg-gray-100 opacity-60'
          }`}
          aria-label={`Оценка по критерию ${criterion.title}`}
        />
        <div className="flex justify-between text-xs text-slate-400 font-medium mt-1 px-0.5">
          {SCORE_VALUES.map((n) => (
            <div key={n} className="relative flex flex-col items-center gap-1">
              <span 
                className={`w-4 text-center transition-colors ${
                  currentScore === n ? 'text-brand-600 font-bold' : ''
                }`}
              >
                {n}
              </span>
              {selfReviewScore === n && (
                <span 
                  className="w-2 h-2 rounded-full bg-info-500" 
                  title="Самооценка"
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Подсказка если не выбрано */}
      {!isSelected && (
        <div className="flex items-center gap-2 p-3 bg-warning-50 border border-warning-200 rounded-xl text-warning-700 mb-4 animate-pulse-soft">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm font-medium">Выберите оценку от 1 до 10</span>
        </div>
      )}

      {/* Динамическая зона описания (Цвета и Текст) */}
      {isSelected && zone && (
        <div className={`
          rounded-xl p-4 transition-all duration-300 animate-fade-in
          ${zone.bg} border ${zone.border}
        `}>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <span className={`
                inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold tracking-wide
                ${zone.text} bg-white/60 border border-current/20
              `}>
                {zone.label}
              </span>
            </div>
            <p className={`text-sm ${zone.text} leading-relaxed font-medium`}>
              {description || 'Описание для этого уровня не задано'}
            </p>
          </div>
        </div>
      )}

      <CriterionScaleToggle criterion={criterion} />
      
      {/* Блок самооценки сотрудника (если есть) */}
      {selfReviewScore !== undefined && selfReviewScore !== null && (
        <div className="mt-4 flex items-center justify-between p-3 bg-info-50 border border-info-200 rounded-xl">
          <div className="flex items-center gap-2 text-info-800">
            <Star className="w-4 h-4 text-info-600 fill-current" />
            <span className="text-sm font-medium">Самооценка сотрудника:</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-info-700">
              {selfReviewScore}
            </span>
            {isSelected && currentScore !== selfReviewScore && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                currentScore > selfReviewScore 
                  ? 'bg-success-100 text-success-700' 
                  : 'bg-danger-100 text-danger-700'
              }`}>
                {currentScore > selfReviewScore ? '+' : ''}{currentScore - selfReviewScore}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Комментарий сотрудника из самооценки (если есть) */}
      {selfComment && (
        <div className="mt-4 p-4 bg-warning-50 border border-warning-200 rounded-xl">
          <div className="flex items-start gap-3">
            <MessageSquare className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-warning-700 mb-1">Комментарий сотрудника:</p>
              <p className="text-sm text-warning-900 italic leading-relaxed">"{selfComment}"</p>
            </div>
          </div>
        </div>
      )}

      {/* Поле комментария руководителя (опционально) */}
      {showCommentField && onCommentChange && (
        <div className="mt-4">
          <label className="label">
            Ваш комментарий <span className="text-slate-400 font-normal">(необязательно)</span>
          </label>
          <textarea
            value={managerComment}
            onChange={(e) => onCommentChange(criterion.id, e.target.value)}
            placeholder="Добавьте комментарий к оценке..."
            rows="2"
            className="input resize-none text-sm"
          />
        </div>
      )}
    </div>
  );
};

export default CriterionSlider;

