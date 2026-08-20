/**
 * UserImportModal - Модальное окно импорта сотрудников из XLSX
 * 
 * Назначение: Загрузка и обработка Excel-файла с данными сотрудников
 * Используется в: AdminUsers
 * 
 * Формат файла идентичен экспорту из системы
 * 
 * Props:
 * - isOpen: boolean - открыто ли модальное окно
 * - options: object - опции для маппинга (departments, grades, managers)
 * - users: array - текущие пользователи (для экспорта и резолва)
 * - onClose: function - колбэк закрытия
 * - onImport: function(users[]) - колбэк после успешного импорта
 */

import React, { useState, useCallback, useRef } from 'react';
import { 
  X, 
  Upload, 
  FileSpreadsheet, 
  AlertCircle, 
  CheckCircle, 
  Download,
  Loader2,
  Trash2,
  FileDown
} from 'lucide-react';
import * as XLSX from 'xlsx-js-style';

// Маппинг колонок файла к полям базы данных
const COLUMN_MAPPING = {
  'ID': 'id',
  'ФИО': 'full_name',
  'Email': 'email',
  'Должность': 'job_title',
  'Роль': 'role',
  'Категория': 'work_category',
  'Отдел': 'department_name',
  'Грейд': 'grade_code',
  'Руководитель': 'manager_name',
  'Руководитель (email)': 'manager_email'
};

// Обратный маппинг для экспорта
const EXPORT_COLUMNS = [
  { key: 'id', header: 'ID' },
  { key: 'full_name', header: 'ФИО' },
  { key: 'email', header: 'Email' },
  { key: 'job_title', header: 'Должность' },
  { key: 'role', header: 'Роль' },
  { key: 'work_category', header: 'Категория' },
  { key: 'department_name', header: 'Отдел' },
  { key: 'grade_name', header: 'Грейд' },
  { key: 'manager_name', header: 'Руководитель' },
  { key: 'manager_email', header: 'Руководитель (email)' }
];

// Допустимые значения для ролей
const VALID_ROLES = ['employee', 'manager', 'hr', 'admin', 'c_level'];

// Допустимые категории
const VALID_CATEGORIES = ['general', 'project', 'tender'];

const UserImportModal = ({ isOpen, options, users = [], onClose, onImport }) => {
  const [file, setFile] = useState(null);
  const [parsedData, setParsedData] = useState([]);
  const [errors, setErrors] = useState([]);
  const [importing, setImporting] = useState(false);
  const [step, setStep] = useState('upload'); // upload | preview | result
  const [importResult, setImportResult] = useState(null);
  const fileInputRef = useRef(null);

  // Сброс состояния
  const resetState = () => {
    setFile(null);
    setParsedData([]);
    setErrors([]);
    setStep('upload');
    setImportResult(null);
  };

  // Закрытие модалки
  const handleClose = () => {
    resetState();
    onClose();
  };

  // Экспорт текущей базы в XLSX
  const handleExport = () => {
    if (!users || users.length === 0) {
      setErrors([{ row: 0, message: 'Нет данных для экспорта' }]);
      return;
    }

    // Создаем карту id -> email для быстрого поиска руководителей
    const userEmailMap = {};
    users.forEach(u => {
      userEmailMap[u.id] = u.email;
    });

    // Создаем данные для экспорта
    const exportData = users.map(user => {
      const row = {};
      EXPORT_COLUMNS.forEach(col => {
        let value = user[col.key];
        // Для manager_email берем email руководителя из карты
        if (col.key === 'manager_email' && user.manager_id) {
          value = userEmailMap[user.manager_id] || '';
        }
        row[col.header] = value || '';
      });
      return row;
    });

    // Создаем worksheet
    const ws = XLSX.utils.json_to_sheet(exportData, {
      header: EXPORT_COLUMNS.map(c => c.header)
    });

    // Устанавливаем ширину колонок
    ws['!cols'] = [
      { wch: 6 },  // ID
      { wch: 35 }, // ФИО
      { wch: 28 }, // Email
      { wch: 25 }, // Должность
      { wch: 12 }, // Роль
      { wch: 12 }, // Категория
      { wch: 20 }, // Отдел
      { wch: 10 }, // Грейд
      { wch: 30 }, // Руководитель
      { wch: 28 }  // Руководитель (email)
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Сотрудники');
    
    const date = new Date().toISOString().split('T')[0];
    XLSX.writeFile(wb, `сотрудники_${date}.xlsx`);
  };

  // Парсинг файла
  const parseFile = useCallback((file) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        
        if (jsonData.length < 2) {
          setErrors([{ row: 0, message: 'Файл пуст или содержит только заголовок' }]);
          return;
        }

        const headers = jsonData[0];
        const rows = jsonData.slice(1).filter(row => row.some(cell => cell));
        
        // Валидация заголовков
        const requiredHeaders = ['ФИО', 'Email'];
        const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
        
        if (missingHeaders.length > 0) {
          setErrors([{ 
            row: 0, 
            message: `Отсутствуют обязательные колонки: ${missingHeaders.join(', ')}` 
          }]);
          return;
        }

        // Создаем маппинг индексов колонок
        const columnIndexes = {};
        headers.forEach((header, index) => {
          const fieldName = COLUMN_MAPPING[header];
          if (fieldName) {
            columnIndexes[fieldName] = index;
          }
        });

        // Собираем email существующих пользователей для проверки дублей
        const existingEmails = new Set(users.map(u => u.email?.toLowerCase()));

        // Парсим строки
        const parsed = [];
        const parseErrors = [];

        rows.forEach((row, rowIndex) => {
          const user = {
            _rowNum: rowIndex + 2,
            _isValid: true,
            _errors: [],
            _isUpdate: false
          };

          // Извлекаем данные по маппингу
          Object.entries(columnIndexes).forEach(([field, index]) => {
            const value = row[index];
            user[field] = value !== undefined && value !== null ? String(value).trim() : '';
          });

          // Проверяем, это обновление или новая запись
          if (user.id) {
            user._isUpdate = true;
            user.id = parseInt(user.id, 10);
          }

          // Валидация обязательных полей
          if (!user.full_name) {
            user._errors.push('ФИО обязательно');
            user._isValid = false;
          }

          if (!user.email) {
            user._errors.push('Email обязателен');
            user._isValid = false;
          } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(user.email)) {
            user._errors.push('Некорректный email');
            user._isValid = false;
          } else if (!user._isUpdate && existingEmails.has(user.email.toLowerCase())) {
            // Проверка дублей только для новых записей
            user._errors.push('Email уже существует');
            user._isValid = false;
          }

          // Валидация роли
          if (user.role && !VALID_ROLES.includes(user.role.toLowerCase())) {
            user._errors.push(`Неизвестная роль: ${user.role}`);
            user.role = 'employee';
          } else if (user.role) {
            user.role = user.role.toLowerCase();
          } else {
            user.role = 'employee';
          }

          // Валидация категории
          if (user.work_category && !VALID_CATEGORIES.includes(user.work_category.toLowerCase())) {
            user._errors.push(`Неизвестная категория: ${user.work_category}`);
            user.work_category = 'general';
          } else if (user.work_category) {
            user.work_category = user.work_category.toLowerCase();
          } else {
            user.work_category = 'general';
          }

          // Резолвим отдел по названию
          if (user.department_name && options.departments) {
            const dept = options.departments.find(
              d => d.name.toLowerCase() === user.department_name.toLowerCase()
            );
            if (dept) {
              user.department_id = dept.id;
            } else {
              user._errors.push(`Отдел не найден: ${user.department_name}`);
            }
          }

          // Резолвим грейд по коду
          if (user.grade_code && options.grades) {
            const grade = options.grades.find(
              g => g.code.toLowerCase() === user.grade_code.toLowerCase()
            );
            if (grade) {
              user.grade_id = grade.id;
            } else {
              user._errors.push(`Грейд не найден: ${user.grade_code}`);
            }
          }

          // Резолвим руководителя по email из существующих пользователей
          if (user.manager_email) {
            const managerEmail = user.manager_email.toLowerCase();
            const manager = users.find(u => u.email?.toLowerCase() === managerEmail);
            if (manager) {
              user.manager_id = manager.id;
            } else {
              // Предупреждение, но не ошибка - руководитель может быть добавлен позже
              user._errors.push(`Руководитель не найден: ${user.manager_email}`);
            }
          }

          if (!user._isValid || user._errors.length > 0) {
            parseErrors.push({
              row: user._rowNum,
              message: user._errors.join('; ')
            });
          }

          parsed.push(user);
        });

        setParsedData(parsed);
        setErrors(parseErrors);
        setStep('preview');
      } catch (err) {
        setErrors([{ row: 0, message: `Ошибка чтения файла: ${err.message}` }]);
      }
    };

    reader.readAsArrayBuffer(file);
  }, [options, users]);

  // Обработка выбора файла
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.match(/\.(xlsx|xls)$/i)) {
        setErrors([{ row: 0, message: 'Поддерживаются только файлы .xlsx и .xls' }]);
        return;
      }
      setFile(selectedFile);
      setErrors([]);
      parseFile(selectedFile);
    }
  };

  // Drag & Drop
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      if (!droppedFile.name.match(/\.(xlsx|xls)$/i)) {
        setErrors([{ row: 0, message: 'Поддерживаются только файлы .xlsx и .xls' }]);
        return;
      }
      setFile(droppedFile);
      setErrors([]);
      parseFile(droppedFile);
    }
  }, [parseFile]);

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  // Удаление строки из превью
  const removeRow = (rowNum) => {
    setParsedData(prev => prev.filter(u => u._rowNum !== rowNum));
    setErrors(prev => prev.filter(e => e.row !== rowNum));
  };

  // Импорт данных
  const handleImport = async () => {
    const validUsers = parsedData.filter(u => u._isValid);
    
    if (validUsers.length === 0) {
      setErrors([{ row: 0, message: 'Нет валидных записей для импорта' }]);
      return;
    }

    setImporting(true);
    
    try {
      // Подготавливаем данные для отправки
      const usersToImport = validUsers.map(u => ({
        id: u._isUpdate ? u.id : undefined,
        full_name: u.full_name,
        email: u.email,
        job_title: u.job_title || '',
        role: u.role,
        work_category: u.work_category,
        department_id: u.department_id || null,
        grade_id: u.grade_id || null,
        manager_id: u.manager_id || null,
        manager_email: u.manager_email || null  // передаём email менеджера для резолва в хуке
      }));

      await onImport(usersToImport);
      
      setImportResult({
        success: true,
        count: usersToImport.length,
        updates: usersToImport.filter(u => u.id).length,
        creates: usersToImport.filter(u => !u.id).length
      });
      setStep('result');
    } catch (err) {
      setImportResult({
        success: false,
        message: err.message || 'Ошибка при импорте'
      });
      setStep('result');
    } finally {
      setImporting(false);
    }
  };

  if (!isOpen) return null;

  const validCount = parsedData.filter(u => u._isValid).length;
  const invalidCount = parsedData.filter(u => !u._isValid).length;
  const updateCount = parsedData.filter(u => u._isUpdate && u._isValid).length;
  const createCount = parsedData.filter(u => !u._isUpdate && u._isValid).length;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleClose}
    >
      <div 
        className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Импорт / Экспорт сотрудников</h2>
              <p className="text-sm text-gray-500">Excel-файл (.xlsx)</p>
            </div>
          </div>
          <button 
            type="button" 
            onClick={handleClose} 
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 'upload' && (
            <div className="space-y-6">
              {/* Кнопка экспорта */}
              <div className="bg-green-50 border border-green-200 rounded-xl p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-green-900 mb-1">Экспорт текущей базы</h3>
                    <p className="text-sm text-green-700">
                      Скачайте файл с {users.length} сотрудниками для редактирования
                    </p>
                  </div>
                  <button
                    onClick={handleExport}
                    disabled={users.length === 0}
                    className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <FileDown className="w-5 h-5" />
                    Скачать XLSX
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex-1 h-px bg-gray-200"></div>
                <span className="text-sm text-gray-400 font-medium">или</span>
                <div className="flex-1 h-px bg-gray-200"></div>
              </div>

              {/* Зона загрузки */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition-all"
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-700 mb-2">
                  Загрузить файл для импорта
                </p>
                <p className="text-sm text-gray-500">
                  Перетащите файл сюда или нажмите для выбора
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* Ошибки */}
              {errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-red-700 font-medium mb-2">
                    <AlertCircle className="w-5 h-5" />
                    Ошибки
                  </div>
                  <ul className="text-sm text-red-600 space-y-1">
                    {errors.map((err, i) => (
                      <li key={i}>
                        {err.row > 0 && `Строка ${err.row}: `}{err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Инструкция */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <h3 className="font-medium text-blue-900 mb-2">Как пользоваться</h3>
                <ol className="text-sm text-blue-700 space-y-2 list-decimal list-inside">
                  <li>Нажмите <strong>"Скачать XLSX"</strong> для экспорта текущих данных</li>
                  <li>Отредактируйте файл в Excel: измените данные или добавьте новые строки</li>
                  <li>Загрузите отредактированный файл обратно</li>
                  <li>Записи с ID будут обновлены, без ID — созданы как новые</li>
                </ol>
              </div>
            </div>
          )}

          {step === 'preview' && (
            <div className="space-y-4">
              {/* Статистика */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-gray-900">{parsedData.length}</div>
                  <div className="text-xs text-gray-500">Всего строк</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-green-600">{validCount}</div>
                  <div className="text-xs text-green-600">Валидных</div>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-blue-600">{updateCount}</div>
                  <div className="text-xs text-blue-600">Обновлений</div>
                </div>
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-purple-600">{createCount}</div>
                  <div className="text-xs text-purple-600">Новых</div>
                </div>
              </div>

              {invalidCount > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                  <span className="text-amber-700 text-sm">
                    {invalidCount} записей с ошибками будут пропущены
                  </span>
                </div>
              )}

              {/* Таблица превью */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="overflow-x-auto max-h-[400px]">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs">Тип</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs">ФИО</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs">Email</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs">Роль</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs">Отдел</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs">Статус</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600 text-xs"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {parsedData.map((user) => (
                        <tr 
                          key={user._rowNum} 
                          className={user._isValid ? 'bg-white' : 'bg-red-50'}
                        >
                          <td className="px-3 py-2">
                            {user._isUpdate ? (
                              <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                                UPD
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                                NEW
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2 font-medium text-gray-900">{user.full_name}</td>
                          <td className="px-3 py-2 text-gray-600">{user.email}</td>
                          <td className="px-3 py-2">
                            <span className="px-2 py-0.5 bg-gray-100 rounded text-xs font-medium">
                              {user.role}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-gray-600 text-xs">{user.department_name || '-'}</td>
                          <td className="px-3 py-2">
                            {user._isValid ? (
                              <span className="flex items-center gap-1 text-green-600 text-xs">
                                <CheckCircle className="w-3.5 h-3.5" />
                                OK
                              </span>
                            ) : (
                              <span className="text-red-600 text-xs truncate max-w-[150px]" title={user._errors.join('; ')}>
                                {user._errors[0]}
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <button
                              onClick={() => removeRow(user._rowNum)}
                              className="p-1 hover:bg-gray-100 rounded transition-colors"
                              title="Удалить из импорта"
                            >
                              <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {step === 'result' && importResult && (
            <div className="text-center py-8">
              {importResult.success ? (
                <>
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Импорт завершён!</h3>
                  <p className="text-gray-600 mb-4">
                    Обработано {importResult.count} записей
                  </p>
                  <div className="flex justify-center gap-4 text-sm">
                    {importResult.updates > 0 && (
                      <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full">
                        Обновлено: {importResult.updates}
                      </span>
                    )}
                    {importResult.creates > 0 && (
                      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full">
                        Создано: {importResult.creates}
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertCircle className="w-8 h-8 text-red-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Ошибка импорта</h3>
                  <p className="text-red-600">{importResult.message}</p>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-between items-center shrink-0">
          <div>
            {file && step === 'preview' && (
              <span className="text-sm text-gray-500">
                Файл: {file.name}
              </span>
            )}
          </div>
          <div className="flex gap-3">
            {step === 'preview' && (
              <button
                onClick={resetState}
                className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors"
              >
                Назад
              </button>
            )}
            
            {step === 'upload' && (
              <button
                onClick={handleClose}
                className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors"
              >
                Закрыть
              </button>
            )}

            {step === 'preview' && (
              <button
                onClick={handleImport}
                disabled={validCount === 0 || importing}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Импорт...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Импортировать {validCount} записей
                  </>
                )}
              </button>
            )}

            {step === 'result' && (
              <button
                onClick={handleClose}
                className="px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md"
              >
                Закрыть
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserImportModal;
