/**
 * ProfileStats - Карточки статистики профиля
 * 
 * Назначение: Отображение основных показателей пользователя
 * Используется в: Profile
 * 
 * Props:
 * - stats: object - объект со статистикой
 *   - latest_score, latest_period, average_score, total_evaluations, latest_date
 * - formatDate: function - функция форматирования даты
 */

import React from 'react';
import { Award, TrendingUp, Calendar, User } from 'lucide-react';

const ProfileStats = ({ stats, formatDate }) => {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      {/* Последняя оценка */}
      <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-blue-500">
        <div className="flex items-center justify-between mb-2">
          <Award className="w-8 h-8 text-blue-500" />
          <span className="text-sm text-gray-500">Последняя</span>
        </div>
        <div className="text-3xl font-bold text-gray-800">
          {stats.latest_score}
        </div>
        <div className="text-sm text-gray-600 mt-1">
          {stats.latest_period}
        </div>
      </div>

      {/* Средний балл */}
      <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-green-500">
        <div className="flex items-center justify-between mb-2">
          <TrendingUp className="w-8 h-8 text-green-500" />
          <span className="text-sm text-gray-500">Средний балл</span>
        </div>
        <div className="text-3xl font-bold text-gray-800">
          {stats.average_score}
        </div>
        <div className="text-sm text-gray-600 mt-1">
          За все периоды
        </div>
      </div>

      {/* Всего оценок */}
      <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-purple-500">
        <div className="flex items-center justify-between mb-2">
          <Calendar className="w-8 h-8 text-purple-500" />
          <span className="text-sm text-gray-500">Всего оценок</span>
        </div>
        <div className="text-3xl font-bold text-gray-800">
          {stats.total_evaluations}
        </div>
        <div className="text-sm text-gray-600 mt-1">
          Периодов оценки
        </div>
      </div>

      {/* Последнее обновление */}
      <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-orange-500">
        <div className="flex items-center justify-between mb-2">
          <User className="w-8 h-8 text-orange-500" />
          <span className="text-sm text-gray-500">Последнее обновление</span>
        </div>
        <div className="text-sm font-semibold text-gray-800 mt-2">
          {formatDate(stats.latest_date)}
        </div>
      </div>
    </div>
  );
};

export default ProfileStats;

