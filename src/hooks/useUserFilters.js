/**
 * useUserFilters - Хук для фильтрации пользователей
 * 
 * Назначение: Логика фильтрации и поиска по списку пользователей
 * Используется в: AdminUsers, TeamView
 * 
 * Параметры:
 * - users: массив всех пользователей (популяция, видимая текущей роли)
 * - itemsPerPage: количество элементов на странице
 * 
 * Возвращает:
 * - filters: текущие фильтры
 * - searchInput: значение поля поиска
 * - currentPage: текущая страница
 * - filteredUsers: отфильтрованный список (порядок API; счётчик «Найдено»)
 * - paginatedUsers: список для текущей страницы (уже отсортированный)
 * - totalPages: общее количество страниц
 * - facets: варианты выбора каждого контрола со счётчиками (см. utils/userFilters)
 * - counts: все числа заголовка, каждое над своей популяцией
 * - activeFilterCount: сколько контролов уведены от значения по умолчанию
 * - sortField / sortDirection: текущая сортировка (null = порядок API)
 * - setSearchInput: установить поиск
 * - handleFilterChange: изменить фильтр
 * - handleSort: переключить сортировку по колонке
 * - resetFilters: сбросить фильтры и сортировку
 * - setCurrentPage: установить страницу
 *
 * Сама логика «подходит ли человек» живёт в utils/userFilters.js — один
 * предикат на фильтрацию, счётчики и списки опций, чтобы они не разъезжались.
 */

import { useState, useEffect, useMemo } from 'react';
import { UI_CONFIG } from '../config/constants';
import { DEFAULT_SORT_DIRECTION, DEFAULT_SORT_FIELD, sortUsers } from '../utils/userSort';
import {
  INITIAL_FILTERS,
  buildCounts,
  buildFacets,
  countActiveFilters,
  filterUsers,
} from '../utils/userFilters';

export const useUserFilters = (users = [], itemsPerPage = UI_CONFIG.ITEMS_PER_PAGE) => {
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [searchInput, setSearchInput] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  // D-0825-11: the list opens sorted by name, A→Z. Until 2026-08-25 the initial
  // sortField was null, which made `sortUsers` return the array untouched, so
  // the table opened in the route's own `ORDER BY u.id DESC` — newest employee
  // first, an order nothing on screen explained and no header showed as active.
  const [sortField, setSortField] = useState(DEFAULT_SORT_FIELD);
  const [sortDirection, setSortDirection] = useState(DEFAULT_SORT_DIRECTION);

  // Debounce для поиска - обновляем фильтр через 300мс после ввода
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters(prev => ({ ...prev, search: searchInput }));
      setCurrentPage(1); // Сброс на первую страницу при новом поиске
    }, UI_CONFIG.DEBOUNCE_DELAY);

    return () => clearTimeout(timer);
  }, [searchInput]);

  const filteredUsers = useMemo(() => filterUsers(users, filters), [users, filters]);

  const facets = useMemo(() => buildFacets(users, filters), [users, filters]);

  const counts = useMemo(
    () => buildCounts(users, filters, filteredUsers),
    [users, filters, filteredUsers]
  );

  const activeFilterCount = useMemo(() => countActiveFilters(filters), [filters]);

  const sortedUsers = useMemo(
    () => sortUsers(filteredUsers, sortField, sortDirection),
    [filteredUsers, sortField, sortDirection]
  );

  // Пагинация
  const totalPages = Math.ceil(filteredUsers.length / itemsPerPage);
  
  const paginatedUsers = useMemo(() => {
    return sortedUsers.slice(
      (currentPage - 1) * itemsPerPage,
      currentPage * itemsPerPage
    );
  }, [sortedUsers, currentPage, itemsPerPage]);

  // Обработчик изменения фильтра
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Сброс на первую страницу
  };

  // Сброс всех фильтров. employment возвращается в 'active', а не в 'all' —
  // это его значение по умолчанию (D-0825-7).
  const resetFilters = () => {
    setFilters(INITIAL_FILTERS);
    setSearchInput('');
    setSortField(DEFAULT_SORT_FIELD);
    setSortDirection(DEFAULT_SORT_DIRECTION);
    setCurrentPage(1);
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  return {
    filters,
    searchInput,
    currentPage,
    filteredUsers,
    paginatedUsers,
    totalPages,
    facets,
    counts,
    activeFilterCount,
    sortField,
    sortDirection,
    setSearchInput,
    handleFilterChange,
    handleSort,
    resetFilters,
    setCurrentPage
  };
};

export default useUserFilters;
