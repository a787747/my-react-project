import { useEffect, useState } from 'react';
import axios from 'axios';
import { Settings, Save, Loader2, ListPlus, ToggleLeft, ToggleRight, Edit3, Plus, Check, Trash2 } from 'lucide-react';

const API_MANAGE_CRITERIA = 'http://92.51.45.147:5678/webhook/manage-criteria';

const AdminSettings = () => {
  const [criteriaList, setCriteriaList] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [editingId, setEditingId] = useState(null); 
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    fetchCriteria();
  }, []);

  const fetchCriteria = async () => {
    try {
      const response = await axios.post(API_MANAGE_CRITERIA, { action: 'get' });
      const rawData = response.data;
      let list = [];
      if (rawData && rawData.data && Array.isArray(rawData.data)) {
        list = rawData.data;
      } else if (Array.isArray(rawData)) {
        list = rawData;
      }
      setCriteriaList(list);
    } catch (error) {
      console.error("Ошибка:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (crit) => {
    setEditingId(crit.id);
    setEditForm({ ...crit });
  };

  const handleAddNew = () => {
    setEditingId('new');
    setEditForm({
      title: '',
      description: '',
      target_audience: 'all',
      is_active: true
    });
  };

  const handleSave = async () => {
    try {
      await axios.post(API_MANAGE_CRITERIA, {
        action: 'save',
        criteria: editForm
      });
      setEditingId(null);
      fetchCriteria(); 
    } catch (error) {
      alert("Ошибка сохранения");
    }
  };

  // ФУНКЦИЯ УДАЛЕНИЯ
  const handleDelete = async (id) => {
    if (!window.confirm("Вы уверены, что хотите удалить этот критерий? Это действие нельзя отменить.")) {
      return;
    }

    try {
      await axios.post(API_MANAGE_CRITERIA, {
        action: 'delete',
        criteria: { id: id }
      });
      fetchCriteria();
    } catch (error) {
      alert("Не удалось удалить. Возможно, этот критерий уже используется в оценках сотрудников.");
    }
  };

  const audiences = [
    { id: 'all', label: 'Все сотрудники' },
    { id: 'project', label: 'Проектная команда' },
    { id: 'tender', label: 'Тендерный отдел' },
    { id: 'back_office', label: 'Бэк-офис' },
  ];

  if (loading) return <div className="p-12 text-center">Загрузка...</div>;

  return (
    <div className="max-w-6xl mx-auto pb-20">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <ListPlus className="text-blue-600 w-8 h-8" />
            Критерии Оценки
          </h1>
          <p className="text-slate-500 mt-2">Добавляйте вопросы и назначайте их отделам.</p>
        </div>
        <button 
          onClick={handleAddNew}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" /> Добавить критерий
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-bold">
            <tr>
              <th className="p-4 border-b">Критерий / Вопрос</th>
              <th className="p-4 border-b w-64">Для кого (Аудитория)</th>
              <th className="p-4 border-b w-32 text-center">Статус</th>
              <th className="p-4 border-b w-32 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {editingId === 'new' && (
              <tr className="bg-blue-50">
                <td className="p-4">
                  <input 
                    className="w-full p-2 border rounded mb-2 font-bold" 
                    placeholder="Название критерия"
                    value={editForm.title}
                    onChange={e => setEditForm({...editForm, title: e.target.value})}
                  />
                  <textarea 
                    className="w-full p-2 border rounded text-sm" 
                    placeholder="Описание (подсказка)"
                    value={editForm.description}
                    onChange={e => setEditForm({...editForm, description: e.target.value})}
                  />
                </td>
                <td className="p-4 align-top">
                  <select 
                    className="w-full p-2 border rounded"
                    value={editForm.target_audience}
                    onChange={e => setEditForm({...editForm, target_audience: e.target.value})}
                  >
                    {audiences.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                  </select>
                </td>
                <td className="p-4 text-center align-top">
                   <span className="text-xs font-bold text-blue-600">NEW</span>
                </td>
                <td className="p-4 align-top text-right">
                  <button onClick={handleSave} className="bg-green-600 text-white p-2 rounded hover:bg-green-700 mr-2"><Check className="w-4 h-4"/></button>
                  <button onClick={() => setEditingId(null)} className="bg-slate-200 text-slate-600 p-2 rounded hover:bg-slate-300"><Settings className="w-4 h-4 rotate-45"/></button>
                </td>
              </tr>
            )}

            {criteriaList.map((crit) => (
              <tr key={crit.id} className={!crit.is_active ? 'opacity-50 bg-slate-50' : ''}>
                
                {editingId === crit.id ? (
                  <>
                    <td className="p-4">
                      <input 
                        className="w-full p-2 border rounded mb-2 font-bold" 
                        value={editForm.title}
                        onChange={e => setEditForm({...editForm, title: e.target.value})}
                      />
                      <textarea 
                        className="w-full p-2 border rounded text-sm" 
                        value={editForm.description || ''}
                        onChange={e => setEditForm({...editForm, description: e.target.value})}
                      />
                    </td>
                    <td className="p-4 align-top">
                      <select 
                        className="w-full p-2 border rounded"
                        value={editForm.target_audience}
                        onChange={e => setEditForm({...editForm, target_audience: e.target.value})}
                      >
                         {audiences.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                      </select>
                    </td>
                    <td className="p-4 text-center align-top">
                      <button 
                        onClick={() => setEditForm({...editForm, is_active: !editForm.is_active})}
                        className="text-2xl"
                      >
                        {editForm.is_active ? <ToggleRight className="text-green-600 w-8 h-8"/> : <ToggleLeft className="text-slate-400 w-8 h-8"/>}
                      </button>
                    </td>
                    <td className="p-4 align-top text-right">
                      <button onClick={handleSave} className="bg-green-600 text-white p-2 rounded hover:bg-green-700 mr-2"><Check className="w-4 h-4"/></button>
                      <button onClick={() => setEditingId(null)} className="bg-slate-200 text-slate-600 p-2 rounded hover:bg-slate-300">Отмена</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="p-4">
                      <div className="font-bold text-slate-900">{crit.title}</div>
                      <div className="text-sm text-slate-500 mt-1">{crit.description}</div>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs font-bold uppercase border ${
                        crit.target_audience === 'all' ? 'bg-slate-100 text-slate-600 border-slate-200' :
                        crit.target_audience === 'project' ? 'bg-purple-100 text-purple-700 border-purple-200' :
                        'bg-blue-100 text-blue-700 border-blue-200'
                      }`}>
                        {audiences.find(a => a.id === crit.target_audience)?.label || crit.target_audience}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      {crit.is_active 
                        ? <span className="text-green-600 text-xs font-bold flex justify-center items-center gap-1"><Check className="w-3 h-3"/> Активен</span> 
                        : <span className="text-slate-400 text-xs font-bold">Отключен</span>}
                    </td>
                    <td className="p-4 text-right flex justify-end gap-2">
                      <button onClick={() => handleEdit(crit)} className="p-2 text-slate-400 hover:text-blue-600 transition-colors" title="Редактировать">
                        <Edit3 className="w-5 h-5" />
                      </button>
                      
                      {/* КНОПКА УДАЛЕНИЯ */}
                      <button 
                        onClick={() => handleDelete(crit.id)} 
                        className="p-2 text-slate-400 hover:text-red-600 transition-colors hover:bg-red-50 rounded"
                        title="Удалить навсегда"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminSettings;