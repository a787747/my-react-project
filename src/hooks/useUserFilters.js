/**
 * useUserFilters - Хук для фильтрации пользователей
 * 
 * Назначение: Логика фильтрации и поиска по списку пользователей
 * Используется в: AdminUsers
 * 
 * Параметры:
 * - users: массив всех пользователей
 * - itemsPerPage: количество элементов на странице
 * 
 * Возвращает:
 * - filters: текущие фильтры
 * - searchInput: значение поля поиска
 * - currentPage: текущая страница
 * - filteredUsers: отфильтрованный список
 * - paginatedUsers: список для текущей страницы
 * - totalPages: общее количество страниц
 * - setSearchInput: установить поиск
 * - handleFilterChange: изменить фильтр
 * - resetFilters: сбросить фильтры
 * - setCurrentPage: установить страницу
 */

import { useState, useEffect, useMemo } from 'react';
import { UI_CONFIG } from '../config/constants';

// Начальные значения фильтров
const initialFilters = {
  search: '',
  role: 'all',
  department_id: 'all',
  manager_id: 'all',
  work_category: 'all'
};

export const useUserFilters = (users = [], itemsPerPage = UI_CONFIG.ITEMS_PER_PAGE) => {
  const [filters, setFilters] = useState(initialFilters);
  const [searchInput, setSearchInput] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Debounce для поиска - обновляем фильтр через 300мс после ввода
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters(prev => ({ ...prev, search: searchInput }));
      setCurrentPage(1); // Сброс на первую страницу при новом поиске
    }, UI_CONFIG.DEBOUNCE_DELAY);

    return () => clearTimeout(timer);
  }, [searchInput]);

  // Фильтрация пользователей
  const filteredUsers = useMemo(() => {
    return users.filter(user => {
      // Поиск по имени и email
      const searchMatch = 
        user.full_name?.toLowerCase().includes(filters.search.toLowerCase()) ||
        user.email?.toLowerCase().includes(filters.search.toLowerCase());
      if (!searchMatch) return false;

      // Фильтр по роли
      if (filters.role !== 'all' && user.role !== filters.role) return false;
      
      // Фильтр по категории
      if (filters.work_category !== 'all' && user.work_category !== filters.work_category) return false;
      
      // Фильтр по отделу
      if (filters.department_id !== 'all' && String(user.department_id) !== String(filters.department_id)) return false;
      
      // Фильтр по менеджеру
      if (filters.manager_id !== 'all' && String(user.manager_id) !== String(filters.manager_id)) return false;

      return true;
    });
  }, [users, filters]);

  // Пагинация
  const totalPages = Math.ceil(filteredUsers.length / itemsPerPage);
  
  const paginatedUsers = useMemo(() => {
    return filteredUsers.slice(
      (currentPage - 1) * itemsPerPage,
      currentPage * itemsPerPage
    );
  }, [filteredUsers, currentPage, itemsPerPage]);

  // Обработчик изменения фильтра
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Сброс на первую страницу
  };

  // Сброс всех фильтров
  const resetFilters = () => {
    setFilters(initialFilters);
    setSearchInput('');
    setCurrentPage(1);
  };

  return {
    filters,
    searchInput,
    currentPage,
    filteredUsers,
    paginatedUsers,
    totalPages,
    setSearchInput,
    handleFilterChange,
    resetFilters,
    setCurrentPage
  };
};

export default useUserFilters;

