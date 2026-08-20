-- Миграция: Поддержка иерархических корректировок оценок
-- Дата: 2025-12-20
-- Назначение: Позволить менеджерам менеджеров также корректировать оценки

-- Проверяем, существует ли таблица score_corrections
-- Если нет - создаём, если да - модифицируем

-- Создаём таблицу score_corrections если её нет
CREATE TABLE IF NOT EXISTS performance_db.score_corrections (
    id serial4 NOT NULL,
    subject_id int4 NOT NULL,
    criteria_id int4 NOT NULL,
    evaluator_id int4 NOT NULL,
    correction_score int4 NOT NULL,
    correction_level varchar(20) DEFAULT 'c_level'::character varying NOT NULL,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT score_corrections_pkey PRIMARY KEY (id),
    CONSTRAINT score_corrections_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES performance_db.users(id) ON DELETE CASCADE,
    CONSTRAINT score_corrections_criteria_id_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.users(id) ON DELETE CASCADE,
    CONSTRAINT score_corrections_evaluator_id_fkey FOREIGN KEY (evaluator_id) REFERENCES performance_db.users(id) ON DELETE CASCADE,
    CONSTRAINT score_corrections_score_check CHECK (correction_score >= 0 AND correction_score <= 10)
);

-- Добавляем колонку correction_level если её нет
-- Значения: 'mid_level' - менеджер менеджера, 'c_level' - C-level/admin
ALTER TABLE performance_db.score_corrections 
ADD COLUMN IF NOT EXISTS correction_level varchar(20) DEFAULT 'c_level' NOT NULL;

-- Обновляем уникальный индекс для поддержки разных уровней корректировки
-- Один сотрудник + один критерий + один уровень = одна запись
DROP INDEX IF EXISTS performance_db.idx_score_corrections_unique;
CREATE UNIQUE INDEX IF NOT EXISTS idx_score_corrections_unique 
ON performance_db.score_corrections (subject_id, criteria_id, correction_level);

-- Создаём индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_score_corrections_subject 
ON performance_db.score_corrections (subject_id);

CREATE INDEX IF NOT EXISTS idx_score_corrections_criteria 
ON performance_db.score_corrections (criteria_id);

CREATE INDEX IF NOT EXISTS idx_score_corrections_level 
ON performance_db.score_corrections (correction_level);

-- Комментарии
COMMENT ON COLUMN performance_db.score_corrections.correction_level IS 
'Уровень корректировки: mid_level - менеджер менеджера, c_level - руководство высшего звена';

COMMENT ON TABLE performance_db.score_corrections IS 
'Корректировки оценок от руководителей разных уровней. 
Итоговая оценка = среднее(оценка_менеджера, [коррекция_mid_level], [коррекция_c_level])';





