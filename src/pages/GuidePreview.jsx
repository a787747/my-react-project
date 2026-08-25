/**
 * Local-only preview of the H1 rating guide and score bands.
 * Registered only when import.meta.env.DEV — not in the production bundle route table.
 */

import React, { useState } from 'react';
import RatingGuide from '../components/RatingGuide';
import CriterionSlider from '../components/CriterionSlider';

const fixture = (id, title, description, levels) => ({
  id,
  title,
  description,
  is_active: true,
  ...Object.fromEntries(
    Object.entries(levels).map(([n, text]) => [`level_${n}_desc`, text])
  ),
});

const CRIT_QUALITY = fixture(3, 'Личная результативность и эффективность', 'Качество своей функции', {
  5: 'Исполнитель с оговорками. В целом справляется, но требует регулярного внимания.',
  6: 'Качественный профи (Нижняя граница нормы). Надежный сотрудник.',
});

const CRIT_VOLUME = fixture(13, 'Объем проектной работы и загрузка', 'Шкала объёма, не качества', {
  3: 'Малый объём проектной загрузки.',
});

const CRIT_BEYOND = fixture(14, 'Ответственность сверх роли', 'Норма — 2', {
  2: 'Выполнял свою основную функцию. Сверхзадач в периоде не возникало.',
});

const GuidePreview = () => {
  const [qualityFive, setQualityFive] = useState(5);
  const [qualitySix, setQualitySix] = useState(6);
  const [volume, setVolume] = useState(3);
  const [beyond, setBeyond] = useState(2);

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <h1 className="text-2xl font-bold text-slate-900">H1 guide + score bands (local preview)</h1>

        <section data-preview="manager-track">
          <h2 className="text-lg font-semibold text-slate-800 mb-3">Welcome · менеджерский трек</h2>
          <RatingGuide variant="full" />
        </section>

        <section data-preview="employee-track">
          <h2 className="text-lg font-semibold text-slate-800 mb-3">Welcome · трек сотрудника</h2>
          <RatingGuide variant="employee" />
        </section>

        <section data-preview="manager-form">
          <h2 className="text-lg font-semibold text-slate-800 mb-3">Форма оценки менеджера · один клик</h2>
          <RatingGuide variant="full" collapsible defaultOpen={false} />
        </section>

        <section data-preview="bands" className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-800">Зоны на слайдере</h2>
          <CriterionSlider
            criterion={CRIT_QUALITY}
            value={qualityFive}
            onChange={(_id, value) => setQualityFive(parseInt(value, 10))}
            showCommentField={false}
          />
          <CriterionSlider
            criterion={CRIT_QUALITY}
            value={qualitySix}
            onChange={(_id, value) => setQualitySix(parseInt(value, 10))}
            showCommentField={false}
          />
          <CriterionSlider
            criterion={CRIT_BEYOND}
            value={beyond}
            onChange={(_id, value) => setBeyond(parseInt(value, 10))}
            showCommentField={false}
          />
          <CriterionSlider
            criterion={CRIT_VOLUME}
            value={volume}
            onChange={(_id, value) => setVolume(parseInt(value, 10))}
            showCommentField={false}
          />
        </section>
      </div>
    </div>
  );
};

export default GuidePreview;
