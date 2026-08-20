/**
 * Skeleton - Компоненты скелетной загрузки
 * 
 * Назначение: Показывает плейсхолдеры во время загрузки данных
 * Используется в: Страницы с данными (Dashboard, Profile, AdminUsers и др.)
 * 
 * Варианты:
 * - Skeleton.Text - текстовая строка
 * - Skeleton.Title - заголовок
 * - Skeleton.Avatar - аватар
 * - Skeleton.Button - кнопка
 * - Skeleton.Card - карточка
 * - Skeleton.TableRow - строка таблицы
 * - Skeleton.EmployeeCard - карточка сотрудника
 * - Skeleton.ProfileHeader - заголовок профиля
 * - Skeleton.StatCard - карточка статистики
 */

import React from 'react';

/**
 * Базовый элемент скелетона с shimmer-эффектом
 */
const SkeletonBase = ({ className = '', ...props }) => {
  return (
    <div 
      className={`bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%] animate-shimmer rounded ${className}`}
      {...props}
    />
  );
};

/**
 * Текстовая строка
 */
const Text = ({ width = 'w-full', className = '' }) => {
  return <SkeletonBase className={`h-4 ${width} ${className}`} />;
};

/**
 * Заголовок
 */
const Title = ({ width = 'w-3/4', className = '' }) => {
  return <SkeletonBase className={`h-6 ${width} ${className}`} />;
};

/**
 * Аватар
 */
const Avatar = ({ size = 'md', className = '' }) => {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };
  return <SkeletonBase className={`${sizes[size]} rounded-full flex-shrink-0 ${className}`} />;
};

/**
 * Кнопка
 */
const Button = ({ width = 'w-24', className = '' }) => {
  return <SkeletonBase className={`h-10 ${width} rounded-xl ${className}`} />;
};

/**
 * Карточка базовая
 */
const Card = ({ className = '' }) => {
  return (
    <div className={`bg-white rounded-2xl border border-slate-200/60 p-6 ${className}`}>
      <div className="flex items-start gap-4 mb-4">
        <Avatar size="lg" />
        <div className="flex-1 space-y-2">
          <Title width="w-1/2" />
          <Text width="w-1/3" />
        </div>
      </div>
      <div className="space-y-2">
        <Text width="w-full" />
        <Text width="w-2/3" />
      </div>
    </div>
  );
};

/**
 * Строка таблицы
 */
const TableRow = ({ columns = 5, className = '' }) => {
  return (
    <tr className={className}>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-6 py-4">
          {i === 0 ? (
            <div className="flex items-center gap-3">
              <Avatar size="md" />
              <div className="space-y-1.5 flex-1">
                <Text width="w-32" />
                <Text width="w-24" className="h-3" />
              </div>
            </div>
          ) : (
            <Text width={i === columns - 1 ? 'w-20' : 'w-24'} />
          )}
        </td>
      ))}
    </tr>
  );
};

/**
 * Таблица целиком
 */
const Table = ({ rows = 5, columns = 5, className = '' }) => {
  return (
    <div className={`bg-white rounded-xl border border-slate-200/60 overflow-hidden ${className}`}>
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i} className="px-6 py-4 text-left">
                <Text width="w-20" className="h-3" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {Array.from({ length: rows }).map((_, i) => (
            <TableRow key={i} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

/**
 * Карточка сотрудника (для Dashboard)
 */
const EmployeeCard = ({ className = '' }) => {
  return (
    <div className={`bg-white rounded-2xl border border-slate-200/60 p-6 ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <Avatar size="xl" />
        <div className="flex flex-col items-end gap-2">
          <SkeletonBase className="h-6 w-20 rounded-full" />
        </div>
      </div>
      <div className="space-y-2 mb-4">
        <Title width="w-3/4" />
        <Text width="w-1/2" />
      </div>
      <div className="space-y-2 mb-6">
        <div className="flex items-center gap-2">
          <SkeletonBase className="w-4 h-4 rounded" />
          <Text width="w-32" />
        </div>
        <div className="flex items-center gap-2">
          <SkeletonBase className="w-4 h-4 rounded" />
          <Text width="w-24" />
        </div>
      </div>
      <Button width="w-full" />
    </div>
  );
};

/**
 * Заголовок профиля
 */
const ProfileHeader = ({ className = '' }) => {
  return (
    <div className={`${className}`}>
      <div className="flex items-center gap-4 mb-6">
        <Avatar size="xl" />
        <div className="space-y-2">
          <Title width="w-48" />
          <Text width="w-32" />
        </div>
      </div>
    </div>
  );
};

/**
 * Карточка статистики
 */
const StatCard = ({ className = '' }) => {
  return (
    <div className={`bg-white rounded-xl border border-slate-200/60 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <SkeletonBase className="w-8 h-8 rounded-lg" />
      </div>
      <SkeletonBase className="h-8 w-16 mb-1" />
      <Text width="w-24" className="h-3" />
    </div>
  );
};

/**
 * Сетка карточек сотрудников
 */
const EmployeeGrid = ({ count = 6, className = '' }) => {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <EmployeeCard key={i} />
      ))}
    </div>
  );
};

/**
 * Карточки статистики
 */
const StatGrid = ({ count = 4, className = '' }) => {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <StatCard key={i} />
      ))}
    </div>
  );
};

/**
 * Слайдер критерия
 */
const CriterionSlider = ({ className = '' }) => {
  return (
    <div className={`bg-white rounded-xl border border-slate-100 p-5 ${className}`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1 space-y-2">
          <Title width="w-2/3" />
          <Text width="w-1/2" className="h-3" />
        </div>
        <SkeletonBase className="w-12 h-10 rounded-lg ml-4" />
      </div>
      <SkeletonBase className="h-2 w-full rounded-full mb-4" />
      <SkeletonBase className="h-16 w-full rounded-lg" />
    </div>
  );
};

/**
 * Форма с полями
 */
const Form = ({ fields = 4, className = '' }) => {
  return (
    <div className={`space-y-6 ${className}`}>
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i}>
          <Text width="w-24" className="h-3 mb-2" />
          <SkeletonBase className="h-10 w-full rounded-xl" />
        </div>
      ))}
    </div>
  );
};

/**
 * Страница целиком с заголовком и контентом
 */
const Page = ({ className = '' }) => {
  return (
    <div className={`p-8 ${className}`}>
      <div className="mb-8">
        <Title width="w-48" className="mb-2" />
        <Text width="w-64" />
      </div>
      <StatGrid count={4} className="mb-8" />
      <EmployeeGrid count={6} />
    </div>
  );
};

// Экспортируем как объект с вложенными компонентами
const Skeleton = {
  Base: SkeletonBase,
  Text,
  Title,
  Avatar,
  Button,
  Card,
  TableRow,
  Table,
  EmployeeCard,
  EmployeeGrid,
  ProfileHeader,
  StatCard,
  StatGrid,
  CriterionSlider,
  Form,
  Page,
};

export default Skeleton;





