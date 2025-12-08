import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import AdminSettings from './pages/AdminSettings';
import AdminUsers from './pages/AdminUsers';
import AdminPeriods from './pages/AdminPeriods';
import Login from './pages/Login';
import EvaluationHistory from './pages/EvaluationHistory';
import Profile from './pages/Profile';
import SelfReview from './pages/SelfReview';

// 1. Компонент для проверки прав администратора/менеджера
const AdminRoute = ({ children, allowedRoles }) => {
  const user = JSON.parse(localStorage.getItem('user'));
  
  // Если не залогинен - на логин
  if (!user) return <Navigate to="/login" replace />;
  
  // Если роль пользователя есть в списке разрешенных - показываем контент
  if (allowedRoles.includes(user.role)) {
    return children;
  }
  
  // Иначе - редирект на главную (Dashboard)
  return <Navigate to="/" replace />;
};

function App() {
  const user = JSON.parse(localStorage.getItem('user'));

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* Глобальная проверка авторизации */}
        <Route
          path="/*"
          element={
            user ? (
              <div className="flex min-h-screen bg-slate-50">
                {/* Передаем user в Sidebar, чтобы показать имя */}
                <Sidebar user={user} />
                
                <div className="flex-1 ml-72">
                  <div className="p-8 min-h-screen">
                    <Routes>
                      {/* Dashboard доступен всем авторизованным */}
                      <Route path="/" element={<Dashboard user={user} />} />
                      
                      {/* История оценок доступна всем авторизованным */}
                      <Route path="/history" element={<EvaluationHistory user={user} />} />
                      
                      {/* Профиль доступен всем авторизованным */}
                      <Route path="/profile" element={<Profile user={user} />} />
                      
                      {/* Самооценка доступна всем авторизованным */}
                      <Route path="/self-review" element={<SelfReview user={user} />} />
                      
                      {/* Управление сотрудниками: Только Admin, Manager, C-level */}
                      <Route 
                        path="/admin/users" 
                        element={
                          <AdminRoute allowedRoles={['admin', 'manager', 'c_level']}>
                            <AdminUsers />
                          </AdminRoute>
                        } 
                      />
                      
                      {/* Периоды оценки: Только Admin */}
                      <Route 
                        path="/admin/periods" 
                        element={
                          <AdminRoute allowedRoles={['admin']}>
                            <AdminPeriods />
                          </AdminRoute>
                        } 
                      />
                      
                      {/* Настройки системы: Только Admin */}
                      <Route 
                        path="/admin" 
                        element={
                          <AdminRoute allowedRoles={['admin']}>
                            <AdminSettings />
                          </AdminRoute>
                        } 
                      />
                    </Routes>
                  </div>
                </div>
              </div>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </Router>
  );
}

export default App;