/**
 * EmploymentStatusModal — отметить увольнение или восстановить сотрудника
 *
 * Назначение: подтверждение обратимого изменения состояния занятости (D-0825-7).
 * Используется в: AdminUsers
 *
 * Увольнение — это состояние, а не удаление. Ни одна оценка не удаляется,
 * ничего не пересчитывается. Окно объясняет последствия до нажатия, потому что
 * последствие — деньги: исключённый из охвата человек не получает доли
 * премиального фонда за период, и фонд перераспределяется между остальными.
 *
 * Props:
 * - isOpen: boolean
 * - mode: 'terminate' | 'reinstate'
 * - user: object | null — сотрудник
 * - saving: boolean
 * - error: string | null — сообщение сервера (например, «есть подчинённые»)
 * - onClose: function
 * - onConfirm: function({ terminationDate, note })
 */

import React, { useState, useEffect } from 'react';
import { X, UserMinus, UserCheck, Loader2, AlertTriangle } from 'lucide-react';

const todayIso = () => {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
};

const EmploymentStatusModal = ({
  isOpen,
  mode = 'terminate',
  user,
  saving,
  error,
  onClose,
  onConfirm
}) => {
  const isTerminate = mode === 'terminate';
  const [terminationDate, setTerminationDate] = useState(todayIso());
  const [note, setNote] = useState('');
  const [dateError, setDateError] = useState('');

  // Reset on open / on a different target, during render rather than in an
  // effect: an effect here would setState synchronously and cascade a render
  // (react-hooks/set-state-in-effect). This is React's documented pattern for
  // "state that changes when a prop changes".
  const openKey = isOpen ? `${mode}:${user?.id ?? ''}` : null;
  const [lastOpenKey, setLastOpenKey] = useState(null);
  if (openKey !== lastOpenKey) {
    setLastOpenKey(openKey);
    setTerminationDate(user?.termination_date || todayIso());
    setNote('');
    setDateError('');
  }

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen && !saving) onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, saving, onClose]);

  if (!isOpen || !user) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isTerminate) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(terminationDate)) {
        setDateError('Укажите дату в формате ГГГГ-ММ-ДД');
        return;
      }
      setDateError('');
    }
    onConfirm({ terminationDate, note });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={() => { if (!saving) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="employment-modal-title"
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="p-6 border-b border-gray-100 flex justify-between items-center">
            <h2 id="employment-modal-title" className="text-xl font-bold text-gray-900 flex items-center gap-2">
              {isTerminate
                ? <><UserMinus className="w-5 h-5 text-red-600" /> Отметить увольнение</>
                : <><UserCheck className="w-5 h-5 text-emerald-600" /> Восстановить сотрудника</>}
            </h2>
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50"
              aria-label="Закрыть"
            >
              <X className="w-6 h-6 text-gray-400" />
            </button>
          </div>

          <div className="p-6 space-y-4">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <div className="font-semibold text-gray-900">{user.full_name}</div>
              <div className="text-sm text-gray-500">{user.email}</div>
              {user.job_title && <div className="text-sm text-gray-500">{user.job_title}</div>}
            </div>

            {isTerminate ? (
              <>
                <div>
                  <label htmlFor="termination_date" className="block text-sm font-medium text-gray-700 mb-1">
                    Дата увольнения (последний рабочий день) <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="termination_date"
                    type="date"
                    value={terminationDate}
                    onChange={(e) => setTerminationDate(e.target.value)}
                    className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all ${
                      dateError ? 'border-red-300 bg-red-50' : 'border-gray-300'
                    }`}
                  />
                  {dateError && <p className="text-red-500 text-xs mt-1">{dateError}</p>}
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900 space-y-2">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertTriangle className="w-4 h-4" /> Что произойдёт
                  </div>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Сотрудник исчезнет из рабочего списка и из задач своего руководителя.</li>
                    <li>Его собственные незавершённые задачи исчезнут; войти в портал он больше не сможет.</li>
                    <li>Он выйдет из охвата текущего периода и <b>не получит доли премиального фонда</b> за него — фонд перераспределится между остальными.</li>
                    <li>Оценки, которые он <b>поставил другим</b>, остаются в силе и продолжают влиять на их результаты.</li>
                    <li>Ни одна оценка не удаляется. Действие обратимо кнопкой «Восстановить».</li>
                  </ul>
                </div>
              </>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-sm text-emerald-900 space-y-2">
                <p>
                  Сотрудник вернётся в рабочий список и в охват тех незакрытых периодов,
                  из которых его вывело именно увольнение.
                  {user.termination_date && (
                    <> Отметка об увольнении от <b>{user.termination_date}</b> будет снята.</>
                  )}
                </p>
                <p>
                  Прежние сессии не восстанавливаются: войти нужно заново.
                  Закрытые периоды и сохранённые в них результаты не меняются.
                </p>
              </div>
            )}

            <div>
              <label htmlFor="employment_note" className="block text-sm font-medium text-gray-700 mb-1">
                Комментарий (необязательно)
              </label>
              <input
                id="employment_note"
                type="text"
                maxLength={500}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                placeholder="Останется в журнале событий"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
                {error}
              </div>
            )}
          </div>

          <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 rounded-b-2xl">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={saving}
              className={`flex items-center gap-2 px-5 py-2.5 text-white font-medium rounded-lg transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                isTerminate
                  ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                  : 'bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500'
              }`}
            >
              {saving
                ? <Loader2 className="w-5 h-5 animate-spin" />
                : (isTerminate ? <UserMinus className="w-5 h-5" /> : <UserCheck className="w-5 h-5" />)}
              {saving
                ? 'Сохранение...'
                : (isTerminate ? 'Отметить увольнение' : 'Восстановить')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EmploymentStatusModal;
