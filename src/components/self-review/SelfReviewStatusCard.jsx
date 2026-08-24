/**
 * SelfReviewStatusCard - Карточка статуса самооценки
 * 
 * Назначение: Показывает текущий статус самооценки (завершена или не начата).
 * H1 has no self-review update path: Submit Self Review ignores is_update,
 * the catalogue freezes at «Запустить оценку», and no self criterion is
 * project-scoped. The mid-period add-criteria control was removed (BUG-036).
 * Используется в: SelfReview
 * 
 * Props:
 * - hasReview: boolean - есть ли уже самооценка
 * - reviewData: object - данные существующей самооценки
 * - totalCriteriaCount: number - общее количество критериев
 * - evaluatedCount: number - количество оцененных критериев
 * - onStartReview: function - начать самооценку (first submit only)
 * - formatDate: function - функция форматирования даты
 */

import React from 'react';
import { CheckCircle, Star } from 'lucide-react';

const criteriaNoun = (count) => {
  const n = Math.abs(Number(count)) % 100;
  const n1 = n % 10;
  if (n > 10 && n < 20) return 'критериев';
  if (n1 === 1) return 'критерий';
  if (n1 >= 2 && n1 <= 4) return 'критерия';
  return 'критериев';
};

const SelfReviewStatusCard = ({ 
  hasReview, 
  reviewData, 
  totalCriteriaCount,
  evaluatedCount,
  onStartReview,
  formatDate 
}) => {
  // Already submitted — there is no H1 path to add criteria later.
  if (hasReview) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <CheckCircle className="w-8 h-8 text-green-600 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-green-900 mb-2">
              ✅ Вы уже оценили себя в этом периоде
            </h3>
            <div className="space-y-1 text-green-700">
              <p>Итоговая оценка: <span className="font-bold text-2xl">{reviewData?.score}</span></p>
              <p className="text-sm">
                Дата самооценки: {formatDate(reviewData?.date)}
              </p>
              <div className="mt-4 inline-flex items-center px-3 py-1 bg-white rounded-full border border-green-200 shadow-sm text-sm font-medium text-green-800">
                🎉 Все {evaluatedCount} критериев оценены
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Первая самооценка
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 mb-6 flex flex-col items-center text-center">
      <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mb-4">
        <Star className="w-10 h-10 text-indigo-600" />
      </div>
      
      <h3 className="text-xl font-bold text-gray-900 mb-2">Готовы начать?</h3>
      <p className="text-gray-500 max-w-md mb-6">
        Вам доступно <span className="font-bold text-gray-900">{totalCriteriaCount}</span> {criteriaNoun(totalCriteriaCount)} для оценки.
        Это займет не более 5-10 минут.
      </p>

      <button
        onClick={onStartReview}
        disabled={totalCriteriaCount === 0}
        className="px-8 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5"
      >
        {totalCriteriaCount === 0 ? 'Нет доступных критериев' : 'Начать самооценку'}
      </button>
    </div>
  );
};

export default SelfReviewStatusCard;

