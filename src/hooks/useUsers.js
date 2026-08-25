/**
 * useUsers - Хук для управления пользователями
 * 
 * Назначение: Загрузка списка пользователей, сохранение и управление состоянием
 * Используется в: AdminUsers
 * 
 * Возвращает:
 * - users: массив пользователей
 * - options: опции для селектов (отделы, грейды, менеджеры)
 * - loading: статус загрузки
 * - saving: статус сохранения
 * - fetchData: функция перезагрузки данных
 * - saveUser: функция сохранения пользователя
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useUsers = () => {
  const [users, setUsers] = useState([]);
  const [options, setOptions] = useState({ 
    departments: [], 
    grades: [], 
    managers: [] 
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Загрузка данных. silent=true after a row save: keep the table mounted
  // so sort, filters, page, and window scroll are not reset.
  const fetchData = useCallback(async ({ silent = false } = {}) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      
      const res = await apiClient.get(API_ENDPOINTS.ADMIN_USERS_DATA);
      const data = res.data; 
      
      setUsers(data.users || []);
      setOptions({
        departments: data.options?.departments || [],
        grades: data.options?.grades || [],
        managers: data.options?.managers || []
      });
    } catch (err) {
      logger.error('Ошибка загрузки пользователей:', err);
      setError('Не удалось загрузить список пользователей');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Сохранение пользователя
  const saveUser = useCallback(async (userData, existingUserId = null) => {
    try {
      setSaving(true);
      
      const payload = { ...userData };
      if (existingUserId) {
        payload.id = existingUserId;
      }

      await apiClient.post(API_ENDPOINTS.ADMIN_SAVE_USER, payload);
      
      // Silent reload: a full-page spinner would unmount the table and jump to top
      await fetchData({ silent: true });
      
      return { success: true };
    } catch (err) {
      logger.error('Ошибка сохранения:', err);
      return { success: false, error: 'Ошибка при сохранении. Попробуйте снова.' };
    } finally {
      setSaving(false);
    }
  }, [fetchData]);

  // Увольнение (D-0825-7). Состояние, не удаление: ни одна строка оценок не
  // трогается, ничего не пересчитывается. Сервер отказывает, если у сотрудника
  // остались прямые подчинённые, и его сообщение показывается как есть.
  const terminateUser = useCallback(async (userId, terminationDate, note = '') => {
    try {
      setSaving(true);
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN_TERMINATE_EMPLOYEE, {
        user_id: userId,
        termination_date: terminationDate,
        note
      });
      await fetchData({ silent: true });
      return { success: true, data };
    } catch (err) {
      logger.error('Ошибка увольнения:', err);
      return { success: false, error: err.userMessage || 'Не удалось отметить увольнение' };
    } finally {
      setSaving(false);
    }
  }, [fetchData]);

  // Восстановление — обратная операция того же маршрута.
  const reinstateUser = useCallback(async (userId, note = '') => {
    try {
      setSaving(true);
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN_REINSTATE_EMPLOYEE, {
        user_id: userId,
        note
      });
      await fetchData({ silent: true });
      return { success: true, data };
    } catch (err) {
      logger.error('Ошибка восстановления:', err);
      return { success: false, error: err.userMessage || 'Не удалось восстановить сотрудника' };
    } finally {
      setSaving(false);
    }
  }, [fetchData]);

  // Массовый импорт пользователей
  const importUsers = useCallback(async (usersData) => {
    try {
      setSaving(true);
      
      // Сначала строим карту email -> manager_id для резолва руководителей
      // Карта email -> { id, manager_id } для сохранения связей
      const existingUsers = users.reduce((acc, u) => {
        acc[u.email.toLowerCase()] = { id: u.id, manager_id: u.manager_id };
        return acc;
      }, {});

      let successCount = 0;
      let errorCount = 0;
      const errors = [];

      // Импортируем по одному для лучшей обработки ошибок
      for (const userData of usersData) {
        try {
          const emailKey = userData.email.toLowerCase();
          const existingUser = existingUsers[emailKey];

          // Резолвим manager_id по email если указан
          let manager_id = existingUser?.manager_id ?? null;
          if (userData.manager_email) {
            const manager = existingUsers[userData.manager_email.toLowerCase()];
            if (manager?.id) {
              manager_id = manager.id;
            } else {
              // Попробуем найти среди уже импортированных
              const imported = usersData.find(
                u => u.email.toLowerCase() === userData.manager_email.toLowerCase() && u !== userData
              );
              if (imported) {
                // Будет обработано после первичного импорта
                manager_id = null;
              } else {
                // Не нашли — оставляем старого менеджера (если был) и фиксируем предупреждение
                manager_id = existingUser?.manager_id ?? null;
                userData._warning = `Руководитель не найден: ${userData.manager_email}`;
              }
            }
          }

          const payload = {
            // Игнорируем ID из файла: обновляем/создаём по уникальному email
            id: existingUser?.id,
            full_name: userData.full_name,
            email: userData.email,
            job_title: userData.job_title || '',
            role: userData.role || 'employee',
            work_category: userData.work_category || 'general',
            department_id: userData.department_id || null,
            grade_id: userData.grade_id || null,
            manager_id: manager_id
          };

          await apiClient.post(API_ENDPOINTS.ADMIN_SAVE_USER, payload);
          successCount++;
          
          // Добавляем в карту для последующих резолвов
          existingUsers[emailKey] = existingUsers[emailKey] || -1; // отмечаем как добавленного/обновлённого
        } catch (err) {
          errorCount++;
          errors.push({ email: userData.email, error: err.message });
          logger.error(`Ошибка импорта ${userData.email}:`, err);
        }
      }

      // Перезагружаем данные после импорта
      await fetchData();
      
      if (errorCount > 0) {
        return { 
          success: false, 
          error: `Импортировано ${successCount} из ${usersData.length}. Ошибок: ${errorCount}`,
          details: errors
        };
      }
      
      return { success: true, count: successCount };
    } catch (err) {
      logger.error('Ошибка массового импорта:', err);
      return { success: false, error: 'Ошибка при импорте. Попробуйте снова.' };
    } finally {
      setSaving(false);
    }
  }, [fetchData, users]);

  // Загружаем данные при монтировании
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    users,
    options,
    loading,
    saving,
    error,
    fetchData,
    saveUser,
    terminateUser,
    reinstateUser,
    importUsers
  };
};

export default useUsers;

