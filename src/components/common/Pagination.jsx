/**
 * Pagination - Компонент пагинации
 * 
 * Назначение: Навигация по страницам списка с большим количеством элементов
 * Используется в: AdminUsers, и другие таблицы с пагинацией
 * 
 * Props:
 * - currentPage: number - текущая страница (начиная с 1)
 * - totalPages: number - общее количество страниц
 * - totalItems: number - общее количество элементов
 * - itemsPerPage: number - элементов на странице
 * - onPageChange: function(page) - колбэк при смене страницы
 * 
 * Accessibility:
 * - nav element с aria-label
 * - aria-current для текущей страницы
 * - Правильные aria-labels для кнопок
 * - Screen reader text для многоточия
 * - Focus-visible стили
 */

import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const Pagination = ({ 
  currentPage, 
  totalPages, 
  totalItems, 
  itemsPerPage, 
  onPageChange 
}) => {
  // Не показываем пагинацию если страница одна
  if (totalPages <= 1) return null;

  // Вычисляем диапазон отображаемых элементов
  const startItem = ((currentPage - 1) * itemsPerPage) + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  // Генерируем номера страниц для отображения
  const renderPageNumbers = () => {
    const pages = [];
    
    for (let i = 1; i <= totalPages; i++) {
      // Показываем: первую, последнюю и страницы рядом с текущей
      if (
        i === 1 || 
        i === totalPages || 
        (i >= currentPage - 1 && i <= currentPage + 1)
      ) {
        pages.push(
          <button
            key={i}
            onClick={() => onPageChange(i)}
            className={`
              min-w-[2.5rem] h-10 px-3 rounded-lg text-sm font-semibold 
              transition-all duration-200
              focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2
              ${currentPage === i 
                ? 'bg-brand-600 text-white shadow-brand' 
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }
            `}
            aria-label={`Перейти на страницу ${i}`}
            aria-current={currentPage === i ? 'page' : undefined}
          >
            {i}
          </button>
        );
      } else if (i === currentPage - 2 || i === currentPage + 2) {
        // Добавляем многоточие
        pages.push(
          <span 
            key={i} 
            className="px-2 text-slate-400 select-none"
            aria-hidden="true"
          >
            ...
          </span>
        );
      }
    }
    
    return pages;
  };

  return (
    <nav 
      className="px-6 py-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4"
      aria-label="Пагинация"
    >
      {/* Информация о показанных элементах */}
      <p className="text-sm text-slate-600">
        Показано <span className="font-medium text-slate-900">{startItem}</span> - <span className="font-medium text-slate-900">{endItem}</span> из <span className="font-medium text-slate-900">{totalItems}</span>
      </p>
      
      {/* Навигация */}
      <div className="flex items-center gap-1.5" role="group" aria-label="Навигация по страницам">
        {/* Кнопка "Назад" */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className={`
            p-2.5 rounded-lg border transition-all duration-200
            focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2
            ${currentPage === 1 
              ? 'border-slate-200 text-slate-300 cursor-not-allowed' 
              : 'border-slate-200 text-slate-600 hover:bg-slate-100 hover:border-slate-300 hover:text-slate-900'
            }
          `}
          aria-label="Предыдущая страница"
          aria-disabled={currentPage === 1}
        >
          <ChevronLeft className="w-5 h-5" aria-hidden="true" />
        </button>
        
        {/* Номера страниц */}
        <div className="flex items-center gap-1">
          {renderPageNumbers()}
        </div>

        {/* Кнопка "Вперед" */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className={`
            p-2.5 rounded-lg border transition-all duration-200
            focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2
            ${currentPage === totalPages 
              ? 'border-slate-200 text-slate-300 cursor-not-allowed' 
              : 'border-slate-200 text-slate-600 hover:bg-slate-100 hover:border-slate-300 hover:text-slate-900'
            }
          `}
          aria-label="Следующая страница"
          aria-disabled={currentPage === totalPages}
        >
          <ChevronRight className="w-5 h-5" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
};

export default Pagination;
