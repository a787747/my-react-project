/**
 * EmployeeSelector - Мультиселект для выбора сотрудников
 * 
 * Назначение: Выбор одного или нескольких сотрудников из списка с поиском
 * Используется в: AdminScoreCalculator
 * 
 * Props:
 * - employees: Array - список сотрудников [{id, full_name, department_name, grade_code}]
 * - selected: Array - массив ID выбранных сотрудников
 * - onChange: Function - callback при изменении выбора
 * - placeholder: String - placeholder для поля поиска
 */

import React, { useState, useRef, useEffect } from 'react';
import { Search, X, ChevronDown, Users } from 'lucide-react';

const EmployeeSelector = ({ 
  employees = [], 
  selected = [], 
  onChange,
  placeholder = "Найти сотрудника..."
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // Закрытие при клике вне компонента
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Фильтрация сотрудников по поисковому запросу
  const filteredEmployees = employees.filter(emp => {
    // Если запрос пустой - показываем всех
    if (!searchQuery.trim()) return true;
    
    const query = searchQuery.toLowerCase().trim();
    return (
      emp.full_name?.toLowerCase().includes(query) ||
      emp.department_name?.toLowerCase().includes(query) ||
      emp.grade_code?.toLowerCase().includes(query) ||
      emp.job_title?.toLowerCase().includes(query)
    );
  });

  // Добавить/удалить сотрудника из выбранных
  const toggleEmployee = (employeeId) => {
    if (selected.includes(employeeId)) {
      onChange(selected.filter(id => id !== employeeId));
    } else {
      onChange([...selected, employeeId]);
    }
  };

  // Удалить сотрудника из выбранных (по тегу)
  const removeEmployee = (employeeId, e) => {
    e.stopPropagation();
    onChange(selected.filter(id => id !== employeeId));
  };

  // Очистить все выбранные
  const clearAll = (e) => {
    e.stopPropagation();
    onChange([]);
    setSearchQuery('');
  };

  // Выбрать всех отфильтрованных
  const selectAll = () => {
    const allIds = filteredEmployees.map(e => e.id);
    const newSelected = [...new Set([...selected, ...allIds])];
    onChange(newSelected);
  };

  // Получить данные сотрудника по ID
  const getEmployeeById = (id) => employees.find(e => e.id === id);

  return (
    <div ref={containerRef} className="relative">
      {/* Основной контейнер */}
      <div
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) {
            setTimeout(() => inputRef.current?.focus(), 100);
          }
        }}
        className={`
          min-h-[52px] px-4 py-2 bg-white border rounded-xl cursor-pointer
          flex items-center flex-wrap gap-2 transition-all
          ${isOpen 
            ? 'border-indigo-500 ring-2 ring-indigo-100' 
            : 'border-gray-200 hover:border-gray-300'
          }
        `}
      >
        {/* Иконка поиска */}
        <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
        
        {/* Выбранные сотрудники как теги */}
        {selected.map(id => {
          const emp = getEmployeeById(id);
          if (!emp) return null;
          return (
            <span
              key={id}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 text-indigo-700 text-sm font-medium rounded-lg"
            >
              <span className="max-w-[150px] truncate">{emp.full_name}</span>
              <button
                onClick={(e) => removeEmployee(id, e)}
                className="p-0.5 hover:bg-indigo-200 rounded transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          );
        })}
        
        {/* Поле ввода для поиска */}
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(true);
          }}
          placeholder={selected.length === 0 ? placeholder : "Добавить ещё..."}
          className="flex-1 min-w-[120px] outline-none text-sm text-gray-700 placeholder:text-gray-400 bg-transparent"
        />
        
        {/* Кнопки справа */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {selected.length > 0 && (
            <button
              onClick={clearAll}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
              title="Очистить всё"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </div>
      
      {/* Счётчик выбранных */}
      {selected.length > 0 && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-indigo-600 text-white text-xs font-bold rounded-full">
          {selected.length}
        </div>
      )}

      {/* Выпадающий список */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden">
          {/* Хедер выпадающего списка */}
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              Найдено: {filteredEmployees.length} из {employees.length}
            </span>
            {filteredEmployees.length > 0 && (
              <button
                onClick={selectAll}
                className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Выбрать всех
              </button>
            )}
          </div>
          
          {/* Список сотрудников */}
          <div className="max-h-64 overflow-y-auto">
            {filteredEmployees.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <Users className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">Сотрудники не найдены</p>
              </div>
            ) : (
              filteredEmployees.map(emp => {
                const isSelected = selected.includes(emp.id);
                return (
                  <div
                    key={emp.id}
                    onClick={() => toggleEmployee(emp.id)}
                    className={`
                      px-4 py-3 cursor-pointer border-b border-gray-50 last:border-0
                      flex items-center gap-3 transition-colors
                      ${isSelected 
                        ? 'bg-indigo-50 hover:bg-indigo-100' 
                        : 'hover:bg-gray-50'
                      }
                    `}
                  >
                    {/* Чекбокс */}
                    <div className={`
                      w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-all
                      ${isSelected 
                        ? 'bg-indigo-600 border-indigo-600' 
                        : 'border-gray-300'
                      }
                    `}>
                      {isSelected && (
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    
                    {/* Информация о сотруднике */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium truncate ${isSelected ? 'text-indigo-900' : 'text-gray-900'}`}>
                        {emp.full_name}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {emp.department_name}
                        {emp.grade_code && <span className="ml-2 text-gray-400">• {emp.grade_code}</span>}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default EmployeeSelector;

