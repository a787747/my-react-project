-- Миграция 004: Добавление роли HR
-- Дата: 2025-12-20
-- Описание: Добавляет новый тип пользователя HR для управления сотрудниками и мониторинга оценок

-- 1. Добавляем значение 'hr' в enum type user_role_type
ALTER TYPE performance_db.user_role_type ADD VALUE IF NOT EXISTS 'hr';

-- 2. Создаём пользователя HR
INSERT INTO performance_db.users (
    full_name,
    email,
    password_hash,
    role,
    job_title,
    employment_type,
    join_date,
    created_at
) VALUES (
    'HR Manager',
    'hr@sedamedical.com',
    '12345',
    'hr',
    'HR Manager',
    'Full-time',
    CURRENT_DATE,
    CURRENT_TIMESTAMP
)
ON CONFLICT (email) DO UPDATE SET
    password_hash = '12345',
    role = 'hr'::performance_db.user_role_type;

-- Примечание: HR имеет следующие права:
-- ✓ Добавление/редактирование сотрудников
-- ✓ Просмотр статуса самооценок
-- ✓ Просмотр статуса оценок руководителей
-- ✓ Просмотр статуса оценок подчинённых
-- ✗ Не может оценивать сотрудников





