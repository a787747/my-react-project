/**
 * ScoreDetailModal - Модальное окно просмотра и корректировки оценки
 * 
 * Назначение: Отображение подробной информации об одной оценке
 *             + возможность корректировки для mid-level менеджеров и C-level/admin
 * Используется в: AdminEvaluationsMatrix, ManagerSubordinatesMatrix
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - сотрудник
 * - criterion: object - критерий с оценками (включая mid_level_correction и c_level_correction)
 * - group: string - группа критерия (self, general, project, c_level)
 * - user: object - текущий пользователь
 * - correctionLevel: string - уровень корректировки ('mid_level' или 'c_level', по умолчанию определяется по роли)
 * - onClose: function - закрыть окно
 * - onCorrectionSubmit: function(employeeId, criterionId, score, level) - отправить корректировку
 */

import React, { useState, useEffect } from 'react';
import { X, Star, User, TrendingUp, MessageSquare, Edit3, Save, Loader2, AlertCircle, Crown, Users } from 'lucide-react';
import { getScoreZone } from '../../utils/evaluationUtils';
import { getCLevelChannel, formatScoreCompact } from '../../utils/matrixUtils';
import logger from '../../utils/logger';

const ScoreDetailModal = ({ 
  isOpen, 
  employee, 
  criterion, 
  group, 
  user,
  correctionLevel: propCorrectionLevel,
  onClose,
  onCorrectionSubmit 
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [correctionScore, setCorrectionScore] = useState(5);
  const [submitting, setSubmitting] = useState(false);

  // Определяем уровень корректировки по роли пользователя или пропсу
  const isAdminActor = user && user.role === 'admin';
  const correctionLevel = propCorrectionLevel || (isAdminActor ? 'c_level' : 'mid_level');

  // Проверка прав на корректировку (ROLE_ACCESS_HR_CLEVEL, 2026-08-26):
  // - admin ставит c_level коррекции
  // - менеджеры менеджеров ставят mid_level коррекции (проверяется на бэкенде)
  // - роль c_level сервер отказывает на маршруте корректировки (403), поэтому
  //   орган корректировки ей не рисуется — C-level смотрит, канал C-level
  //   калибруется усреднением (D-0826-1), не корректировкой
  const canCorrect = user && (
    isAdminActor || (user.role === 'manager' && user.has_manager_subordinates)
  );
  
  // Можно корректировать только если есть оценка менеджера (не C-level only критерии)
  const hasManagerScore = criterion?.manager_score !== undefined && criterion?.manager_score !== null;
  const showCorrectionOption = canCorrect && hasManagerScore && group !== 'c_level';

  // Инициализация значения корректировки
  useEffect(() => {
    if (isOpen && criterion) {
      // Берём существующую корректировку для текущего уровня, или оценку менеджера
      const existingCorrection = correctionLevel === 'c_level' 
        ? (criterion.c_level_correction ?? criterion.manager_score ?? 5)
        : (criterion.mid_level_correction ?? criterion.manager_score ?? 5);
      setCorrectionScore(existingCorrection);
      setIsEditing(false);
    }
  }, [isOpen, criterion, correctionLevel]);

  if (!isOpen || !employee || !criterion) return null;

  // Определяем цвета в зависимости от группы
  const groupStyles = {
    self: {
      gradient: 'from-blue-600 to-cyan-600',
      title: '⭐ Основной критерий',
      subtitle: 'Самооценка + Оценка руководителя'
    },
    general: {
      gradient: 'from-green-600 to-emerald-600',
      title: '📋 Общий критерий',
      subtitle: 'Оценка руководителя'
    },
    project: {
      gradient: 'from-purple-600 to-pink-600',
      title: '🎯 Проектный критерий',
      subtitle: 'Для участников проектов'
    },
    c_level: {
      gradient: 'from-orange-600 to-red-600',
      title: '👑 C-level критерий',
      subtitle: 'Оценка руководства'
    }
  };

  const style = groupStyles[group] || groupStyles.general;

  // Функция для определения цвета оценки
  const getScoreStyle = (score) => {
    if (!score && score !== 0) return { bg: 'bg-gray-100', text: 'text-gray-400', label: 'Нет оценки' };
    const zone = getScoreZone(score, criterion);
    return { bg: zone.bg, text: zone.text, label: zone.label };
  };

  // Получаем описание уровня
  const getLevelDescription = (score) => {
    if (score === null || score === undefined) return null;
    return criterion[`level_${score}_desc`] || criterion[`level_${Math.round(score)}_desc`];
  };

  const selfScore = criterion.self_score;
  const managerScore = criterion.manager_score;
  // D-0826-1: канал c_level_direct — среднее по всем C-level, поставившим
  // оценку по этому критерию, и число оценщиков рядом.
  const cLevelChannel = getCLevelChannel(criterion);
  const cLevelScore = cLevelChannel.score;
  const midLevelCorrection = criterion.mid_level_correction;
  const cLevelCorrection = criterion.c_level_correction;
  
  const selfStyle = getScoreStyle(selfScore);
  const managerStyle = getScoreStyle(managerScore);
  const cLevelStyle = getScoreStyle(cLevelScore);

  // Вычисление итоговой оценки с учётом всех корректировок
  const calculateFinalScore = () => {
    if (group === 'c_level') {
      return cLevelScore;
    }
    
    if (managerScore === undefined || managerScore === null) {
      return null;
    }
    
    // Собираем все оценки для усреднения
    const scores = [managerScore];
    
    if (midLevelCorrection !== undefined && midLevelCorrection !== null) {
      scores.push(midLevelCorrection);
    }
    
    if (cLevelCorrection !== undefined && cLevelCorrection !== null) {
      scores.push(cLevelCorrection);
    }
    
    if (scores.length === 1) {
      return managerScore;
    }
    
    const sum = scores.reduce((acc, s) => acc + s, 0);
    return (sum / scores.length).toFixed(1);
  };

  const finalScore = calculateFinalScore();
  const hasMidLevelCorrection = midLevelCorrection !== undefined && midLevelCorrection !== null;
  const hasCLevelCorrection = cLevelCorrection !== undefined && cLevelCorrection !== null;
  const hasAnyCorrection = hasMidLevelCorrection || hasCLevelCorrection;
  
  // Для обратной совместимости
  const hasCorrectionApplied = hasAnyCorrection;

  const levelDescription = getLevelDescription(managerScore || selfScore || cLevelScore);

  // Обработчик отправки корректировки
  const handleSubmitCorrection = async () => {
    if (!onCorrectionSubmit) return;
    
    setSubmitting(true);
    try {
      await onCorrectionSubmit(employee.id, criterion.criteria_id, correctionScore, correctionLevel);
      setIsEditing(false);
    } catch (error) {
      logger.error('Ошибка сохранения корректировки:', error);
      alert(error?.message || 'Ошибка при сохранении корректировки');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className={`bg-gradient-to-r ${style.gradient} text-white p-4 shrink-0`}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-white/80 text-xs mb-0.5">{style.title}</p>
              <h2 className="text-lg font-bold">{criterion.criteria_title}</h2>
              <p className="text-white/70 text-sm">{employee.full_name}</p>
            </div>
            <button onClick={onClose} className="p-1.5 hover:bg-white/20 rounded-full transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4 overflow-y-auto flex-1 min-h-0">
          
          {/* Описание критерия */}
          {criterion.criteria_description && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-sm text-gray-600">{criterion.criteria_description}</p>
            </div>
          )}

          {/* Оценки */}
          <div className="space-y-3">
            
            {/* Самооценка (если есть) */}
            {(group === 'self' || selfScore !== undefined) && (
              <div className={`${selfStyle.bg} rounded-lg p-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-blue-200 rounded-full flex items-center justify-center">
                      <Star className="w-4 h-4 text-blue-700" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">Самооценка</p>
                      <p className="text-xs text-gray-500">{selfStyle.label}</p>
                    </div>
                  </div>
                  <span className={`text-3xl font-bold ${selfStyle.text}`}>
                    {selfScore ?? '-'}
                  </span>
                </div>
              </div>
            )}

            {/* Оценка руководителя (если есть) */}
            {(group !== 'c_level' && (managerScore !== undefined || group === 'general' || group === 'project')) && (
              <div className={`${managerStyle.bg} rounded-lg p-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-green-200 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-green-700" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">Оценка руководителя</p>
                      <p className="text-xs text-gray-500">{managerStyle.label}</p>
                    </div>
                  </div>
                  <span className={`text-3xl font-bold ${managerStyle.text}`}>
                    {managerScore ?? '-'}
                  </span>
                </div>
              </div>
            )}

            {/* C-level оценка (если есть) */}
            {(group === 'c_level' || cLevelScore !== undefined) && (
              <div className={`${cLevelStyle.bg} rounded-lg p-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-orange-200 rounded-full flex items-center justify-center">
                      <TrendingUp className="w-4 h-4 text-orange-700" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">
                        C-level оценка
                        {cLevelChannel.averaged && (
                          <span className="ml-1 text-xs font-normal text-orange-700" data-testid="c-level-count">
                            — среднее по {cLevelChannel.count} оценкам
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-gray-500">{cLevelStyle.label}</p>
                    </div>
                  </div>
                  <span className={`text-3xl font-bold ${cLevelStyle.text}`}>
                    {formatScoreCompact(cLevelScore) ?? '-'}
                  </span>
                </div>
              </div>
            )}

            {/* Сравнение самооценки и оценки руководителя */}
            {group === 'self' && selfScore !== undefined && managerScore !== undefined && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-600" />
                  <div>
                    <p className="font-medium text-indigo-900 text-sm">Разница оценок</p>
                    <p className="text-xs text-indigo-700">
                      {selfScore === managerScore ? (
                        'Оценки совпадают'
                      ) : selfScore > managerScore ? (
                        `Самооценка выше на ${selfScore - managerScore} баллов`
                      ) : (
                        `Оценка руководителя выше на ${managerScore - selfScore} баллов`
                      )}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Отображение существующих корректировок */}
            {hasMidLevelCorrection && (
              <div className="bg-teal-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-teal-200 rounded-full flex items-center justify-center">
                      <Users className="w-4 h-4 text-teal-700" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">Коррекция менеджера</p>
                      <p className="text-xs text-gray-500">Mid-level</p>
                    </div>
                  </div>
                  <span className="text-3xl font-bold text-teal-700">{midLevelCorrection}</span>
                </div>
              </div>
            )}
            
            {hasCLevelCorrection && (
              <div className="bg-orange-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-orange-200 rounded-full flex items-center justify-center">
                      <Crown className="w-4 h-4 text-orange-700" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">Коррекция C-level</p>
                      <p className="text-xs text-gray-500">Высшее руководство</p>
                    </div>
                  </div>
                  <span className="text-3xl font-bold text-orange-700">{cLevelCorrection}</span>
                </div>
              </div>
            )}

            {/* Блок добавления/редактирования корректировки (если есть права) */}
            {showCorrectionOption && (
              <div className={`border-2 border-dashed rounded-lg p-3 ${
                correctionLevel === 'c_level' 
                  ? 'border-amber-300 bg-amber-50' 
                  : 'border-teal-300 bg-teal-50'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {correctionLevel === 'c_level' ? (
                      <Crown className="w-4 h-4 text-amber-600" />
                    ) : (
                      <Users className="w-4 h-4 text-teal-600" />
                    )}
                    <p className={`font-semibold text-sm ${
                      correctionLevel === 'c_level' ? 'text-amber-800' : 'text-teal-800'
                    }`}>
                      {correctionLevel === 'c_level' ? 'Корректировка C-level' : 'Корректировка Mid-level'}
                    </p>
                  </div>
                  {!isEditing && (
                    <button
                      onClick={() => setIsEditing(true)}
                      className={`flex items-center gap-1 px-2 py-1 text-xs text-white rounded-lg transition-colors ${
                        correctionLevel === 'c_level' 
                          ? 'bg-amber-600 hover:bg-amber-700' 
                          : 'bg-teal-600 hover:bg-teal-700'
                      }`}
                    >
                      <Edit3 className="w-3 h-3" />
                      {(correctionLevel === 'c_level' ? hasCLevelCorrection : hasMidLevelCorrection) 
                        ? 'Изменить' : 'Добавить'}
                    </button>
                  )}
                </div>

                {isEditing && (
                  <div className="mt-3 space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-600">Ваша оценка:</span>
                        <span className={`text-xl font-bold ${
                          correctionLevel === 'c_level' ? 'text-amber-700' : 'text-teal-700'
                        }`}>{correctionScore}</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={correctionScore}
                        onChange={(e) => setCorrectionScore(parseInt(e.target.value))}
                        className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${
                          correctionLevel === 'c_level' 
                            ? 'bg-amber-200 accent-amber-600' 
                            : 'bg-teal-200 accent-teal-600'
                        }`}
                      />
                      <div className="flex justify-between text-xs text-gray-400 mt-1 px-0.5">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                          <span key={n} className={`w-3 text-center ${
                            correctionScore === n 
                              ? (correctionLevel === 'c_level' ? 'text-amber-600 font-bold' : 'text-teal-600 font-bold') 
                              : ''
                          }`}>
                            {n}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="bg-white rounded-lg p-2 text-xs text-gray-600">
                      <p>
                        <strong>Расчёт итоговой оценки:</strong>{' '}
                        {(() => {
                          const scores = [managerScore];
                          const labels = ['Менеджер'];
                          
                          if (correctionLevel === 'mid_level') {
                            scores.push(correctionScore);
                            labels.push('Mid-level');
                            if (hasCLevelCorrection) {
                              scores.push(cLevelCorrection);
                              labels.push('C-level');
                            }
                          } else {
                            if (hasMidLevelCorrection) {
                              scores.push(midLevelCorrection);
                              labels.push('Mid-level');
                            }
                            scores.push(correctionScore);
                            labels.push('C-level');
                          }
                          
                          const sum = scores.reduce((a, b) => a + b, 0);
                          const avg = (sum / scores.length).toFixed(1);
                          
                          return (
                            <>
                              ({scores.join(' + ')}) / {scores.length} = {' '}
                              <span className={`font-bold ${
                                correctionLevel === 'c_level' ? 'text-amber-700' : 'text-teal-700'
                              }`}>{avg}</span>
                            </>
                          );
                        })()}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() => setIsEditing(false)}
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        Отмена
                      </button>
                      <button
                        onClick={handleSubmitCorrection}
                        disabled={submitting}
                        className={`flex-1 px-3 py-2 text-sm text-white rounded-lg transition-colors flex items-center justify-center gap-1 ${
                          correctionLevel === 'c_level' 
                            ? 'bg-amber-600 hover:bg-amber-700' 
                            : 'bg-teal-600 hover:bg-teal-700'
                        }`}
                      >
                        {submitting ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
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
                )}

                {!isEditing && (
                  <p className={`text-xs mt-2 ${
                    correctionLevel === 'c_level' ? 'text-amber-700' : 'text-teal-700'
                  }`}>
                    💡 Вы можете скорректировать оценку. Итоговый балл будет средним всех корректировок.
                  </p>
                )}
              </div>
            )}

            {/* Итоговая оценка с учётом корректировок */}
            {hasAnyCorrection && group !== 'c_level' && (
              <div className="bg-gradient-to-r from-indigo-100 to-purple-100 border border-indigo-300 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-indigo-900 text-sm">Итоговая оценка</p>
                    <p className="text-xs text-indigo-700">
                      {(() => {
                        const parts = [managerScore];
                        if (hasMidLevelCorrection) parts.push(midLevelCorrection);
                        if (hasCLevelCorrection) parts.push(cLevelCorrection);
                        return `(${parts.join(' + ')}) / ${parts.length}`;
                      })()}
                    </p>
                  </div>
                  <span className="text-3xl font-bold text-indigo-800">{finalScore}</span>
                </div>
              </div>
            )}
          </div>

          {/* Описание уровня */}
          {levelDescription && (
            <div className="border border-gray-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900 text-sm mb-0.5">Описание уровня</p>
                  <p className="text-xs text-gray-600">{levelDescription}</p>
                </div>
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

export default ScoreDetailModal;
