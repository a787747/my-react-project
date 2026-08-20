/**
 * UserContext - Контекст для управления состоянием пользователя
 * 
 * Назначение: Централизованное управление данными пользователя
 * Используется в: App.jsx, Login.jsx, Sidebar.jsx, Profile.jsx и другие
 * 
 * Экспортирует:
 * - UserProvider - провайдер контекста
 * - useUser - хук для доступа к контексту
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import logger from '../utils/logger';

// Создаем контекст
const UserContext = createContext(null);

/**
 * Провайдер контекста пользователя
 * Оборачивает приложение и предоставляет доступ к данным пользователя
 */
export const UserProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Загрузка пользователя из localStorage при монтировании
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
      }
    } catch (error) {
      logger.error('Ошибка загрузки данных пользователя:', error);
      // Очищаем невалидные данные
      localStorage.removeItem('user');
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Обновляет данные пользователя в state и localStorage
   * @param {Object|null} userData - данные пользователя или null для logout
   * @param {string|null} token - токен авторизации (опционально)
   */
  const updateUser = useCallback((userData, token = null) => {
    setUser(userData);
    
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData));
      if (token) {
        localStorage.setItem('token', token);
      }
    } else {
      // Logout - очищаем всё
      localStorage.removeItem('user');
      localStorage.removeItem('token');
    }
  }, []);

  /**
   * Выход из системы
   */
  const logout = useCallback(() => {
    updateUser(null);
  }, [updateUser]);

  /**
   * Проверяет, авторизован ли пользователь
   * @returns {boolean}
   */
  const isAuthenticated = useCallback(() => {
    return !!user;
  }, [user]);

  /**
   * Проверяет, имеет ли пользователь указанную роль
   * @param {string|string[]} roles - роль или массив ролей
   * @returns {boolean}
   */
  const hasRole = useCallback((roles) => {
    if (!user) return false;
    const rolesArray = Array.isArray(roles) ? roles : [roles];
    return rolesArray.includes(user.role);
  }, [user]);

  const value = {
    user,
    loading,
    updateUser,
    logout,
    isAuthenticated,
    hasRole
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};

/**
 * Хук для доступа к контексту пользователя
 * @returns {{ user: Object|null, loading: boolean, updateUser: Function, logout: Function, isAuthenticated: Function, hasRole: Function }}
 */
export const useUser = () => {
  const context = useContext(UserContext);
  
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  
  return context;
};

export default UserContext;
