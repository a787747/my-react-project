/**
 * ManagerSubordinatesMatrix - Страница матрицы оценок подчинённых менеджеров
 * 
 * Назначение: Позволяет менеджерам среднего звена видеть и корректировать
 *             оценки сотрудников, которыми управляют их подчинённые менеджеры
 * 
 * Доступ: Менеджеры, у которых есть подчинённые с has_subordinates = true
 * 
 * Логика корректировок:
 * - Mid-level менеджеры добавляют mid_level_correction
 * - Итоговая оценка = среднее(оценка_менеджера, mid_level_correction, [c_level_correction])
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Users, TrendingUp, RefreshCw, Filter, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { LoadingSpinner, PeriodBanner } from '../components/common';
import ScoreDetailModal from '../components/admin/ScoreDetailModal';
import { groupCriteria } from '../utils/matrixUtils';
import logger from '../utils/logger';

/**
 * Получить итоговую оценку по критерию с учётом корректировок
 */
const getFinalScore = (criterion) => {
  const { manager_score, mid_level_correction, c_level_correction } = criterion;
  
  if (manager_score === null || manager_score === undefined) {
    return null;
  }
  
  const scores = [manager_score];
  
  if (mid_level_correction !== null && mid_level_correction !== undefined) {
    scores.push(mid_level_correction);
  }
  
  if (c_level_correction !== null && c_level_correction !== undefined) {
    scores.push(c_level_correction);
  }
  
  const sum = scores.reduce((acc, score) => acc + score, 0);
  return sum / scores.length;
};

/**
 * Стиль для оценки
 */
const getScoreStyle = (score) => {
  if (score === null || score === undefined) {
    return 'bg-gray-100 text-gray-400';
  }
  if (score >= 8) return 'bg-green-100 text-green-700';
  if (score >= 5) return 'bg-yellow-100 text-yellow-700';
  if (score >= 3) return 'bg-orange-100 text-orange-700';
  return 'bg-red-100 text-red-700';
};

const ManagerSubordinatesMatrix = ({ user }) => {
  const [employees, setEmployees] = useState([]);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);
  const [periodCatalog, setPeriodCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detailModal, setDetailModal] = useState({ isOpen: false, employee: null, criterion: null, group: null });
  const [expandedManagers, setExpandedManagers] = useState({});
  const [filterManager, setFilterManager] = useState('');

  // Загрузка данных
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(API_ENDPOINTS.MANAGER_SUBORDINATES_MATRIX, {
        params: { manager_id: user.id }
      });
      setEmployees(response.data.data || []);
      setPeriod(response.data.period || null);
      setCampaignActive(Boolean(response.data.campaign_active));
      
      // Раскрываем все группы по умолчанию
      const managers = {};
      (response.data.data || []).forEach(e => {
        if (e.manager_name) {
          managers[e.manager_name] = true;
        }
      });
      setExpandedManagers(managers);
    } catch (err) {
      logger.error('Ошибка загрузки:', err);
      setError(err.response?.data?.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    apiClient.get(API_ENDPOINTS.PERIODS)
      .then((response) => setPeriodCatalog(response.data?.data || []))
      .catch(() => setPeriodCatalog([]));
  }, []);

  // Группировка сотрудников по менеджерам
  const employeesByManager = useMemo(() => {
    const groups = {};
    employees.forEach(emp => {
      const managerName = emp.manager_name || 'Без менеджера';
      if (!groups[managerName]) {
        groups[managerName] = [];
      }
      groups[managerName].push(emp);
    });
    return groups;
  }, [employees]);

  // Уникальные менеджеры для фильтра
  const uniqueManagers = useMemo(() => {
    return Object.keys(employeesByManager).sort();
  }, [employeesByManager]);

  // Фильтрованные группы
  const filteredGroups = useMemo(() => {
    if (!filterManager) return employeesByManager;
    return { [filterManager]: employeesByManager[filterManager] || [] };
  }, [employeesByManager, filterManager]);

  // Клик по ячейке с оценкой
  const handleScoreClick = (employee, criterion, group) => {
    setDetailModal({ isOpen: true, employee, criterion, group });
  };

  // Закрыть модалку
  const handleCloseModal = () => {
    setDetailModal({ isOpen: false, employee: null, criterion: null, group: null });
  };

  // Отправка корректировки
  const handleScoreCorrection = async (employeeId, criteriaId, score, correctionLevel) => {
    try {
      const payload = {
        evaluator_id: user.id,
        subject_id: employeeId,
        criteria_id: criteriaId,
        correction_score: score,
        correction_level: correctionLevel || 'mid_level'
      };

      await apiClient.post(API_ENDPOINTS.ADMIN_SCORE_CORRECTION, payload);
      
      // Обновляем локальное состояние
      const correctionField = correctionLevel === 'c_level' ? 'c_level_correction' : 'mid_level_correction';
      setDetailModal(prev => ({
        ...prev,
        criterion: {
          ...prev.criterion,
          [correctionField]: score
        }
      }));
      
      // Перезагружаем данные
      await fetchData();
    } catch (err) {
      logger.error('Ошибка сохранения корректировки:', err);
      throw new Error(err.response?.data?.message || 'Ошибка при сохранении корректировки');
    }
  };

  // Переключение раскрытия группы
  const toggleManager = (managerName) => {
    setExpandedManagers(prev => ({
      ...prev,
      [managerName]: !prev[managerName]
    }));
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка данных подчинённых..." />;
  }

  // Ошибка
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-red-900 mb-2">Ошибка загрузки</h2>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={fetchData}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <RefreshCw className="w-5 h-5" />
              Повторить
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Если нет подчинённых
  if (employees.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Users className="w-8 h-8 text-teal-600" />
              Оценки команды
            </h1>
            <p className="text-gray-600 mt-2">
              Корректировка оценок сотрудников ваших подчинённых менеджеров
            </p>
          </div>

          <PeriodBanner
            period={period}
            campaignActive={campaignActive}
            emptyCopy="Нет активного периода — матрица не смешивает строки."
            draftName={periodCatalog.find((item) => item.status === 'draft')?.name}
          />
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Users className="w-10 h-10 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              Нет данных для отображения
            </h2>
            <p className="text-gray-600">
              У ваших подчинённых менеджеров пока нет оценённых сотрудников, 
              или у вас нет подчинённых с правами менеджера.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Users className="w-8 h-8 text-teal-600" />
          Оценки команды
        </h1>
        <p className="text-gray-600 mt-2">
          Корректировка оценок сотрудников ваших подчинённых менеджеров. 
          Нажмите на оценку для просмотра деталей и добавления корректировки.
        </p>
      </div>

      <PeriodBanner
        period={period}
        campaignActive={campaignActive}
        emptyCopy="Нет активного периода — матрица не смешивает строки."
        draftName={periodCatalog.find((item) => item.status === 'draft')?.name}
      />

      {/* Фильтры */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-gray-600">
            <Filter className="w-5 h-5" />
            <span className="font-medium">Фильтр:</span>
          </div>
          
          <select
            value={filterManager}
            onChange={(e) => setFilterManager(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          >
            <option value="">Все менеджеры</option>
            {uniqueManagers.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          
          <div className="ml-auto text-sm text-gray-500">
            Всего сотрудников: <span className="font-semibold">{employees.length}</span>
          </div>
          
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Обновить
          </button>
        </div>
      </div>

      {/* Таблицы по менеджерам */}
      <div className="space-y-6">
        {Object.entries(filteredGroups).map(([managerName, managerEmployees]) => {
          if (!managerEmployees || managerEmployees.length === 0) return null;
          
          const isExpanded = expandedManagers[managerName];
          
          return (
            <div key={managerName} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              {/* Header группы */}
              <button
                onClick={() => toggleManager(managerName)}
                className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-teal-50 to-cyan-50 hover:from-teal-100 hover:to-cyan-100 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-teal-500 rounded-lg flex items-center justify-center text-white font-bold">
                    {managerName.charAt(0)}
                  </div>
                  <div className="text-left">
                    <h3 className="font-bold text-gray-900">{managerName}</h3>
                    <p className="text-sm text-gray-600">
                      {managerEmployees.length} сотрудник{managerEmployees.length === 1 ? '' : managerEmployees.length < 5 ? 'а' : 'ов'}
                    </p>
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                )}
              </button>
              
              {/* Таблица */}
              {isExpanded && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                          Сотрудник
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                          Должность
                        </th>
                        <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                          Средний балл
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                          Критерии (нажмите для корректировки)
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {managerEmployees.map(employee => {
                        const criteria = employee.criteria || [];
                        const grouped = groupCriteria(criteria);
                        
                        // Вычисляем средний балл
                        const allScores = criteria
                          .filter(c => !c.c_level_only)
                          .map(c => getFinalScore(c))
                          .filter(s => s !== null);
                        const avgScore = allScores.length > 0 
                          ? (allScores.reduce((a, b) => a + b, 0) / allScores.length).toFixed(1)
                          : null;
                        
                        return (
                          <tr key={employee.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
                                  {employee.full_name?.charAt(0) || '?'}
                                </div>
                                <div>
                                  <div className="font-medium text-gray-900">{employee.full_name}</div>
                                  {employee.grade_code && (
                                    <div className="text-xs text-gray-500">{employee.grade_code}</div>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {employee.job_title || '-'}
                            </td>
                            <td className="px-4 py-3 text-center">
                              {avgScore !== null ? (
                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${getScoreStyle(parseFloat(avgScore))}`}>
                                  <TrendingUp className="w-4 h-4 mr-1" />
                                  {avgScore}
                                </span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-1">
                                {/* Основные критерии */}
                                {[...grouped.self, ...grouped.general].map(criterion => {
                                  const score = getFinalScore(criterion);
                                  const hasCorrection = criterion.mid_level_correction != null || criterion.c_level_correction != null;
                                  
                                  return (
                                    <button
                                      key={criterion.criteria_id}
                                      onClick={() => handleScoreClick(employee, criterion, 'general')}
                                      className={`
                                        px-2 py-1 rounded text-xs font-medium transition-all
                                        ${score !== null ? getScoreStyle(score) : 'bg-gray-100 text-gray-400'}
                                        ${hasCorrection ? 'ring-2 ring-teal-400 ring-offset-1' : ''}
                                        hover:scale-105 hover:shadow-md cursor-pointer
                                      `}
                                      title={`${criterion.criteria_title}${hasCorrection ? ' (есть корректировка)' : ''}`}
                                    >
                                      {score !== null ? score.toFixed(1) : '-'}
                                    </button>
                                  );
                                })}
                                
                                {/* Проектные критерии */}
                                {grouped.project.length > 0 && (
                                  <>
                                    <span className="text-gray-300 mx-1">|</span>
                                    {grouped.project.map(criterion => {
                                      const score = getFinalScore(criterion);
                                      const hasCorrection = criterion.mid_level_correction != null || criterion.c_level_correction != null;
                                      
                                      return (
                                        <button
                                          key={criterion.criteria_id}
                                          onClick={() => handleScoreClick(employee, criterion, 'project')}
                                          className={`
                                            px-2 py-1 rounded text-xs font-medium transition-all
                                            ${score !== null ? getScoreStyle(score) : 'bg-purple-100 text-purple-400'}
                                            ${hasCorrection ? 'ring-2 ring-teal-400 ring-offset-1' : ''}
                                            hover:scale-105 hover:shadow-md cursor-pointer
                                          `}
                                          title={`${criterion.criteria_title} (проект)${hasCorrection ? ' (есть корректировка)' : ''}`}
                                        >
                                          {score !== null ? score.toFixed(1) : '-'}
                                        </button>
                                      );
                                    })}
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Легенда */}
      <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <h4 className="font-semibold text-gray-700 mb-3">Легенда</h4>
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-green-100 flex items-center justify-center text-green-700 text-xs font-bold">8+</span>
            <span className="text-gray-600">Отлично</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-yellow-100 flex items-center justify-center text-yellow-700 text-xs font-bold">5-7</span>
            <span className="text-gray-600">Хорошо</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-orange-100 flex items-center justify-center text-orange-700 text-xs font-bold">3-4</span>
            <span className="text-gray-600">Требует улучшения</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-red-100 flex items-center justify-center text-red-700 text-xs font-bold">&lt;3</span>
            <span className="text-gray-600">Критично</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-gray-100 ring-2 ring-teal-400 flex items-center justify-center text-gray-600 text-xs font-bold">✓</span>
            <span className="text-gray-600">Есть корректировка</span>
          </div>
        </div>
      </div>

      {/* Модальное окно деталей */}
      <ScoreDetailModal
        isOpen={detailModal.isOpen}
        employee={detailModal.employee}
        criterion={detailModal.criterion}
        group={detailModal.group}
        user={{ ...user, has_manager_subordinates: true }}
        correctionLevel="mid_level"
        onClose={handleCloseModal}
        onCorrectionSubmit={handleScoreCorrection}
      />
    </div>
  );
};

export default ManagerSubordinatesMatrix;

