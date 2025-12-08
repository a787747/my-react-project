import React from 'react';
import { LayoutDashboard, Settings, LogOut, Users, ClipboardList, Calendar, Star, User } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';

const Sidebar = ({ user }) => {
  const navigate = useNavigate();

  // Функция выхода
  const handleLogout = () => {
    if (window.confirm('Вы точно хотите выйти?')) {
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      navigate('/login');
      // Перезагрузка нужна, чтобы сбросить стейт в App.jsx
      window.location.reload();
    }
  };

  const getLinkClass = ({ isActive }) => {
    return `flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${
      isActive 
        ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
        : 'text-slate-400 hover:bg-slate-800 hover:text-white'
    }`;
  };

  // Защита от краша, если user вдруг null
  const safeUser = user || { full_name: 'Guest', role: 'guest' };

  return (
    <div className="w-72 bg-slate-900 h-screen flex flex-col text-white fixed left-0 top-0 border-r border-slate-800">
      
      {/* Логотип */}
      <div className="p-8 pb-4">
        <div className="flex items-center gap-3 text-2xl font-bold tracking-tight">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
            <span className="text-white text-xl">E</span>
          </div>
          Evaluation
        </div>
        <p className="text-slate-500 text-xs mt-2 pl-1">Corporate Performance Portal</p>
      </div>

      {/* Меню Навигации */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        
        {/* 1. Дашборд (Видят все) */}
        <NavLink to="/" className={getLinkClass}>
          <LayoutDashboard className="w-5 h-5" />
          Моя Команда
        </NavLink>
        
        {/* 2. История оценок (Видят все) */}
        <NavLink to="/history" className={getLinkClass}>
          <ClipboardList className="w-5 h-5" />
          Мои оценки
        </NavLink>
        
        {/* 3. Мой Профиль (Видят все) */}
        <NavLink to="/profile" className={getLinkClass}>
          <User className="w-5 h-5" />
          Мой Профиль
        </NavLink>
        
        {/* 4. Самооценка (Видят все) */}
        <NavLink to="/self-review" className={getLinkClass}>
          <Star className="w-5 h-5" />
          Самооценка
        </NavLink>
        
        {/* 5. Сотрудники (Видят только Админы, Менеджеры и C-Level) */}
        {['admin', 'manager', 'c_level'].includes(safeUser.role) && (
          <NavLink to="/admin/users" className={getLinkClass}>
            <Users className="w-5 h-5" />
            Сотрудники
          </NavLink>
        )}

        {/* 6. Периоды оценки (Видят только Админы) */}
        {safeUser.role === 'admin' && (
          <NavLink to="/admin/periods" className={getLinkClass}>
            <Calendar className="w-5 h-5" />
            Периоды
          </NavLink>
        )}

        {/* 7. Настройки Критериев (Видят только Админы) */}
        {safeUser.role === 'admin' && (
          <NavLink to="/admin" end className={getLinkClass}>
            <Settings className="w-5 h-5" />
            Критерии
          </NavLink>
        )}
      </nav>

      {/* Футер пользователя (Кнопка выхода) */}
      <div className="p-4 border-t border-slate-800">
        <button 
          onClick={handleLogout}
          className="w-full flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 hover:bg-red-500/10 hover:border-red-500/50 border border-transparent transition-all cursor-pointer group text-left"
        >
          <div className="w-10 h-10 bg-indigo-500 rounded-full flex items-center justify-center text-white font-bold group-hover:bg-red-500 transition-colors">
            {safeUser.full_name ? safeUser.full_name.charAt(0) : 'U'}
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-medium text-white truncate group-hover:text-red-400 transition-colors">
              {safeUser.full_name}
            </p>
            <p className="text-xs text-slate-400 truncate capitalize">
              {safeUser.role}
            </p>
          </div>
          <LogOut className="w-4 h-4 text-slate-400 group-hover:text-red-400" />
        </button>
      </div>
    </div>
  );
};

export default Sidebar;