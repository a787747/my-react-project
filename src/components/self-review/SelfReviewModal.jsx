/**
 * SelfReviewModal - Модальное окно самооценки
 * 
 * Назначение: Форма для заполнения самооценки по критериям
 * Используется в: SelfReview
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - isUpdate: boolean - это обновление (новые критерии) или первая оценка
 * - userName: string - имя пользователя
 * - criteria: array - критерии для оценки
 * - grades: object - текущие оценки
 * - comments: object - комментарии к оценкам {criteriaId: comment}
 * - submitting: boolean - статус отправки
 * - draftRestored: boolean - восстановлен ли локальный черновик
 * - onGradeChange: function(criteriaId, value) - изменить оценку
 * - onCommentChange: function(criteriaId, comment) - изменить комментарий
 * - onSubmit: function - отправить
 * - onClose: function - закрыть
 */

import React, { useState, useMemo } from 'react';
import { Loader2, MessageSquare, AlertCircle, CheckCircle, X } from 'lucide-react';
import { getScoreZone, getLevelDescription } from '../../utils/evaluationUtils';
import { isCriterionTouched } from '../../utils/evaluationGrades';
import RatingGuide from '../RatingGuide';
import CriterionScaleToggle from '../CriterionScaleToggle';

const SelfReviewModal = ({ 
  isOpen, 
  isUpdate,
  userName,
  criteria, 
  grades,
  comments = {},
  submitting,
  draftRestored = false,
  onGradeChange,
  onCommentChange,
  onSubmit, 
  onClose 
}) => {
  const [showConfirmation, setShowConfirmation] = useState(false);
  
  // Проверяем, все ли критерии оценены
  const evaluatedCount = useMemo(() => {
    return criteria.filter(c => isCriterionTouched(grades[c.id])).length;
  }, [criteria, grades]);
  
  const allCriteriaEvaluated = evaluatedCount === criteria.length && criteria.length > 0;
  const unevaluatedCriteria = useMemo(() => {
    return criteria.filter(c => !isCriterionTouched(grades[c.id]));
  }, [criteria, grades]);

  if (!isOpen) return null;

  const handleSubmitClick = () => {
    if (!allCriteriaEvaluated) return;
    setShowConfirmation(true);
  };

  const handleConfirmSubmit = () => {
    setShowConfirmation(false);
    onSubmit();
  };

  const handleCancelConfirm = () => {
    setShowConfirmation(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-white border-b border-gray-100 p-6 flex justify-between items-center z-10">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {isUpdate ? 'Оценка новых критериев' : 'Самооценка'}
            </h2>
            <p className="text-sm text-gray-500">{userName}</p>
          </div>
          <div className="flex items-center gap-2">
            {draftRestored && (
              <span className="text-xs bg-amber-100 text-amber-800 px-3 py-1 rounded-full font-medium border border-amber-200">
                Черновик восстановлен
              </span>
            )}
            <div className="bg-indigo-50 px-3 py-1 rounded-full text-indigo-700 text-sm font-medium">
              {criteria.length} вопросов
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8 overflow-y-auto">
            <RatingGuide variant="employee" />
            {criteria.map((criterion) => {
            const isSelected = isCriterionTouched(grades[criterion.id]);
            const currentScore = isSelected ? parseInt(grades[criterion.id], 10) : null;
            const zone = isSelected ? getScoreZone(currentScore, criterion) : null;
            const desc = isSelected ? getLevelDescription(criterion, currentScore) : null;

            return (
              <div key={criterion.id} className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
                {/* Заголовок */}
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">{criterion.title}</h3>
                    {criterion.description && (
                      <p className="text-sm text-gray-500 mt-1 leading-relaxed whitespace-pre-wrap">
                        {criterion.description}
                      </p>
                    )}
                  </div>
                  <div className={`flex flex-col items-center ml-4 px-3 py-2 rounded-lg ${
                    isSelected ? 'bg-indigo-50' : 'bg-gray-50'
                  }`}>
                    <span className={`text-2xl font-bold leading-none ${
                      isSelected ? 'text-indigo-600' : 'text-gray-400'
                    }`}>
                      {isSelected ? currentScore : '—'}
                    </span>
                    <span className="text-xs text-gray-400">/10</span>
                  </div>
                </div>
                
                {/* Слайдер */}
                <div className="mb-4">
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={currentScore ?? 1}
                    onChange={(e) => onGradeChange(criterion.id, e.target.value)}
                    className={`w-full h-2 rounded-lg appearance-none cursor-pointer accent-indigo-600 ${
                      isSelected ? 'bg-gray-200' : 'bg-gray-100 opacity-60'
                    }`}
                  />
                  <div className="flex justify-between text-xs text-gray-400 font-medium mt-1 px-0.5">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                      <span 
                        key={n} 
                        className={`w-4 text-center transition-colors ${
                          currentScore === n ? 'text-indigo-600 font-bold' : ''
                        }`}
                      >
                        {n}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Подсказка если не выбрано */}
                {!isSelected && (
                  <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 mb-4">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span className="text-sm font-medium">Выберите оценку от 1 до 10</span>
                  </div>
                )}

                {/* Описание уровня */}
                {isSelected && zone && (
                  <div className={`${zone.bg} ${zone.border} border rounded-lg p-3 transition-colors duration-300`}>
                    <div className="flex items-start gap-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold mt-0.5 ${zone.text} bg-white bg-opacity-50 border border-current border-opacity-20`}>
                        {zone.label}
                      </span>
                      <p className={`text-sm ${zone.text} font-medium`}>
                        {desc || 'Описание для этого уровня не задано'}
                      </p>
                    </div>
                  </div>
                )}

                <CriterionScaleToggle criterion={criterion} />

                {/* Комментарий к критерию */}
                <div className="mt-4">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-2">
                    <MessageSquare className="w-4 h-4" />
                    Комментарий (необязательно)
                  </label>
                  <textarea
                    value={comments[criterion.id] || ''}
                    onChange={(e) => onCommentChange(criterion.id, e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-shadow text-sm resize-none"
                    rows="2"
                    placeholder="Добавьте пояснение к вашей оценке..."
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-100 bg-gray-50 z-10">
          {/* Прогресс оценивания */}
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-600">
                Оценено: {evaluatedCount} из {criteria.length}
              </span>
              {!allCriteriaEvaluated && (
                <span className="text-xs text-amber-600 font-medium">
                  Осталось: {unevaluatedCriteria.length}
                </span>
              )}
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${
                  allCriteriaEvaluated ? 'bg-green-500' : 'bg-indigo-500'
                }`}
                style={{ width: `${(evaluatedCount / criteria.length) * 100}%` }}
              />
            </div>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-white hover:shadow-sm transition-all"
              disabled={submitting}
            >
              Отмена
            </button>
            <button
              onClick={handleSubmitClick}
              disabled={submitting || !allCriteriaEvaluated}
              className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all flex justify-center items-center gap-2 ${
                allCriteriaEvaluated
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-200'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              {submitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Сохранение...
                </>
              ) : allCriteriaEvaluated ? (
                'Сохранить самооценку'
              ) : (
                `Оцените все критерии (${unevaluatedCriteria.length})`
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Модальное окно подтверждения */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4 z-[60]">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header подтверждения */}
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Подтверждение самооценки</h3>
                  <p className="text-sm text-gray-500">Проверьте ваши оценки перед сохранением</p>
                </div>
              </div>
              <button 
                onClick={handleCancelConfirm}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Список оценок */}
            <div className="p-6 overflow-y-auto flex-1">
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm font-medium text-amber-900">
                Напоминание: самооценка отправляется один раз и не подлежит изменению.
              </div>
              <div className="space-y-3">
                {criteria.map((criterion) => {
                  const score = parseInt(grades[criterion.id], 10);
                  const zone = getScoreZone(score, criterion);
                  return (
                    <div key={criterion.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-sm font-medium text-gray-700 flex-1 mr-4 line-clamp-1">
                        {criterion.title}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${zone.text} ${zone.bg}`}>
                          {zone.label}
                        </span>
                        <span className="text-lg font-bold text-indigo-600 w-8 text-center">
                          {score}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {/* Средний балл */}
              <div className="mt-6 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-indigo-800">Средний балл:</span>
                  <span className="text-2xl font-bold text-indigo-600">
                    {(Object.values(grades).reduce((acc, v) => acc + parseInt(v, 10), 0) / criteria.length).toFixed(1)}
                  </span>
                </div>
              </div>
            </div>

            {/* Footer подтверждения */}
            <div className="p-6 border-t border-gray-100 bg-gray-50 flex gap-3">
              <button
                onClick={handleCancelConfirm}
                className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-white transition-all"
              >
                Изменить
              </button>
              <button
                onClick={handleConfirmSubmit}
                className="flex-1 px-6 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 shadow-md transition-all flex justify-center items-center gap-2"
              >
                <CheckCircle className="w-5 h-5" />
                Подтвердить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SelfReviewModal;


