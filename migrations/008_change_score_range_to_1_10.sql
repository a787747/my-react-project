-- Миграция: Изменение диапазона оценок с 0-10 на 1-10
-- Дата: 2025-12-21

-- Удаление коэффициентов для уровня 0
DELETE FROM performance_db.score_coefficients WHERE score_level = 0;

-- Очистка описаний уровня 0
UPDATE performance_db.criteria SET level_0_desc = NULL;

-- Обновление CHECK constraint
ALTER TABLE performance_db.score_coefficients 
  DROP CONSTRAINT score_coefficients_score_level_check,
  ADD CONSTRAINT score_coefficients_score_level_check 
    CHECK (score_level >= 1 AND score_level <= 10);





