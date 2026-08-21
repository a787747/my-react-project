/**
 * Sidebar - Боковое меню навигации
 * 
 * Назначение: Навигация по приложению с учетом роли пользователя
 * Используется в: App.jsx (отображается для авторизованных пользователей)
 * 
 * Props:
 * - user: object - текущий пользователь с ролью
 * 
 * Функционал:
 * - Адаптивный дизайн (desktop sidebar / mobile drawer)
 * - Группировка пунктов меню по категориям
 * - Навигация для всех пользователей: Дашборд, История, Профиль, Самооценка
 * - Админ-навигация (admin, c_level): Аналитика, Сотрудники, Периоды, Критерии
 * - Панель задач с прогрессом
 * - Кнопка выхода
 */

import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, Settings, LogOut, Users, ClipboardList, Calendar, 
  Star, User, BarChart3, TrendingUp, Grid3x3, Calculator, Award, 
  UserCheck, BookOpen, ClipboardCheck, CheckCircle2, Shield, Info, 
  Coins, Menu, X, ChevronDown, CalendarRange
} from 'lucide-react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { useTaskStatus } from '../context/TaskStatusContext';
import { canViewAnalytics, canAccessAdminPanel, isHR } from '../utils/permissions';

/**
 * NavItem - Компонент пункта меню
 */
const NavItem = ({ to, icon: Icon, label, onClick, end = false }) => {
  return (
    <NavLink 
      to={to} 
      end={end}
      onClick={onClick}
      className={({ isActive }) => `
        flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm
        ${isActive 
          ? 'bg-brand-600 text-white shadow-brand' 
          : 'text-slate-400 hover:bg-slate-800 hover:text-white'
        }
      `}
    >
      <Icon className="w-5 h-5 flex-shrink-0" />
      <span className="truncate">{label}</span>
    </NavLink>
  );
};

/**
 * NavGroup - Группа пунктов меню со сворачиванием (управляемый компонент)
 */
const NavGroup = ({ title, icon: Icon, children, groupId, openGroupId, onToggle }) => {
  // Группа открыта ТОЛЬКО если её id совпадает с открытой группой
  const isOpen = openGroupId === groupId;
  
  const handleToggle = () => {
    // Если группа уже открыта - закрываем (передаём null), иначе открываем
    onToggle(isOpen ? null : groupId);
  };
  
  // Если нет children, не рендерим группу
  const hasChildren = React.Children.count(children) > 0;
  if (!hasChildren) return null;
  
  return (
    <div className="mb-2 mt-3 first:mt-0">
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-200 transition-colors border-t border-slate-700/50 pt-3"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-3.5 h-3.5 text-brand-500" />}
          <span>{title}</span>
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isOpen ? '' : '-rotate-90'}`} />
      </button>
      <div className={`space-y-1 overflow-hidden transition-all duration-200 ${isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}>
        {children}
      </div>
    </div>
  );
};

/**
 * TaskStatusIndicator - Индикатор статуса задачи
 */
const TaskStatusIndicator = ({ done, icon: Icon, label, info = false }) => {
  return (
    <div className="group relative">
      <div className={`
        relative w-7 h-7 rounded-md flex items-center justify-center transition-all cursor-default
        ${info 
          ? 'bg-warning-900/30' 
          : done 
            ? 'bg-gradient-to-br from-success-500 to-success-600 shadow-sm shadow-success-900/30' 
            : 'bg-slate-700'
        }
      `}>
        <Icon className={`w-3.5 h-3.5 ${info ? 'text-warning-400' : done ? 'text-white' : 'text-slate-400'}`} />
        {done && !info && (
          <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-white rounded-full flex items-center justify-center shadow">
            <CheckCircle2 className="w-2 h-2 text-success-500" />
          </div>
        )}
        {info && (
          <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-warning-500 rounded-full flex items-center justify-center shadow">
            <Info className="w-2 h-2 text-white" />
          </div>
        )}
      </div>
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-20 shadow-lg">
        {label}
        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-700" />
      </div>
    </div>
  );
};

const Sidebar = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useUser();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [openGroupId, setOpenGroupId] = useState('personal'); // По умолчанию открыта группа "Личные"
  
  // Используем контекст статусов задач
  const { 
    hasSelfReview, 
    hasEvaluatedManager, 
    hasEvaluatedAllSubordinates, 
    hasSubordinates, 
    hasManager, 
    isManagerCLevel,
    needsSelfReview,
    isOutOfScope
  } = useTaskStatus();

  // Закрываем мобильное меню при навигации
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  // Блокируем скролл body при открытом мобильном меню
  useEffect(() => {
    if (isMobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileOpen]);

  const handleLogout = () => {
    if (window.confirm('Вы точно хотите выйти?')) {
      logout();
      navigate('/login');
    }
  };

  const closeMobileMenu = () => setIsMobileOpen(false);

  const safeUser = user || { full_name: 'Guest', role: 'guest' };
  const showTaskPanel = !isHR(safeUser.role);

  // Контент сайдбара
  const SidebarContent = () => (
    <>
      {/* Логотип */}
      <div className="px-4 py-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center shadow-brand">
            <span className="text-white text-lg font-bold">E</span>
          </div>
          <div>
            <div className="text-lg font-bold text-white tracking-tight">Evaluation</div>
            <div className="text-[10px] text-slate-500 font-medium">Performance Portal</div>
          </div>
        </div>
      </div>

      {/* Меню Навигации */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        
        {/* === ЛИЧНЫЕ === */}
        {!isHR(safeUser.role) && (
          <NavGroup title="Личные" icon={User} groupId="personal" openGroupId={openGroupId} onToggle={setOpenGroupId}>
            <NavItem to="/welcome" icon={BookOpen} label="Инструкции" onClick={closeMobileMenu} />
            <NavItem to="/profile" icon={User} label="Мой Профиль" onClick={closeMobileMenu} />
            {!isOutOfScope && (
              <NavItem to="/self-review" icon={Star} label="Самооценка" onClick={closeMobileMenu} />
            )}
            <NavItem to="/history" icon={ClipboardList} label="Мои оценки" onClick={closeMobileMenu} />
            {!isOutOfScope && (
              <NavItem to="/manager-evaluation" icon={UserCheck} label="Оценить руководителя" onClick={closeMobileMenu} />
            )}
          </NavGroup>
        )}

        {/* === КОМАНДА === */}
        {!isOutOfScope && !isHR(safeUser.role) && (hasSubordinates || safeUser.has_manager_subordinates || safeUser.role === 'manager') && (
          <NavGroup title="Команда" icon={Users} groupId="team" openGroupId={openGroupId} onToggle={setOpenGroupId}>
            <NavItem to="/dashboard" icon={LayoutDashboard} label="Моя Команда" onClick={closeMobileMenu} />
            {safeUser.has_manager_subordinates && (
              <NavItem to="/team-scores" icon={TrendingUp} label="Оценки команды" onClick={closeMobileMenu} />
            )}
            {safeUser.role === 'manager' && (
              <NavItem to="/team" icon={Users} label="Список команды" onClick={closeMobileMenu} />
            )}
          </NavGroup>
        )}

        {/* === HR === */}
        {isHR(safeUser.role) && (
          <NavGroup title="HR Панель" icon={ClipboardCheck} groupId="hr" openGroupId={openGroupId} onToggle={setOpenGroupId}>
            <NavItem to="/hr/dashboard" icon={ClipboardCheck} label="Статусы оценок" onClick={closeMobileMenu} />
            <NavItem to="/admin/users" icon={Users} label="Сотрудники" onClick={closeMobileMenu} />
          </NavGroup>
        )}

        {/* === АНАЛИТИКА (admin, c_level) === */}
        {canViewAnalytics(safeUser.role) && (
          <NavGroup title="Аналитика" icon={BarChart3} groupId="analytics" openGroupId={openGroupId} onToggle={setOpenGroupId}>
            <NavItem to="/analytics" icon={BarChart3} label="Дашборд" onClick={closeMobileMenu} />
            <NavItem to="/admin/all-evaluations" icon={TrendingUp} label="Все оценки" onClick={closeMobileMenu} />
            <NavItem to="/admin/evaluations-matrix" icon={Grid3x3} label="Матрица оценок" onClick={closeMobileMenu} />
            <NavItem to="/admin/final-scores" icon={Award} label="Итоговые баллы" onClick={closeMobileMenu} />
            <NavItem to="/admin/bonus-calculation" icon={Coins} label="Калькуляция бонусов" onClick={closeMobileMenu} />
            <NavItem to="/admin/annual-rollup" icon={CalendarRange} label="Годовые итоги" onClick={closeMobileMenu} />
            {safeUser.role === 'admin' && (
              <NavItem to="/admin/score-calculator" icon={Calculator} label="Калькуляция баллов" onClick={closeMobileMenu} />
            )}
          </NavGroup>
        )}

        {/* === АДМИНИСТРИРОВАНИЕ === */}
        {canAccessAdminPanel(safeUser.role) && !isHR(safeUser.role) && (
          <NavGroup title="Администрирование" icon={Settings} groupId="admin" openGroupId={openGroupId} onToggle={setOpenGroupId}>
            <NavItem to="/admin/users" icon={Users} label="Сотрудники" onClick={closeMobileMenu} />
            {safeUser.role === 'admin' && (
              <>
                <NavItem to="/admin/periods" icon={Calendar} label="Периоды" onClick={closeMobileMenu} />
                <NavItem to="/admin" icon={Settings} label="Критерии" onClick={closeMobileMenu} end />
                <NavItem to="/admin/scoring" icon={Calculator} label="Коэффициенты" onClick={closeMobileMenu} />
              </>
            )}
          </NavGroup>
        )}
      </nav>

      {/* Панель задач */}
      {showTaskPanel && !isOutOfScope && (
        <div className="px-4 pb-3">
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <p className="text-[10px] text-slate-500 mb-2 text-center font-semibold uppercase tracking-wider">
              Мои задачи
            </p>
            <div className="flex justify-center gap-2">
              {needsSelfReview && (
                <TaskStatusIndicator 
                  done={hasSelfReview} 
                  icon={Star} 
                  label={`Самооценка ${hasSelfReview ? '✓' : ''}`} 
                />
              )}
              {hasSubordinates && (
                <TaskStatusIndicator 
                  done={hasEvaluatedAllSubordinates} 
                  icon={Users} 
                  label={`Сотрудники ${hasEvaluatedAllSubordinates ? '✓' : ''}`} 
                />
              )}
              {hasManager && !isManagerCLevel && (
                <TaskStatusIndicator 
                  done={hasEvaluatedManager} 
                  icon={Shield} 
                  label={`Руководитель ${hasEvaluatedManager ? '✓' : ''}`} 
                />
              )}
              {hasManager && isManagerCLevel && (
                <TaskStatusIndicator 
                  done={false} 
                  icon={Shield} 
                  label="C-level не оценивается" 
                  info={true}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Футер пользователя */}
      <div className="p-3 border-t border-slate-800">
        <button 
          onClick={handleLogout}
          className="w-full flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 hover:bg-danger-500/10 hover:border-danger-500/50 border border-transparent transition-all cursor-pointer group text-left"
        >
          <div className="w-10 h-10 bg-brand-600 rounded-full flex items-center justify-center text-white text-sm font-bold group-hover:bg-danger-500 transition-colors">
            {safeUser.full_name ? safeUser.full_name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate group-hover:text-danger-400 transition-colors">
              {safeUser.full_name}
            </p>
            <p className="text-xs text-slate-400 truncate capitalize">
              {safeUser.role === 'c_level' ? 'C-Level' : safeUser.role}
            </p>
          </div>
          <LogOut className="w-4 h-4 text-slate-400 group-hover:text-danger-400 flex-shrink-0" />
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile Header с hamburger */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-fixed bg-sidebar-bg border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center shadow-brand">
            <span className="text-white text-sm font-bold">E</span>
          </div>
          <span className="text-white font-bold">Evaluation</span>
        </div>
        <button 
          onClick={() => setIsMobileOpen(true)}
          className="p-2 text-white hover:bg-slate-800 rounded-lg transition-colors"
          aria-label="Открыть меню"
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-modal-backdrop animate-fade-in"
          onClick={closeMobileMenu}
        />
      )}

      {/* Mobile Drawer */}
      <div className={`
        lg:hidden fixed inset-y-0 left-0 w-72 bg-sidebar-bg z-modal flex flex-col
        transform transition-transform duration-300 ease-out
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Close button */}
        <button 
          onClick={closeMobileMenu}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors z-10"
          aria-label="Закрыть меню"
        >
          <X className="w-5 h-5" />
        </button>
        <SidebarContent />
      </div>

      {/* Desktop Sidebar */}
      <div className="hidden lg:flex w-64 bg-sidebar-bg h-screen flex-col text-white fixed left-0 top-0 border-r border-slate-800">
        <SidebarContent />
      </div>

      {/* Spacer for mobile header */}
      <div className="lg:hidden h-14" />
    </>
  );
};

export default Sidebar;
