-- Миграция: Добавление колонки weighted_score в таблицу evaluations
-- Дата: 2025-12-20
-- Назначение: Хранение взвешенного балла отдельно от простого среднего

-- Добавляем колонку weighted_score для хранения взвешенного балла с коэффициентами
-- calculated_score будет хранить простое среднее (для отображения сотрудникам)
-- weighted_score будет хранить взвешенный балл (для Admin/C-level)

ALTER TABLE performance_db.evaluations 
ADD COLUMN IF NOT EXISTS weighted_score numeric(10, 2) NULL;

-- Для существующих записей копируем calculated_score в weighted_score
-- (так как до этого calculated_score содержал взвешенный балл)
UPDATE performance_db.evaluations 
SET weighted_score = calculated_score 
WHERE weighted_score IS NULL;

COMMENT ON COLUMN performance_db.evaluations.calculated_score IS 'Простое среднее оценок (0-10) - для отображения сотрудникам';
COMMENT ON COLUMN performance_db.evaluations.weighted_score IS 'Взвешенный балл с коэффициентами - для Admin/C-level';





