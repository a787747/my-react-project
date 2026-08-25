/**
 * Analytics - Страница аналитики
 * 
 * Назначение: Отображение статистики и сравнение по отделам
 * Доступ: admin, c_level
 * 
 * Функционал:
 * - Карточки с общей статистикой
 * - Сравнение отделов по среднему баллу
 * - Детальная таблица по отделам
 * - Распределение оценок по грейдам
 * - Топ лучших и требующих внимания сотрудников
 */

import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { 
  BarChart3, 
  Users, 
  Award, 
  Loader2, 
  ArrowUp, 
  ArrowDown,
  Building2,
  Target,
  TrendingUp,
  Percent,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend
} from 'recharts';
import { API_ENDPOINTS } from '../config/api';
import { PeriodBanner } from '../components/common';
import logger from '../utils/logger';

// Цвета для графиков
const COLORS = {
  excellent: '#10b981', // green
  good: '#3b82f6',      // blue
  average: '#f59e0b',   // amber
  poor: '#ef4444'       // red
};

// Получить цвет по баллу
const getScoreColor = (score) => {
  if (score >= 8) return COLORS.excellent;
  if (score >= 6) return COLORS.good;
  if (score >= 5) return COLORS.average;
  return COLORS.poor;
};

// Получить зону по баллу (department averages — default quality scale)
const getScoreZone = (score) => {
  if (score >= 8) return { label: 'Отлично', color: 'text-green-600', bg: 'bg-green-100' };
  if (score >= 6) return { label: 'Хорошо', color: 'text-blue-600', bg: 'bg-blue-100' };
  if (score >= 5) return { label: 'В целом справляется, требует внимания', color: 'text-amber-600', bg: 'bg-amber-100' };
  if (score >= 4) return { label: 'Ниже ожиданий', color: 'text-orange-600', bg: 'bg-orange-100' };
  return { label: 'Низко', color: 'text-red-600', bg: 'bg-red-100' };
};

const Analytics = () => {
  const [data, setData] = useState(null);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);
  const [periodCatalog, setPeriodCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: 'avg_score', direction: 'desc' });

  useEffect(() => {
    fetchAnalytics();
    apiClient.get(API_ENDPOINTS.PERIODS)
      .then((response) => setPeriodCatalog(response.data?.data || []))
      .catch(() => setPeriodCatalog([]));
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(API_ENDPOINTS.ANALYTICS);
      setData(response.data.data);
      setPeriod(response.data.period || null);
      setCampaignActive(Boolean(response.data.campaign_active));
      setError(null);
    } catch (err) {
      logger.error('Ошибка загрузки аналитики:', err);
      // Если ошибка 500 - скорее всего нет данных, показываем пустое состояние
      if (err.message?.includes('500') || err.message?.includes('Внутренняя ошибка')) {
        setData({
          overall: {
            total_evaluations: 0,
            company_avg_score: 0,
            total_employees: 0,
            active_evaluators: 0
          },
          departments: [],
          top_performers: [],
          low_performers: [],
          period_trends: []
        });
        setError(null);
      } else {
        setError('Не удалось загрузить данные');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Загрузка аналитики...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-8 h-8 text-red-600" />
          </div>
          <div className="text-xl text-red-600 font-medium">{error}</div>
        </div>
      </div>
    );
  }

  const { overall, departments = [], top_performers = [], low_performers = [] } = data || {};

  // Проверка на пустые данные (нет оценок)
  const hasNoEvaluations = !overall?.total_evaluations || parseInt(overall.total_evaluations) === 0;

  // Если нет оценок - показываем пустое состояние
  if (hasNoEvaluations) {
    return (
      <div className="p-6 lg:p-8 bg-slate-50 min-h-screen">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Аналитика по отделам</h1>
          <p className="text-slate-600">Сравнение показателей и средние баллы подразделений</p>
        </div>

        <PeriodBanner
          period={period}
          campaignActive={campaignActive}
          emptyCopy="Нет активного периода — аналитика не смешивает циклы."
          draftName={periodCatalog.find((item) => item.status === 'draft')?.name}
        />

        {/* Пустое состояние */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-12">
          <div className="text-center max-w-md mx-auto">
            <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <BarChart3 className="w-10 h-10 text-indigo-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-3">Пока нет данных для аналитики</h2>
            <p className="text-slate-600 mb-6">
              Аналитика станет доступна после того, как будут проведены первые оценки сотрудников. 
              Начните оценивать сотрудников, чтобы видеть статистику по отделам.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
                <div className="text-left">
                  <div className="text-2xl font-bold text-slate-900">0</div>
                  <div className="text-xs text-slate-500">Оценок</div>
                </div>
              </div>
              <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-purple-600" />
                </div>
                <div className="text-left">
                  <div className="text-2xl font-bold text-slate-900">0</div>
                  <div className="text-xs text-slate-500">Сотрудников оценено</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Подготовка данных для графика по отделам (отсортировано по баллу)
  const deptChartData = [...departments]
    .sort((a, b) => parseFloat(b.avg_score) - parseFloat(a.avg_score))
    .map(dept => ({
      name: dept.department,
      score: parseFloat(dept.avg_score),
      count: parseInt(dept.employee_count || 0),
      fullName: dept.department
    }));

  // Сортировка таблицы отделов
  const sortedDepartments = [...departments].sort((a, b) => {
    let aVal = a[sortConfig.key];
    let bVal = b[sortConfig.key];
    
    if (sortConfig.key === 'avg_score' || sortConfig.key === 'employee_count') {
      aVal = parseFloat(aVal) || 0;
      bVal = parseFloat(bVal) || 0;
    }
    
    if (sortConfig.direction === 'asc') {
      return aVal > bVal ? 1 : -1;
    }
    return aVal < bVal ? 1 : -1;
  });

  // Обработчик сортировки
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  // Иконка сортировки
  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return null;
    return sortConfig.direction === 'desc' 
      ? <ChevronDown className="w-4 h-4 inline ml-1" />
      : <ChevronUp className="w-4 h-4 inline ml-1" />;
  };

  // Подсчёт распределения по зонам
  const scoreDistribution = departments.reduce((acc, dept) => {
    const score = parseFloat(dept.avg_score);
    if (score >= 8) acc.excellent++;
    else if (score >= 6) acc.good++;
    else if (score >= 4) acc.average++;
    else acc.poor++;
    return acc;
  }, { excellent: 0, good: 0, average: 0, poor: 0 });

  const distributionData = [
    { name: 'Отлично (8-10)', value: scoreDistribution.excellent, color: COLORS.excellent },
    { name: 'Хорошо (6-8)', value: scoreDistribution.good, color: COLORS.good },
    { name: 'Средне (4-6)', value: scoreDistribution.average, color: COLORS.average },
    { name: 'Требует внимания (<4)', value: scoreDistribution.poor, color: COLORS.poor }
  ].filter(d => d.value > 0);

  // Средний балл компании (число)
  const companyAvg = parseFloat(overall.company_avg_score) || 0;
  const companyZone = getScoreZone(companyAvg);

  return (
    <div className="p-6 lg:p-8 bg-slate-50 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Аналитика по отделам</h1>
        <p className="text-slate-600">Сравнение показателей и средние баллы подразделений. Числа — одного периода.</p>
      </div>

      <PeriodBanner
        period={period}
        campaignActive={campaignActive}
        emptyCopy="Нет активного периода — аналитика не смешивает циклы."
        draftName={periodCatalog.find((item) => item.status === 'draft')?.name}
      />

      {/* Главные метрики */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Средний балл компании */}
        <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
              <Target className="w-6 h-6 text-indigo-600" />
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${companyZone.bg} ${companyZone.color}`}>
              {companyZone.label}
            </span>
          </div>
          <div className="text-4xl font-bold text-slate-900 mb-1">{overall.company_avg_score}</div>
          <div className="text-sm text-slate-500">Средний балл компании</div>
        </div>

        {/* Оценено сотрудников */}
        <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div className="text-4xl font-bold text-slate-900 mb-1">{overall.total_employees}</div>
          <div className="text-sm text-slate-500">Оценено сотрудников</div>
        </div>

        {/* Количество отделов */}
        <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <Building2 className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <div className="text-4xl font-bold text-slate-900 mb-1">{departments.length}</div>
          <div className="text-sm text-slate-500">Отделов в системе</div>
        </div>

        {/* Всего оценок */}
        <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <Award className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <div className="text-4xl font-bold text-slate-900 mb-1">{overall.total_evaluations}</div>
          <div className="text-sm text-slate-500">Всего оценок</div>
        </div>
      </div>

      {/* Основной график - Средний балл по отделам */}
      <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200 mb-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Средний балл по отделам</h2>
            <p className="text-sm text-slate-500 mt-1">Сравнение подразделений от лучшего к худшему</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.excellent }} />
              <span className="text-slate-600">8–10</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.good }} />
              <span className="text-slate-600">6–7 Хорошо</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.average }} />
              <span className="text-slate-600">5 — требует внимания</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.poor }} />
              <span className="text-slate-600">&lt;5</span>
            </div>
          </div>
        </div>
        
        <ResponsiveContainer width="100%" height={Math.max(300, deptChartData.length * 50)}>
          <BarChart 
            data={deptChartData} 
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
            <XAxis type="number" domain={[0, 10]} tickCount={11} />
            <YAxis 
              type="category" 
              dataKey="name" 
              width={150}
              tick={{ fontSize: 12 }}
            />
            <Tooltip 
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-3 rounded-lg shadow-lg border border-slate-200">
                      <p className="font-semibold text-slate-900">{data.fullName}</p>
                      <p className="text-sm text-slate-600">
                        Средний балл: <span className="font-bold" style={{ color: getScoreColor(data.score) }}>
                          {data.score.toFixed(2)}
                        </span>
                      </p>
                      {data.count > 0 && (
                        <p className="text-sm text-slate-500">Сотрудников: {data.count}</p>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar 
              dataKey="score" 
              radius={[0, 4, 4, 0]}
              barSize={30}
            >
              {deptChartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getScoreColor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Таблица отделов и Распределение */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Детальная таблица отделов */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-6 border-b border-slate-200">
            <h2 className="text-xl font-bold text-slate-900">Детализация по отделам</h2>
            <p className="text-sm text-slate-500 mt-1">Нажмите на заголовок для сортировки</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th 
                    className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => handleSort('department')}
                  >
                    Отдел <SortIcon columnKey="department" />
                  </th>
                  <th 
                    className="px-6 py-4 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => handleSort('avg_score')}
                  >
                    Ср. балл <SortIcon columnKey="avg_score" />
                  </th>
                  <th 
                    className="px-6 py-4 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => handleSort('employee_count')}
                  >
                    Сотрудников <SortIcon columnKey="employee_count" />
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Зона
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Отклонение
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedDepartments.map((dept, idx) => {
                  const score = parseFloat(dept.avg_score) || 0;
                  const zone = getScoreZone(score);
                  const deviation = score - companyAvg;
                  const isPositive = deviation >= 0;
                  
                  return (
                    <tr key={dept.department || idx} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div 
                            className="w-2 h-8 rounded-full" 
                            style={{ backgroundColor: getScoreColor(score) }} 
                          />
                          <span className="font-medium text-slate-900">{dept.department}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-xl font-bold" style={{ color: getScoreColor(score) }}>
                          {score.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center text-slate-600">
                        {dept.employee_count || '—'}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${zone.bg} ${zone.color}`}>
                          {zone.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`flex items-center justify-center gap-1 text-sm font-medium ${
                          isPositive ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {isPositive ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                          {Math.abs(deviation).toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Распределение по зонам */}
        <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
          <h2 className="text-xl font-bold text-slate-900 mb-2">Распределение отделов</h2>
          <p className="text-sm text-slate-500 mb-6">По зонам эффективности</p>
          
          {distributionData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={distributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {distributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              
              <div className="mt-4 space-y-3">
                {distributionData.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-sm text-slate-600">{item.name}</span>
                    </div>
                    <span className="font-semibold text-slate-900">{item.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-slate-500">
              Нет данных для отображения
            </div>
          )}
        </div>
      </div>

      {/* Лучшие и требующие внимания */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Лучшие сотрудники */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-green-50 to-emerald-50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">Лучшие сотрудники</h2>
                <p className="text-sm text-slate-500">Топ-5 по среднему баллу</p>
              </div>
            </div>
          </div>
          <div className="p-4">
            {top_performers && top_performers.length > 0 ? (
              <div className="space-y-3">
                {top_performers.slice(0, 5).map((emp, idx) => (
                  <div 
                    key={emp.id} 
                    className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-green-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 text-white rounded-xl flex items-center justify-center font-bold text-lg shadow-sm">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900">{emp.full_name}</div>
                        <div className="text-sm text-slate-500">{emp.job_title}</div>
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-green-600">{parseFloat(emp.score).toFixed(1)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                Нет данных о сотрудниках
              </div>
            )}
          </div>
        </div>

        {/* Требуют внимания */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-amber-50 to-orange-50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
                <ArrowDown className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">Требуют внимания</h2>
                <p className="text-sm text-slate-500">Сотрудники с низким баллом</p>
              </div>
            </div>
          </div>
          <div className="p-4">
            {low_performers && low_performers.length > 0 ? (
              <div className="space-y-3">
                {low_performers.slice(0, 5).map((emp, idx) => (
                  <div 
                    key={emp.id} 
                    className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-amber-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 text-white rounded-xl flex items-center justify-center font-bold text-lg shadow-sm">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900">{emp.full_name}</div>
                        <div className="text-sm text-slate-500">{emp.job_title}</div>
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-amber-600">{parseFloat(emp.score).toFixed(1)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                <div className="text-4xl mb-3">🎉</div>
                <div className="font-medium">Отлично!</div>
                <div className="text-sm">Все сотрудники показывают хорошие результаты</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
