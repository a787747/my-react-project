/**
 * PeerRecognition — страница «Отметить коллегу» (brief PEER_RECOGNITION, 2026-08-27)
 *
 * Назначение: любой сотрудник может отметить ОДНОГО коллегу, чья помощь реально
 * повлияла на его работу, и описать это тремя короткими полями.
 * Доступ: ProtectedRoute — любой авторизованный, включая тех, кто вне охвата
 * H1 и не имеет ни одной задачи по оценке. Именно они видят помощь между
 * отделами, которую руководство не видит.
 *
 * Это НЕ часть формы оценки и не поле внутри неё. Форма оценки этой страницей
 * не затрагивается: люди уже сдали оценки и поля внутри неё никогда бы не
 * увидели, а трогать форму во время идущей кампании нельзя.
 *
 * Данные: usePeerRecognition → GET /api/recognition/form (один запрос),
 * сохранение → POST /api/recognition/save. Списки «можно» и «нельзя» строит
 * сервер; те же три отказа он проверяет заново при сохранении, поэтому прямой
 * вызов маршрута мимо экрана отказывает так же.
 *
 * Тексты заголовка, пояснения, подписей полей и подсказок — владельца, дословно.
 * Менять их нельзя: форма, которая спрашивает ситуацию, действие и результат,
 * не заполняется «за приятного человека», и в этом весь смысл конструкции.
 *
 * Счётчиков здесь нет и быть не может: ни числа отметок, ни бейджа, ни
 * сортировки по частоте. Маршрут их не отдаёт.
 */

import React, { useMemo, useState } from 'react';
import { HeartHandshake, Search, Check, Info, AlertCircle, Ban } from 'lucide-react';

import { LoadingSpinner } from '../components/common';
import { useToast } from '../context/ToastContext';
import { usePeerRecognition } from '../hooks/usePeerRecognition';

// Дословные тексты владельца. Одно место, чтобы правка формулировки была
// правкой решения, а не случайной опечаткой в разметке.
const COPY = {
  title: 'Кто помог вам в этом полугодии',
  intro: [
    'Необязательно. Можно отметить одного человека, чья помощь реально повлияла на вашу работу или на результат для клиента.',
    'Это не голосование и не рейтинг. Количество отметок нигде не подсчитывается и ни на чью премию не влияет. Смысл в другом: руководство почти не видит помощь, которая происходит между отделами, — а видите её вы.',
    'Не нужно отмечать за то, что с человеком приятно работать или он выручил по мелочи. Это нормальные рабочие отношения, а не то, о чём стоит сообщать отдельно.'
  ],
  nomineeLabel: 'Кого вы отмечаете',
  fields: [
    {
      key: 'situation',
      label: 'В какой ситуации это было?',
      hint: 'Например: срочная поставка, сложный монтаж, проблема у клиента, чужая задача, которую некому было закрыть.'
    },
    {
      key: 'action',
      label: 'Что конкретно он или она сделал(а)?',
      hint: 'Действие, а не качество характера.'
    },
    {
      key: 'outcome',
      label: 'Что изменилось благодаря этому?',
      hint: 'Для вас, для проекта или для клиента.'
    }
  ]
};

const MAX_TEXT = 2000;

const personSubtitle = (person) =>
  [person.job_title, person.department_name].filter(Boolean).join(' · ');

const PeerRecognition = ({ user }) => {
  const toast = useToast();
  const {
    period,
    colleagues,
    blocked,
    myNomination,
    loading,
    saving,
    error,
    save
  } = usePeerRecognition(user);

  const [search, setSearch] = useState('');
  const [nomineeId, setNomineeId] = useState(null);
  const [texts, setTexts] = useState({ situation: '', action: '', outcome: '' });
  // Причина отказа по конкретному человеку — приходит с сервера словами.
  const [blockedMessage, setBlockedMessage] = useState(null);

  // Существующая отметка открывается заполненной: её можно заменить, пока
  // период не закрыт, и «заменить» значит переписать ту же строку.
  // Подстройка состояния во время рендера, а не в эффекте — рекомендованный
  // React способ синхронизировать форму с пришедшими данными без лишнего
  // каскада рендеров.
  const [hydratedFrom, setHydratedFrom] = useState(null);
  const nominationKey = myNomination ? `${myNomination.id}:${myNomination.updated_at}` : null;
  if (nominationKey && nominationKey !== hydratedFrom) {
    setHydratedFrom(nominationKey);
    setNomineeId(myNomination.nominee_id);
    setTexts({
      situation: myNomination.situation || '',
      action: myNomination.action || '',
      outcome: myNomination.outcome || ''
    });
  }

  const allPeople = useMemo(
    () =>
      [...colleagues.map((p) => ({ ...p, blocked_reason: null })), ...blocked].sort((a, b) =>
        String(a.full_name || '').localeCompare(String(b.full_name || ''), 'ru')
      ),
    [colleagues, blocked]
  );

  const visiblePeople = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return allPeople;
    return allPeople.filter((person) =>
      [person.full_name, person.job_title, person.department_name]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle))
    );
  }, [allPeople, search]);

  const selected = useMemo(
    () => colleagues.find((person) => person.id === nomineeId) || null,
    [colleagues, nomineeId]
  );

  const handlePick = (person) => {
    if (person.blocked_reason) {
      // Экран говорит словами, почему нельзя, вместо того чтобы просто не
      // реагировать на клик. Сервер откажет тем же текстом.
      setBlockedMessage(person.message);
      return;
    }
    setBlockedMessage(null);
    setNomineeId(person.id);
  };

  const canSubmit =
    !!selected &&
    !!texts.situation.trim() &&
    !!texts.action.trim() &&
    !!texts.outcome.trim() &&
    !saving;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    const result = await save({
      nomineeId: selected.id,
      situation: texts.situation.trim(),
      action: texts.action.trim(),
      outcome: texts.outcome.trim()
    });
    if (result.ok) {
      toast.success(result.message);
    } else {
      toast.error(result.message);
    }
  };

  if (loading) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <LoadingSpinner text="Загрузка..." />
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center">
              <HeartHandshake className="w-5 h-5 text-brand-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900">{COPY.title}</h1>
          </div>
          {period?.name && (
            <p className="text-gray-500 text-sm">
              Период: {period.name}
              {period.start_date && period.end_date
                ? ` (${period.start_date} — ${period.end_date})`
                : ''}
            </p>
          )}
        </div>

        {/* Пояснение владельца, дословно */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6 shadow-sm">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-brand-500 flex-shrink-0 mt-0.5" />
            <div className="space-y-3 text-gray-700 text-sm leading-relaxed">
              {COPY.intro.map((paragraph) => (
                <p key={paragraph.slice(0, 24)}>{paragraph}</p>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
            <p className="text-danger-800 text-sm">{error}</p>
          </div>
        )}

        {!period && !error && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-amber-800 text-sm">
              Сейчас нет открытого периода — отметить коллегу можно только внутри периода.
            </p>
          </div>
        )}

        {myNomination && (
          <div className="bg-success-50 border border-success-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <Check className="w-5 h-5 text-success-600 flex-shrink-0 mt-0.5" />
            <p className="text-success-800 text-sm">
              Вы уже отметили: <strong>{myNomination.nominee_name}</strong>. Отметку можно
              заменить — она останется одна.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          {/* Кого вы отмечаете */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              {COPY.nomineeLabel}
            </label>

            {selected && (
              <div className="mb-3 flex items-center justify-between gap-3 bg-brand-50 border border-brand-200 rounded-lg px-4 py-3">
                <div>
                  <div className="font-medium text-gray-900">{selected.full_name}</div>
                  {personSubtitle(selected) && (
                    <div className="text-xs text-gray-500">{personSubtitle(selected)}</div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setNomineeId(null)}
                  className="text-xs text-gray-500 hover:text-gray-900 underline"
                >
                  изменить
                </button>
              </div>
            )}

            <div className="relative mb-2">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Поиск по имени, должности или отделу"
                aria-label="Поиск коллеги"
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="border border-gray-200 rounded-lg max-h-72 overflow-y-auto divide-y divide-gray-100">
              {visiblePeople.length === 0 && (
                <p className="px-4 py-6 text-sm text-gray-500 text-center">Никого не найдено</p>
              )}
              {visiblePeople.map((person) => {
                const isBlocked = !!person.blocked_reason;
                const isSelected = person.id === nomineeId;
                return (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => handlePick(person)}
                    aria-disabled={isBlocked}
                    className={`w-full text-left px-4 py-2.5 flex items-center justify-between gap-3 transition-colors ${
                      isBlocked
                        ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                        : isSelected
                          ? 'bg-brand-50 text-gray-900'
                          : 'hover:bg-gray-50 text-gray-900'
                    }`}
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-medium truncate">{person.full_name}</span>
                      {personSubtitle(person) && (
                        <span className="block text-xs text-gray-400 truncate">
                          {personSubtitle(person)}
                        </span>
                      )}
                    </span>
                    {isBlocked ? (
                      <Ban className="w-4 h-4 flex-shrink-0" />
                    ) : isSelected ? (
                      <Check className="w-4 h-4 text-brand-600 flex-shrink-0" />
                    ) : null}
                  </button>
                );
              })}
            </div>

            {blockedMessage && (
              <p className="mt-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                {blockedMessage}
              </p>
            )}
          </div>

          {/* Три поля */}
          {COPY.fields.map((field) => (
            <div className="mb-6" key={field.key}>
              <label
                htmlFor={`recognition-${field.key}`}
                className="block text-sm font-semibold text-gray-900 mb-1"
              >
                {field.label}
              </label>
              <p className="text-xs text-gray-500 mb-2">{field.hint}</p>
              <textarea
                id={`recognition-${field.key}`}
                rows={3}
                maxLength={MAX_TEXT}
                value={texts[field.key]}
                onChange={(event) =>
                  setTexts((prev) => ({ ...prev, [field.key]: event.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          ))}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={!canSubmit}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                canSubmit
                  ? 'bg-brand-600 text-white hover:bg-brand-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {saving ? 'Сохранение...' : myNomination ? 'Заменить отметку' : 'Отметить'}
            </button>
            <span className="text-xs text-gray-400">
              Одна отметка на период. Её можно заменить, пока период не закрыт.
            </span>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PeerRecognition;
