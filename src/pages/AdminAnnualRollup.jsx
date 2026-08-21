/**
 * AdminAnnualRollup - Годовые итоги по контейнерному периоду
 *
 * Назначение: Свод сохранённых результатов закрытых дочерних периодов
 *             контейнера: итог каждого периода, годовой рейтинг (среднее
 *             по периодам в охвате), годовой индекс (сумма индексов).
 * Доступ: admin, c_level (ReportingRoute; API — admin + c_level, D-0820-11)
 *
 * Числа приходят с сервера из period_results (снимок на момент закрытия);
 * живые данные (веса, грейды, коэффициенты) на эту страницу не влияют.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { CalendarRange, Loader2, AlertCircle, Info } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { cellState, cellLabel, formatRating, formatIndex, CELL_STATES } from '../utils/annualRollup';
import handleApiError from '../utils/errorHandler';
import logger from '../utils/logger';

const STATUS_BADGES = {
  closed: { text: 'закрыт', className: 'bg-gray-200 text-gray-700' },
  active: { text: 'активен', className: 'bg-green-100 text-green-700' },
  draft: { text: 'черновик', className: 'bg-amber-100 text-amber-700' },
};

const CELL_BADGES = {
  [CELL_STATES.NOT_CLOSED]: 'bg-amber-50 text-amber-600 border border-amber-200',
  [CELL_STATES.CLOSED_NO_RESULTS]: 'bg-red-50 text-red-500 border border-red-200',
  [CELL_STATES.OUT_OF_SCOPE]: 'bg-gray-100 text-gray-400',
  [CELL_STATES.NO_DATA]: 'bg-orange-50 text-orange-500 border border-orange-200',
};

const AdminAnnualRollup = () => {
  const [containers, setContainers] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingRollup, setLoadingRollup] = useState(false);
  const [rollup, setRollup] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    apiClient.get(API_ENDPOINTS.PERIODS)
      .then((response) => {
        if (cancelled) return;
        const all = response.data?.data || [];
        const withChildren = all.filter((p) => Number(p.child_count) > 0);
        setContainers(withChildren);
        if (withChildren.length === 1) {
          setSelectedId(String(withChildren[0].id));
        }
      })
      .catch((err) => {
        if (!cancelled) setError(handleApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => { cancelled = true; };
  }, []);

  const fetchRollup = useCallback(async (containerId) => {
    if (!containerId) {
      setRollup(null);
      return;
    }
    try {
      setLoadingRollup(true);
      setError('');
      const response = await apiClient.get(
        `${API_ENDPOINTS.PERIODS_ANNUAL_ROLLUP}?container_id=${containerId}`
      );
      setRollup(response.data);
    } catch (err) {
      logger.error('Ошибка загрузки годовой сводки:', err);
      setRollup(null);
      setError(handleApiError(err));
    } finally {
      setLoadingRollup(false);
    }
  }, []);

  useEffect(() => {
    fetchRollup(selectedId);
  }, [selectedId, fetchRollup]);

  const children = rollup?.children || [];
  const rows = rollup?.rows || [];
  const hasClosedResults = children.some((c) => c.status === 'closed' && c.has_results);

  if (loadingCatalog) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <CalendarRange className="w-8 h-8 text-indigo-600" />
          Годовые итоги
        </h1>
        <p className="text-gray-500 mt-2">
          Сохранённые результаты закрытых периодов внутри контейнера. Годовой рейтинг —
          среднее по периодам в охвате; годовой индекс — сумма индексов периодов.
        </p>
      </div>

      {containers.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-500">
          <CalendarRange className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p className="font-medium text-gray-600">Контейнерных периодов пока нет</p>
          <p className="text-sm mt-1">
            Создайте годовой период на странице «Периоды» и привяжите к нему полугодия.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6 flex items-center gap-3">
            <label className="text-sm font-medium text-gray-600">Контейнер:</label>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none min-w-[260px]"
            >
              <option value="">— выберите контейнер —</option>
              {containers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {loadingRollup && <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {rollup && !hasClosedResults && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-500">
              <Info className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="font-medium text-gray-600">
                Ни один дочерний период ещё не закрыт
              </p>
              <p className="text-sm mt-1">
                Годовые значения появятся после закрытия периодов —
                сводка не показывает живые (незафиксированные) числа.
              </p>
              {children.length > 0 && (
                <p className="text-sm mt-3 text-gray-400">
                  Дочерние периоды: {children.map((c) => `${c.name} (${STATUS_BADGES[c.status]?.text || c.status})`).join(', ')}
                </p>
              )}
            </div>
          )}

          {rollup && hasClosedResults && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase sticky left-0 bg-gray-50 z-10">
                        Сотрудник
                      </th>
                      {children.map((child) => (
                        <th key={child.id} className="px-4 py-4 text-center border-l border-gray-100">
                          <div className="text-xs font-semibold text-gray-600">{child.name}</div>
                          <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_BADGES[child.status]?.className || 'bg-gray-100 text-gray-500'}`}>
                            {STATUS_BADGES[child.status]?.text || child.status}
                          </span>
                        </th>
                      ))}
                      <th className="px-4 py-4 text-center border-l-2 border-indigo-100 bg-indigo-50/50">
                        <div className="text-xs font-semibold text-indigo-700">Годовой рейтинг</div>
                        <div className="text-[10px] text-indigo-400 font-normal">среднее по охвату</div>
                      </th>
                      <th className="px-4 py-4 text-center border-l border-indigo-100 bg-indigo-50/50">
                        <div className="text-xs font-semibold text-indigo-700">Годовой индекс</div>
                        <div className="text-[10px] text-indigo-400 font-normal">сумма индексов</div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={children.length + 3} className="px-6 py-10 text-center text-gray-500">
                          Нет сотрудников с сохранёнными результатами в этом контейнере
                        </td>
                      </tr>
                    ) : (
                      rows.map((person) => (
                        <tr key={person.user_id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                          <td className="px-6 py-3 sticky left-0 bg-white z-10">
                            <div className="font-medium text-gray-900">{person.full_name}</div>
                            <div className="text-xs text-gray-500">
                              {person.department_name && <span>{person.department_name}</span>}
                              {person.grade_code && <span className="ml-1 text-indigo-600">• {person.grade_code}</span>}
                            </div>
                          </td>
                          {children.map((child) => {
                            const cell = cellState(child, (person.results || {})[child.id]);
                            return (
                              <td key={child.id} className="px-4 py-3 text-center border-l border-gray-50">
                                {cell.state === CELL_STATES.OK ? (
                                  <div>
                                    <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 font-bold">
                                      {formatRating(cell.final_rating)}
                                    </span>
                                    {cell.bonus_index !== null && (
                                      <div className="text-[10px] text-gray-400 mt-1">
                                        индекс {formatIndex(cell.bonus_index)}
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  <span className={`inline-block px-2 py-1 rounded-lg text-xs ${CELL_BADGES[cell.state] || 'bg-gray-100 text-gray-400'}`}>
                                    {cellLabel(cell.state)}
                                  </span>
                                )}
                              </td>
                            );
                          })}
                          <td className="px-4 py-3 text-center border-l-2 border-indigo-100 bg-indigo-50/30">
                            <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-indigo-100 text-indigo-800 font-bold">
                              {formatRating(person.annual_rating)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center border-l border-indigo-100 bg-indigo-50/30">
                            <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-indigo-100 text-indigo-800 font-bold">
                              {formatIndex(person.annual_index)}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 text-xs text-gray-500">
                «Вне охвата» не участвует в среднем (ноль не подставляется). «Нет данных» — человек
                был в охвате, но не был оценён; исключён из среднего, но виден. Значения зафиксированы
                при закрытии периода и не меняются при правках весов и коэффициентов.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AdminAnnualRollup;
