/**
 * AdminScoring - Страница управления коэффициентами и весами оценок
 * 
 * Назначение: Настройка весов критериев, коэффициентов оценок и коэффициентов грейдов
 * Доступ: admin, c_level
 * 
 * Использует компоненты:
 * - ScoringCoefficientsTable - таблица с коэффициентами критериев
 * - LoadingSpinner - индикатор загрузки
 * 
 * Использует хуки:
 * - useScoreCoefficients - загрузка и сохранение коэффициентов
 */

import React, { useState } from 'react';
import { Calculator, Save, RotateCcw, AlertCircle, Award, ChevronDown, ChevronUp } from 'lucide-react';

// Компоненты
import { LoadingSpinner } from '../components/common';
import { ScoringCoefficientsTable } from '../components/admin';

// Хуки
import { useScoreCoefficients } from '../hooks/useScoreCoefficients';

const AdminScoring = () => {
  // Хук для работы с коэффициентами
  const { 
    criteriaWithCoefficients,
    grades, 
    loading, 
    saving,
    error,
    hasChanges,
    saveCoefficients, 
    updateWeight,
    updateCoefficient,
    updateGradeCoefficient,
    resetChanges
  } = useScoreCoefficients();

  // Состояние секций
  const [showGrades, setShowGrades] = useState(true);
  const [showCriteria, setShowCriteria] = useState(true);

  // Фильтруем и сортируем грейды в нужном порядке
  const gradeOrder = ['A', 'S1', 'S2', 'S3', 'S4-M1', 'M2', 'M3'];
  const filteredGrades = grades
    .filter(g => gradeOrder.includes(g.code))
    .sort((a, b) => gradeOrder.indexOf(a.code) - gradeOrder.indexOf(b.code));

  // Обработчик сохранения
  const handleSave = async () => {
    const result = await saveCoefficients();
    if (result.success) {
      if (result.warning) {
        alert(result.warning);
      } else {
        alert('Коэффициенты успешно сохранены!');
      }
    } else {
      alert(result.error || 'Ошибка при сохранении');
    }
  };

  // Обработчик сброса
  const handleReset = () => {
    if (window.confirm('Вы уверены, что хотите отменить все несохраненные изменения?')) {
      resetChanges();
    }
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка коэффициентов..." />;
  }

  return (
    <div className="max-w-6xl mx-auto p-8 pb-20">
      {/* Header */}
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Calculator className="text-indigo-600 w-8 h-8" />
            Коэффициенты оценок
          </h1>
          <p className="text-slate-500 mt-2">
            Настройте веса критериев и коэффициенты для каждого уровня оценки
          </p>
        </div>
        
        {/* Кнопки действий */}
        <div className="flex gap-3">
          {hasChanges && (
            <button 
              onClick={handleReset}
              disabled={saving}
              className="px-4 py-2 rounded-lg font-semibold flex items-center gap-2 border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <RotateCcw className="w-4 h-4" />
              Отменить
            </button>
          )}
          <button 
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={`px-5 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors ${
              hasChanges 
                ? 'bg-indigo-600 text-white hover:bg-indigo-700' 
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
            }`}
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Сохранение...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Сохранить
              </>
            )}
          </button>
        </div>
      </div>

      {/* Индикатор несохраненных изменений */}
      {hasChanges && (
        <div className="mb-6 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-amber-800">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">
            Есть несохраненные изменения. Не забудьте сохранить перед выходом.
          </span>
        </div>
      )}

      {/* Ошибка */}
      {error && (
        <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {/* Секция: Коэффициенты грейдов */}
      <div className="mb-8">
        <button
          onClick={() => setShowGrades(!showGrades)}
          className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200 hover:border-amber-300 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Award className="w-6 h-6 text-amber-600" />
            <div className="text-left">
              <h2 className="text-lg font-bold text-slate-900">Коэффициенты грейдов</h2>
              <p className="text-sm text-slate-500">Множитель итогового балла для каждого грейда сотрудника</p>
            </div>
          </div>
          {showGrades ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </button>

        {showGrades && (
          <div className="mt-4 bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <p className="text-sm text-slate-600">
                <strong>Формула:</strong> Итоговый балл = Σ(взвешенных баллов) × <span className="text-amber-600 font-bold">коэффициент грейда</span>
              </p>
            </div>
            <div className="p-4">
              {filteredGrades.length === 0 ? (
                <p className="text-center text-slate-400 py-4">Грейды не найдены</p>
              ) : (
                <div className="grid grid-cols-7 gap-3">
                  {filteredGrades.map(grade => (
                    <div 
                      key={grade.id} 
                      className="bg-slate-50 rounded-lg p-3 border border-slate-200 hover:border-amber-300 transition-colors"
                    >
                      <div className="text-center mb-2">
                        <span className="inline-flex items-center justify-center w-10 h-10 bg-amber-100 text-amber-700 rounded-full font-bold text-sm">
                          {grade.code}
                        </span>
                      </div>
                      <input
                        type="number"
                        value={grade.coefficient}
                        onChange={(e) => updateGradeCoefficient(grade.id, e.target.value)}
                        className="w-full px-2 py-1.5 border border-slate-200 rounded-lg text-center font-bold focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-colors"
                        step="0.01"
                        min="0.1"
                        max="5"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Секция: Коэффициенты критериев */}
      <div className="mb-8">
        <button
          onClick={() => setShowCriteria(!showCriteria)}
          className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 hover:border-indigo-300 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Calculator className="w-6 h-6 text-indigo-600" />
            <div className="text-left">
              <h2 className="text-lg font-bold text-slate-900">Веса и коэффициенты критериев</h2>
              <p className="text-sm text-slate-500">Настройка веса каждого критерия и коэффициентов для уровней оценки (1-10)</p>
            </div>
          </div>
          {showCriteria ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </button>

        {showCriteria && (
          <div className="mt-4">
            <ScoringCoefficientsTable
              criteria={criteriaWithCoefficients}
              onWeightChange={updateWeight}
              onCoefficientChange={updateCoefficient}
            />
          </div>
        )}
      </div>

      {/* Плавающая кнопка сохранения при наличии изменений */}
      {hasChanges && (
        <div className="fixed bottom-8 right-8 z-50">
          <button 
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-3 bg-indigo-600 text-white rounded-full font-semibold flex items-center gap-2 shadow-lg hover:bg-indigo-700 transition-all hover:scale-105 disabled:opacity-50"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Сохранение...
              </>
            ) : (
              <>
                <Save className="w-5 h-5" />
                Сохранить изменения
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default AdminScoring;

