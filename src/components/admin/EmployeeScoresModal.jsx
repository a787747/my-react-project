/**
 * EmployeeScoresModal - Модальное окно просмотра всех оценок сотрудника
 * 
 * Назначение: Отображение всех критериев и оценок сотрудника в удобном формате
 * Используется в: AdminEvaluationsMatrix
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - сотрудник для просмотра
 * - onClose: function - закрыть окно
 * - onCLevelClick: function - перейти к C-level оценке
 * 
 * Логика отображения корректировок:
 * - Если есть c_level_correction, показываем усреднённый балл
 * - Помечаем скорректированные оценки специальным индикатором
 */

import React from 'react';
import { X, Star, Briefcase, Award, Crown, CheckCircle, MinusCircle, AlertTriangle, Users, UserCheck } from 'lucide-react';
import { groupCriteria, getCriterionFinalScore, getCriterionCorrections, canReceiveCLevel, formatCorrectionTooltip, getCLevelChannel, formatCLevelChannel, formatScoreCompact } from '../../utils/matrixUtils';
import { getScoreBandChipClasses } from '../../utils/evaluationUtils';

const EmployeeScoresModal = ({ isOpen, employee, period, onClose, onCLevelClick }) => {
  if (!isOpen || !employee) return null;

  const groups = groupCriteria(employee.criteria || []);

  // Функция для определения цвета оценки
  const getScoreStyle = (score, hasCorrection = false, criterion = null) => {
    if (!score && score !== 0) return 'bg-gray-100 text-gray-400';
    return getScoreBandChipClasses(score, criterion, { hasCorrection });
  };

  const getFinalScore = (criterion) => {
    const raw = getCriterionFinalScore(criterion);
    if (raw === null || raw === undefined) return null;
    return Number(raw).toFixed(1);
  };

  const hasCorrection = (criterion) => getCriterionCorrections(criterion).hasAny;

  // Рендер группы критериев с учётом корректировок
  const renderGroup = (title, criteria, icon, bgColor, borderColor, textColor, showSelfScore = false) => {
    if (!criteria || criteria.length === 0) return null;

    return (
      <div className={`rounded-xl border-2 ${borderColor} overflow-hidden mb-4`}>
        <div className={`${bgColor} px-4 py-3 flex items-center gap-3`}>
          {icon}
          <div>
            <h3 className={`font-bold ${textColor}`}>{title}</h3>
            <p className="text-xs text-gray-600">{criteria.length} критериев</p>
          </div>
        </div>
        
        <div className="divide-y divide-gray-100">
          {criteria.map(c => {
            const hasCorrectionApplied = hasCorrection(c);
            const finalScore = getFinalScore(c);
            
            return (
              <div key={c.criteria_id} className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1 pr-4">
                    <p className="font-medium text-gray-900 text-sm">{c.criteria_title}</p>
                    {c.criteria_description && (
                      <p className="text-xs text-gray-500 mt-1">{c.criteria_description}</p>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {showSelfScore && (
                      <>
                        <div className="text-center">
                          <p className="text-[10px] text-gray-400 mb-1">Само</p>
                          <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${getScoreStyle(c.self_score, false, c)}`}>
                            {c.self_score ?? '-'}
                          </span>
                        </div>
                        <span className="text-gray-300">/</span>
                      </>
                    )}
                    
                    <div className="text-center">
                      <p className="text-[10px] text-gray-400 mb-1">
                        {hasCorrectionApplied ? 'Итого' : (showSelfScore ? 'Рук.' : 'Оценка')}
                      </p>
                      <div className="relative">
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${getScoreStyle(c.manager_score || c.c_level_score, hasCorrectionApplied, c)}`}>
                          {hasCorrectionApplied ? finalScore : (c.manager_score || c.c_level_score || '-')}
                        </span>
                        {hasCorrectionApplied && (
                          <AlertTriangle className="w-3 h-3 text-amber-600 absolute -top-1 -right-1" />
                        )}
                      </div>
                    </div>

                    {/* Показываем детали корректировки */}
                    {hasCorrectionApplied && (
                      <div className="text-center ml-1">
                        <p className="text-[10px] text-amber-600 mb-1">Корр.</p>
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs bg-amber-50 text-amber-700 border border-amber-200">
                          {c.c_level_correction}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Пояснение корректировки */}
                {hasCorrectionApplied && (
                  <div className="mt-2 flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded-lg px-2 py-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>
                      {formatCorrectionTooltip(c)}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Подсчет статистики
  const allCriteria = employee.criteria || [];
  const correctedCount = allCriteria.filter(c => hasCorrection(c)).length;
  const subordinateEvaluatedCount = groups.management?.filter(c => c.subordinate_avg_score !== null && c.subordinate_avg_score !== undefined).length || 0;
  
  const stats = {
    totalCriteria: allCriteria.length,
    evaluated: allCriteria.filter(c => c.manager_score || c.c_level_score || c.self_score).length,
    selfReviewed: allCriteria.filter(c => c.self_score).length,
    cLevelEvaluated: groups.c_level?.filter(c => c.c_level_score).length || 0,
    cLevelTotal: groups.c_level?.length || 0,
    corrected: correctedCount,
    subordinateEvaluated: subordinateEvaluatedCount,
    managementTotal: groups.management?.length || 0
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-4 flex justify-between items-start shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center text-white font-bold text-xl backdrop-blur-md">
              {employee.full_name?.charAt(0) || 'U'}
            </div>
            <div>
              <h2 className="text-xl font-bold">{employee.full_name}</h2>
              <p className="text-indigo-100 text-sm">{employee.job_title}</p>
              {(employee.department_name || employee.grade_code) && (
                <p className="text-xs text-indigo-200">
                  {employee.department_name}{employee.grade_code && ` • ${employee.grade_code}`}
                </p>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Stats bar */}
        <div className="px-4 py-2 bg-indigo-50 border-b border-indigo-100 flex items-center gap-4 shrink-0 text-xs flex-wrap">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-600" />
            <span className="text-gray-600">Оценено:</span>
            <span className="font-bold text-gray-900">{stats.evaluated}/{stats.totalCriteria}</span>
          </div>
          <div className="flex items-center gap-2">
            <Star className="w-4 h-4 text-blue-600" />
            <span className="text-gray-600">Самооценка:</span>
            <span className="font-bold text-gray-900">{stats.selfReviewed}</span>
          </div>
          {stats.cLevelTotal > 0 && (
            <div className="flex items-center gap-2">
              <Crown className="w-4 h-4 text-orange-600" />
              <span className="text-gray-600">C-level:</span>
              <span className="font-bold text-gray-900">{stats.cLevelEvaluated}/{stats.cLevelTotal}</span>
            </div>
          )}
          {stats.corrected > 0 && (
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span className="text-gray-600">Корректировок:</span>
              <span className="font-bold text-amber-700">{stats.corrected}</span>
            </div>
          )}
          {employee.has_subordinates && stats.managementTotal > 0 && (
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-teal-600" />
              <span className="text-gray-600">От подчинённых:</span>
              <span className="font-bold text-teal-700">{stats.subordinateEvaluated}/{stats.managementTotal}</span>
            </div>
          )}
          {employee.is_project_participant && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
              🎯 Участник проекта
            </span>
          )}
        </div>

        {/* Body */}
        <div className="p-4 overflow-y-auto flex-1 min-h-0">
          {/* Самооценка + Оценка руководителя */}
          {renderGroup(
            'Основные критерии',
            groups.self,
            <Star className="w-5 h-5 text-blue-600" />,
            'bg-blue-50',
            'border-blue-200',
            'text-blue-800',
            true
          )}

          {/* Общие критерии */}
          {renderGroup(
            'Общие критерии',
            groups.general,
            <Briefcase className="w-5 h-5 text-green-600" />,
            'bg-green-50',
            'border-green-200',
            'text-green-800'
          )}

          {/* Проектные критерии */}
          {employee.is_project_participant && renderGroup(
            'Проектные критерии',
            groups.project,
            <Award className="w-5 h-5 text-purple-600" />,
            'bg-purple-50',
            'border-purple-200',
            'text-purple-800'
          )}

          {/* Оценка как руководителя (от подчинённых) */}
          {employee.has_subordinates && groups.management?.length > 0 && (
            <div className="rounded-xl border-2 border-teal-200 overflow-hidden mb-4">
              <div className="bg-teal-50 px-4 py-3 flex items-center gap-3">
                <Users className="w-5 h-5 text-teal-600" />
                <div>
                  <h3 className="font-bold text-teal-800">Оценка как руководителя</h3>
                  <p className="text-xs text-gray-600">{groups.management.length} критериев • Оценки от подчинённых и начальника</p>
                </div>
              </div>
              
              <div className="divide-y divide-gray-100">
                {groups.management.map(c => {
                  const hasSubordinateScore = c.subordinate_avg_score !== null && c.subordinate_avg_score !== undefined;
                  const hasBossScore = c.boss_score !== null && c.boss_score !== undefined;
                  const subordinateCount = c.subordinate_count || 0;
                  
                  return (
                    <div key={c.criteria_id} className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 pr-4">
                          <p className="font-medium text-gray-900 text-sm">{c.criteria_title}</p>
                          {c.criteria_description && (
                            <p className="text-xs text-gray-500 mt-1">{c.criteria_description}</p>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-3">
                          {/* Оценка от подчинённых */}
                          <div className="text-center">
                            <p className="text-[10px] text-gray-400 mb-1">
                              От подчин. {hasSubordinateScore && `(${subordinateCount})`}
                            </p>
                            <span className={`inline-flex items-center justify-center w-10 h-8 rounded-full font-bold text-sm ${
                              hasSubordinateScore ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-400'
                            }`}>
                              {hasSubordinateScore ? c.subordinate_avg_score : '-'}
                            </span>
                          </div>
                          
                          <span className="text-gray-300 text-lg">/</span>
                          
                          {/* Оценка от начальника */}
                          <div className="text-center">
                            <p className="text-[10px] text-gray-400 mb-1">От начальн.</p>
                            <span className={`inline-flex items-center justify-center w-10 h-8 rounded-full font-bold text-sm ${
                              hasBossScore ? 'bg-cyan-100 text-cyan-700' : 'bg-gray-100 text-gray-400'
                            }`}>
                              {hasBossScore ? c.boss_score : '-'}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      {/* Детализация оценок */}
                      {(hasSubordinateScore || hasBossScore) && (
                        <div className="mt-2 flex items-center gap-2 text-xs text-teal-700 bg-teal-50 rounded-lg px-2 py-1">
                          <UserCheck className="w-3 h-3" />
                          <span>
                            {hasSubordinateScore && `Среднее от ${subordinateCount} подчинённых: ${c.subordinate_avg_score}`}
                            {hasSubordinateScore && hasBossScore && ' • '}
                            {hasBossScore && `Оценка начальника: ${c.boss_score}`}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* C-level критерии */}
          {groups.c_level?.length > 0 && (
            <div className="rounded-xl border-2 border-orange-200 overflow-hidden">
              <div className="bg-orange-50 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Crown className="w-5 h-5 text-orange-600" />
                  <div>
                    <h3 className="font-bold text-orange-800">C-level критерии</h3>
                    <p className="text-xs text-gray-600">{groups.c_level.length} критериев</p>
                  </div>
                </div>
                {onCLevelClick && canReceiveCLevel(employee, period) && (
                  <button
                    onClick={() => {
                      onClose();
                      onCLevelClick(employee);
                    }}
                    className="px-3 py-1.5 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 transition-colors"
                  >
                    {stats.cLevelEvaluated > 0 ? 'Изменить оценки' : 'Оценить'}
                  </button>
                )}
              </div>
              
              <div className="divide-y divide-gray-100">
                {groups.c_level.map(c => (
                  <div key={c.criteria_id} className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 pr-4">
                        <p className="font-medium text-gray-900 text-sm">{c.criteria_title}</p>
                        {c.criteria_description && (
                          <p className="text-xs text-gray-500 mt-1">{c.criteria_description}</p>
                        )}
                      </div>
                      
                      {/* D-0826-1: балл — среднее по всем C-level, поставившим
                          оценку по этому критерию; число оценщиков подписано
                          под ним, иначе 6 из «4 и 8» неотличимо от чистой 6. */}
                      <div className="text-center">
                        <p className="text-[10px] text-gray-400 mb-1">C-level</p>
                        <span
                          className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${getScoreStyle(getCLevelChannel(c).score, false, c)}`}
                          title={formatCLevelChannel(c) || 'C-level оценка ещё не выставлена'}
                        >
                          {formatScoreCompact(getCLevelChannel(c).score) ?? <MinusCircle className="w-4 h-4" />}
                        </span>
                        {getCLevelChannel(c).averaged && (
                          <p className="text-[10px] text-orange-600 font-semibold mt-1" data-testid="c-level-count">
                            среднее по {getCLevelChannel(c).count}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-100 bg-gray-50 shrink-0">
          <button
            onClick={onClose}
            className="w-full px-4 py-2.5 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-colors text-sm"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

export default EmployeeScoresModal;
