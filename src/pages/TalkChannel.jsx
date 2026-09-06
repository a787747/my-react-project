import React, { useState } from 'react';
import { AlertCircle, CheckCircle, MessageCircle } from 'lucide-react';

import { LoadingSpinner } from '../components/common';
import { useToast } from '../context/ToastContext';
import { TALK_COPY, TALK_SENSITIVE_TOPICS } from '../content/talkCopy';
import { useTalkChannel } from '../hooks/useTalkChannel';

const emptyForm = {
  answer_key: '',
  topic_key: null,
  counterpart_mode: 'help_choose',
  counterpart_ids: [],
  urgency_key: 'this_cycle',
  group_readiness_key: 'individual_only',
};

const TalkChannel = ({ user }) => {
  const toast = useToast();
  const {
    wave, topics, counterparts, myResponse, loading, saving, withdrawing, error, save, withdraw,
  } = useTalkChannel(user);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const startEdit = () => {
    if (myResponse) {
      setForm({
        answer_key: myResponse.answer_key,
        topic_key: myResponse.topic_key,
        counterpart_mode: myResponse.counterpart_mode,
        counterpart_ids: myResponse.counterpart_ids || [],
        urgency_key: myResponse.urgency_key || 'this_cycle',
        group_readiness_key: myResponse.group_readiness_key || 'individual_only',
      });
    } else {
      setForm(emptyForm);
    }
    setEditing(true);
  };

  const selectAnswer = (answerKey) => {
    setForm((current) => ({
      ...emptyForm,
      answer_key: answerKey,
      topic_key: answerKey === 'all_good' ? null : current.topic_key,
    }));
  };

  const selectTopic = (topicKey) => {
    setForm((current) => ({
      ...current,
      topic_key: topicKey,
      counterpart_ids:
        topicKey === 't10_manager'
          ? current.counterpart_ids.filter(
            (id) => !counterparts.some((person) => person.id === id && person.is_own_manager),
          )
          : current.counterpart_ids,
      group_readiness_key: TALK_SENSITIVE_TOPICS.has(topicKey)
        ? 'individual_only'
        : current.group_readiness_key,
    }));
  };

  const chooseMode = (mode) => {
    setForm((current) => ({ ...current, counterpart_mode: mode, counterpart_ids: [] }));
  };

  const toggleCounterpart = (id) => {
    setForm((current) => {
      const selected = current.counterpart_ids.includes(id);
      return {
        ...current,
        counterpart_mode: 'people',
        counterpart_ids: selected
          ? current.counterpart_ids.filter((value) => value !== id)
          : [...current.counterpart_ids, id],
      };
    });
  };

  const canSubmit =
    form.answer_key === 'all_good'
    || (form.answer_key === 'topic_only' && !!form.topic_key)
    || (
      form.answer_key === 'conversation'
      && !!form.topic_key
      && !!form.urgency_key
      && !!form.group_readiness_key
      && (
        (form.counterpart_mode === 'people' && form.counterpart_ids.length > 0)
        || ['help_choose', 'all_leadership'].includes(form.counterpart_mode)
      )
    );

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit || saving) return;
    const payload = form.answer_key === 'all_good'
      ? {
        answer_key: 'all_good', topic_key: null, counterpart_mode: 'none',
        counterpart_ids: [], urgency_key: null, group_readiness_key: null,
      }
      : form.answer_key === 'topic_only'
        ? {
          answer_key: 'topic_only', topic_key: form.topic_key, counterpart_mode: 'none',
          counterpart_ids: [], urgency_key: null, group_readiness_key: null,
        }
        : form;
    const result = await save(payload);
    if (result.ok) {
      setEditing(false);
      toast.success('Ответ получен');
    } else {
      toast.error(result.message);
    }
  };

  const handleWithdraw = async () => {
    if (!window.confirm('Снять ответ?')) return;
    const result = await withdraw();
    if (result.ok) {
      setEditing(false);
      toast.success(result.message);
    } else {
      toast.error(result.message);
    }
  };

  if (loading) return <LoadingSpinner text="Загрузка..." />;

  const availableCounterparts = form.topic_key === 't10_manager'
    ? counterparts.filter((person) => !person.is_own_manager)
    : counterparts;

  return (
    <div className="min-h-screen bg-surface-raised p-4 lg:p-8">
      <div className="max-w-3xl mx-auto">
        <header className="mb-6 flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-brand-100 flex items-center justify-center">
            <MessageCircle className="w-6 h-6 text-brand-600" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">{TALK_COPY.title}</h1>
        </header>

        <section className="card p-6 mb-6 space-y-4 text-sm text-slate-700 leading-relaxed">
          {TALK_COPY.intro.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          {wave?.deadline_text && (
            <p className="font-semibold">Ответить можно до {wave.deadline_text}.</p>
          )}
        </section>

        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4 text-danger-800">
            {error}
          </div>
        )}

        {wave && !wave.is_open && (
          <div className="bg-slate-100 border border-slate-200 rounded-xl p-6 flex gap-3">
            <AlertCircle className="w-5 h-5 text-slate-500 shrink-0" />
            <p className="text-slate-700">Срок ответа завершён.</p>
          </div>
        )}

        {wave?.is_open && myResponse && !editing && (
          <div className="bg-success-50 border border-success-200 rounded-xl p-8 text-center">
            <CheckCircle className="w-12 h-12 text-success-600 mx-auto mb-3" />
            <h2 className="text-xl font-bold text-success-900 mb-5">Ответ получен</h2>
            <div className="flex justify-center gap-3">
              <button type="button" onClick={startEdit} className="btn-primary">Изменить ответ</button>
              <button
                type="button"
                disabled={withdrawing}
                onClick={handleWithdraw}
                className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700"
              >
                {withdrawing ? 'Снятие...' : 'Снять ответ'}
              </button>
            </div>
          </div>
        )}

        {wave?.is_open && (!myResponse || editing) && (
          <form onSubmit={handleSubmit} className="card p-6 space-y-6">
            <fieldset>
              <legend className="text-lg font-bold text-slate-900 mb-3">{TALK_COPY.question}</legend>
              <div className="space-y-2">
                {Object.entries(TALK_COPY.answers).map(([key, label]) => (
                  <label key={key} className="flex gap-3 p-3 border rounded-lg cursor-pointer">
                    <input
                      type="radio"
                      name="talk-answer"
                      checked={form.answer_key === key}
                      onChange={() => selectAnswer(key)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            {['topic_only', 'conversation'].includes(form.answer_key) && (
              <fieldset>
                <legend className="font-semibold text-slate-900 mb-3">Тема</legend>
                <div className="space-y-2">
                  {topics.map((topic) => (
                    <label key={topic.key} className="flex gap-3 p-3 border rounded-lg cursor-pointer">
                      <input
                        type="radio"
                        name="talk-topic"
                        checked={form.topic_key === topic.key}
                        onChange={() => selectTopic(topic.key)}
                      />
                      <span>{topic.label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            {form.answer_key === 'conversation' && form.topic_key && (
              <>
                <fieldset>
                  <legend className="font-semibold text-slate-900 mb-3">С кем</legend>
                  <div className="space-y-2">
                    <label className="flex gap-3 p-3 border rounded-lg cursor-pointer">
                      <input
                        type="radio"
                        name="talk-counterpart-mode"
                        checked={form.counterpart_mode === 'help_choose'}
                        onChange={() => chooseMode('help_choose')}
                      />
                      <span>{TALK_COPY.specialCounterparts.help_choose}</span>
                    </label>
                    <label className="flex gap-3 p-3 border rounded-lg cursor-pointer">
                      <input
                        type="radio"
                        name="talk-counterpart-mode"
                        checked={form.counterpart_mode === 'all_leadership'}
                        onChange={() => chooseMode('all_leadership')}
                      />
                      <span>
                        {TALK_COPY.specialCounterparts.all_leadership}
                        {form.topic_key === 't10_manager' && (
                          <span className="block text-xs text-slate-500 mt-1">
                            Ваш непосредственный руководитель не будет включён.
                          </span>
                        )}
                      </span>
                    </label>
                    {availableCounterparts.map((person) => (
                      <label key={person.id} className="flex gap-3 p-3 border rounded-lg cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.counterpart_mode === 'people'
                            && form.counterpart_ids.includes(person.id)}
                          onChange={() => toggleCounterpart(person.id)}
                        />
                        <span>{person.full_name}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <fieldset>
                  <legend className="font-semibold text-slate-900 mb-3">Срочность</legend>
                  {Object.entries(TALK_COPY.urgency).map(([key, label]) => (
                    <label key={key} className="flex gap-3 p-3 border rounded-lg mb-2 cursor-pointer">
                      <input
                        type="radio"
                        name="talk-urgency"
                        checked={form.urgency_key === key}
                        onChange={() => setForm((current) => ({ ...current, urgency_key: key }))}
                      />
                      <span>{label}</span>
                    </label>
                  ))}
                </fieldset>

                <fieldset>
                  <legend className="font-semibold text-slate-900 mb-3">{TALK_COPY.groupQuestion}</legend>
                  {Object.entries(TALK_COPY.groupReadiness).map(([key, label]) => (
                    <label key={key} className="flex gap-3 p-3 border rounded-lg mb-2 cursor-pointer">
                      <input
                        type="radio"
                        name="talk-group"
                        checked={form.group_readiness_key === key}
                        onChange={() => setForm((current) => (
                          { ...current, group_readiness_key: key }
                        ))}
                      />
                      <span>{label}</span>
                    </label>
                  ))}
                </fieldset>
              </>
            )}

            <div className="flex gap-3">
              {myResponse && (
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className="px-5 py-2.5 border border-slate-300 rounded-lg"
                >
                  Отмена
                </button>
              )}
              <button
                type="submit"
                disabled={!canSubmit || saving}
                className={`px-5 py-2.5 rounded-lg font-medium ${
                  canSubmit && !saving
                    ? 'bg-brand-600 text-white hover:bg-brand-700'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }`}
              >
                {saving ? 'Сохранение...' : 'Отправить'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default TalkChannel;
