import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Users, Plus, Pencil, Search, Filter, X, Save, Loader2, Briefcase, Mail, Shield } from 'lucide-react';

const API_GET_DATA = 'http://92.51.45.147:5678/webhook/admin/users-data';
const API_SAVE_USER = 'http://92.51.45.147:5678/webhook/admin/save-user';

const AdminUsers = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Данные
  const [users, setUsers] = useState([]);
  const [options, setOptions] = useState({ departments: [], grades: [], managers: [] });

  // Фильтры
  const initialFilters = {
    search: '',
    role: 'all',
    department_id: 'all',
    manager_id: 'all',
    work_category: 'all'
  };
  const [filters, setFilters] = useState(initialFilters);

  // Модальное окно
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Форма
  const initialFormState = {
    full_name: '',
    email: '',
    job_title: '',
    role: 'employee',
    work_category: 'general',
    department_id: '',
    grade_id: '',
    manager_id: ''
  };
  const [formData, setFormData] = useState(initialFormState);

  // Загрузка данных
  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await axios.get(API_GET_DATA);
      const data = res.data; 
      
      setUsers(data.users || []);
      setOptions({
        departments: data.options?.departments || [],
        grades: data.options?.grades || [],
        managers: data.options?.managers || []
      });
    } catch (error) {
      console.error('Ошибка загрузки пользователей:', error);
      alert('Не удалось загрузить список пользователей.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // --- ЛОГИКА ФИЛЬТРАЦИИ ---
  const filteredUsers = users.filter(user => {
    // 1. Поиск по тексту
    const searchMatch = 
      user.full_name.toLowerCase().includes(filters.search.toLowerCase()) ||
      user.email.toLowerCase().includes(filters.search.toLowerCase());
    if (!searchMatch) return false;

    // 2. Фильтр по Роли
    if (filters.role !== 'all' && user.role !== filters.role) return false;

    // 3. Фильтр по Категории
    if (filters.work_category !== 'all' && user.work_category !== filters.work_category) return false;

    // 4. Фильтр по Отделу (сравниваем ID, приводим к строке для надежности)
    if (filters.department_id !== 'all' && String(user.department_id) !== String(filters.department_id)) return false;

    // 5. Фильтр по Менеджеру
    if (filters.manager_id !== 'all' && String(user.manager_id) !== String(filters.manager_id)) return false;

    return true;
  });

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters(initialFilters);
  };

  // --- ЛОГИКА МОДАЛЬНОГО ОКНА ---
  const handleOpenModal = (user = null) => {
    if (user) {
      setCurrentUser(user);
      setFormData({
        full_name: user.full_name,
        email: user.email,
        job_title: user.job_title || '',
        role: user.role,
        work_category: user.work_category,
        department_id: user.department_id || '',
        grade_id: user.grade_id || '',
        manager_id: user.manager_id || ''
      });
    } else {
      setCurrentUser(null);
      setFormData(initialFormState);
    }
    setIsModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...formData };
      if (currentUser) payload.id = currentUser.id;

      await axios.post(API_SAVE_USER, payload);
      
      setIsModalOpen(false);
      await fetchData(); 
    } catch (error) {
      console.error('Ошибка сохранения:', error);
      alert('Ошибка при сохранении.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin text-indigo-600" /></div>;

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Сотрудники</h1>
          <p className="text-gray-500">
            Всего: {users.length} | Найдено: <span className="text-indigo-600 font-bold">{filteredUsers.length}</span>
          </p>
        </div>
        <button 
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm font-medium"
        >
          <Plus className="w-5 h-5" /> Добавить
        </button>
      </div>

      {/* ПАНЕЛЬ ФИЛЬТРОВ */}
      <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 mb-6">
        <div className="flex items-center gap-2 mb-4 text-gray-700 font-medium">
          <Filter className="w-4 h-4" /> Фильтрация
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Поиск */}
          <div className="lg:col-span-1 relative">
            <Search className="absolute left-3 top-2.5 text-gray-400 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Поиск..." 
              className="w-full pl-9 p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 transition-colors"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
            />
          </div>

          {/* Отдел */}
          <select 
            className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 bg-white"
            value={filters.department_id}
            onChange={(e) => handleFilterChange('department_id', e.target.value)}
          >
            <option value="all">Все отделы</option>
            {options.departments.map(d => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>

          {/* Менеджер */}
          <select 
            className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 bg-white"
            value={filters.manager_id}
            onChange={(e) => handleFilterChange('manager_id', e.target.value)}
          >
            <option value="all">Все руководители</option>
            {options.managers.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>

          {/* Роль / Категория (Смешанный или раздельный) */}
          <select 
            className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 bg-white"
            value={filters.work_category}
            onChange={(e) => handleFilterChange('work_category', e.target.value)}
          >
            <option value="all">Все категории</option>
            <option value="general">General</option>
            <option value="project">Project</option>
            <option value="tender">Tender</option>
          </select>

           {/* Кнопка сброса */}
           <button 
             onClick={resetFilters}
             className="flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-dashed border-gray-300 hover:border-red-200"
           >
             <X className="w-4 h-4" /> Сброс
           </button>
        </div>
      </div>

      {/* ТАБЛИЦА */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Сотрудник</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Роль / Категория</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Отдел / Грейд</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Менеджер</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filteredUsers.length > 0 ? (
                filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold mr-3">
                          {user.full_name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-semibold text-gray-900">{user.full_name}</div>
                          <div className="text-xs text-gray-500 flex items-center gap-1">
                             <Mail className="w-3 h-3" /> {user.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <span className={`inline-flex w-fit items-center px-2 py-0.5 rounded text-xs font-medium capitalize border
                          ${user.role === 'admin' ? 'bg-red-50 text-red-700 border-red-100' : 'bg-blue-50 text-blue-700 border-blue-100'}`}>
                          {user.role}
                        </span>
                        <span className="text-sm text-gray-600 capitalize">{user.work_category}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 font-medium">{user.department_name || '-'}</div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        Grade: <span className="font-medium text-gray-700">{user.grade_name || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {user.manager_name ? (
                        <div className="flex items-center gap-1.5">
                          <Users className="w-4 h-4 text-gray-400" /> 
                          {user.manager_name}
                        </div>
                      ) : (
                        <span className="text-gray-400 italic text-xs">Не назначен</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => handleOpenModal(user)}
                        className="text-gray-400 hover:text-indigo-600 p-2 rounded-lg hover:bg-indigo-50 transition-colors"
                      >
                        <Pencil className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="text-center py-10 text-gray-500">
                    Сотрудники не найдены по выбранным фильтрам.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* МОДАЛЬНОЕ ОКНО (То же самое, что и было) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <form onSubmit={handleSave}>
              <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0">
                <h2 className="text-xl font-bold text-gray-900">
                  {currentUser ? 'Редактировать сотрудника' : 'Новый сотрудник'}
                </h2>
                <button type="button" onClick={() => setIsModalOpen(false)} className="p-2 hover:bg-gray-100 rounded-full">
                  <X className="w-6 h-6 text-gray-400" />
                </button>
              </div>

              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="col-span-2 md:col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">ФИО</label>
                  <input required type="text" className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.full_name} onChange={(e) => setFormData({...formData, full_name: e.target.value})} />
                </div>
                <div className="col-span-2 md:col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input required type="email" className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Должность</label>
                  <input type="text" className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.job_title} onChange={(e) => setFormData({...formData, job_title: e.target.value})} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Роль доступа</label>
                  <select className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
                    value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})}>
                    <option value="employee">Employee</option>
                    <option value="manager">Manager</option>
                    <option value="admin">Admin</option>
                    <option value="c_level">C-Level</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
                  <select className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
                    value={formData.work_category} onChange={(e) => setFormData({...formData, work_category: e.target.value})}>
                    <option value="general">General</option>
                    <option value="project">Project</option>
                    <option value="tender">Tender</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Отдел</label>
                  <select className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
                    value={formData.department_id} onChange={(e) => setFormData({...formData, department_id: e.target.value})}>
                    <option value="">Без отдела</option>
                    {options.departments.map(d => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Грейд</label>
                  <select className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
                    value={formData.grade_id} onChange={(e) => setFormData({...formData, grade_id: e.target.value})}>
                    <option value="">Без грейда</option>
                    {options.grades.map(g => (
                      <option key={g.id} value={g.id}>{g.code}</option>
                    ))}
                  </select>
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Руководитель</label>
                  <select className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
                    value={formData.manager_id} onChange={(e) => setFormData({...formData, manager_id: e.target.value})}>
                    <option value="">Без руководителя</option>
                    {options.managers.map(m => (
                      <option key={m.id} value={m.id}>
                        {m.name} {currentUser && currentUser.id === m.id ? '(Это он сам)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 sticky bottom-0 rounded-b-2xl">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors">Отмена</button>
                <button type="submit" disabled={saving} className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md disabled:opacity-50">
                  {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                  {saving ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;