# Evaluation Portal — Контекст проекта

## 📋 Описание

**Evaluation Portal** — корпоративное веб-приложение для проведения оценки сотрудников (Performance Review). Позволяет менеджерам оценивать подчиненных, сотрудникам — проводить самооценку, а руководству — видеть аналитику и управлять процессом.

## 🛠 Технологический стек

| Технология | Версия | Назначение |
|------------|--------|------------|
| React | 19.x | UI фреймворк |
| Vite | 7.x (rolldown-vite) | Сборщик |
| Tailwind CSS | 3.x | Стилизация |
| React Router | 7.x | Маршрутизация |
| Axios | 1.x | HTTP-клиент |
| Recharts | 3.x | Графики и диаграммы |
| Lucide React | - | Иконки |
| clsx + tailwind-merge | - | Утилиты для CSS классов |
| n8n | - | Backend (webhooks) |
| PostgreSQL | - | База данных |

## 👥 Роли пользователей

| Роль | Права доступа |
|------|---------------|
| `employee` | Самооценка, просмотр своего профиля |
| `manager` | + Оценка подчиненных, история своих оценок |
| `c_level` | + Аналитика, C-level оценки, управление пользователями |
| `admin` | Полный доступ ко всем функциям |
| `hr` | Управление сотрудниками, мониторинг статусов оценок (без возможности оценивать) |

## 🗄 База данных

База данных PostgreSQL со схемой `performance_db`. При написании SQL запросов **всегда используй полный путь**:

```sql
SELECT * FROM performance_db.users;
SELECT * FROM performance_db.evaluations;
```

### Основные таблицы и связи

```
performance_db.users
├── id (PK)
├── full_name, email, job_title
├── password_hash
├── role (admin, c_level, manager, employee, hr)
├── work_category (general, project, hybrid, tender)
├── is_project_participant
├── has_subordinates (boolean) - является ли менеджером (есть ли подчиненные)
├── employment_type, join_date
├── salary_current, salary_proposed
├── department_id → performance_db.departments
├── grade_id → performance_db.grades
└── manager_id → performance_db.users (self-ref)

performance_db.departments
├── id (PK)
├── name (unique)
└── description

performance_db.grades
├── id (PK)
├── code (unique) - например "J1", "M2", "S3"
├── coefficient - коэффициент для расчета бонуса
└── description

performance_db.evaluations
├── id (PK)
├── period_id → performance_db.evaluation_periods
├── subject_id → performance_db.users (кого оценивают)
├── evaluator_id → performance_db.users (кто оценивает)
├── is_self_evaluation (boolean)
├── evaluation_type (manager, self, ...)
├── evaluation_source (manager, subordinate, self) - источник оценки
├── general_comment, private_comment
├── calculated_score
└── status (draft, completed)

performance_db.evaluation_scores
├── id (PK)
├── evaluation_id → performance_db.evaluations (ON DELETE CASCADE)
├── criteria_id → performance_db.criteria
├── score_value (0-10)
└── comment

performance_db.criteria
├── id (PK)
├── title, description, category
├── weight - вес критерия
├── target_audience (all, project_participants, project, tender, managers_only)
├── is_active, selfassesment, for_manager, c_level_only
└── level_0_desc ... level_10_desc

performance_db.evaluation_periods
├── id (PK)
├── name, is_active
└── start_date, end_date

performance_db.score_coefficients
├── id (PK)
├── criteria_id → performance_db.criteria (ON DELETE CASCADE)
├── score_level (0-10)
└── coefficient

performance_db.global_settings
├── setting_key (PK)
├── setting_value
└── description

performance_db.invite_tokens
├── id (PK)
├── token (unique)
├── created_by → performance_db.users
├── created_at, expires_at
├── is_used, used_by, used_at
└── expires_at

performance_db.email_verification_codes
├── id (PK)
├── email
├── code
├── created_at, expires_at
├── is_verified, verified_at
└── attempts
```

## 📁 Структура проекта

```
evaluation-portal/
├── public/
├── src/
│   ├── components/
│   │   ├── common/                     # 🔧 Общие UI компоненты
│   │   │   ├── Toast.jsx              # Уведомления (success/error/info)
│   │   │   ├── LoadingSpinner.jsx     # Индикатор загрузки
│   │   │   ├── EmptyState.jsx         # Пустое состояние
│   │   │   ├── Modal.jsx              # Универсальная модалка
│   │   │   ├── Pagination.jsx         # Пагинация таблиц
│   │   │   ├── Skeleton.jsx           # Скелетон-загрузка
│   │   │   └── index.js               # Экспорты
│   │   │
│   │   ├── admin/                      # 👔 Компоненты админки
│   │   │   ├── UserTable.jsx          # Таблица сотрудников
│   │   │   ├── UserFilters.jsx        # Фильтры сотрудников
│   │   │   ├── UserModal.jsx          # Модалка создания/редактирования
│   │   │   ├── CriteriaTable.jsx      # Таблица критериев
│   │   │   ├── CriteriaForm.jsx       # Форма редактирования критерия
│   │   │   ├── RoleCheckbox.jsx       # Чекбокс ролей оценщика
│   │   │   ├── LevelDescriptions.jsx  # Описания уровней 0-10
│   │   │   ├── MatrixFilters.jsx      # Фильтры матрицы оценок
│   │   │   ├── EvaluationsMatrixTable.jsx  # Таблица матрицы
│   │   │   ├── CLevelEvaluationModal.jsx   # Модалка C-level оценки
│   │   │   ├── AllEvaluationsTable.jsx     # Таблица всех оценок
│   │   │   ├── AllEvaluationsDetailsModal.jsx  # Детали оценки
│   │   │   ├── ScoringCoefficientsTable.jsx    # Таблица коэффициентов
│   │   │   ├── CoefficientRow.jsx     # Строка коэффициента
│   │   │   ├── FinalScoresMatrixTable.jsx  # Матрица итоговых баллов
│   │   │   ├── EmployeeScoresModal.jsx     # Модалка баллов сотрудника
│   │   │   ├── ScoreDetailModal.jsx   # Детали балла
│   │   │   ├── ClearTestEvaluationsModal.jsx  # Очистка тестовых оценок
│   │   │   └── index.js
│   │   │
│   │   ├── evaluation/                 # ⭐ Компоненты оценок
│   │   │   ├── EvaluationBlock.jsx    # Блок оценки с критериями
│   │   │   ├── EvaluationHistoryCard.jsx   # Карточка в истории
│   │   │   ├── EvaluationHistoryModal.jsx  # Модалка деталей
│   │   │   └── index.js
│   │   │
│   │   ├── profile/                    # 👤 Компоненты профиля
│   │   │   ├── ProfileStats.jsx       # Карточки статистики
│   │   │   ├── ProfileChart.jsx       # График динамики оценок
│   │   │   ├── SelfEvaluationCard.jsx # Карточка самооценки
│   │   │   ├── ProfileEvaluationsTable.jsx # Таблица истории
│   │   │   ├── EvaluationDetailsModal.jsx  # Модалка деталей
│   │   │   ├── CriteriaOverview.jsx   # Обзор критериев
│   │   │   └── index.js
│   │   │
│   │   ├── self-review/               # 📝 Компоненты самооценки
│   │   │   ├── SelfReviewStatusCard.jsx    # Карточка статуса
│   │   │   ├── SelfReviewModal.jsx         # Модалка самооценки
│   │   │   └── index.js
│   │   │
│   │   ├── CriterionSlider.jsx        # Слайдер оценки по критерию
│   │   ├── EmployeeCard.jsx           # Карточка сотрудника на дашборде
│   │   ├── EvaluationModal.jsx        # Модалка оценки менеджером
│   │   ├── SelfReviewBanner.jsx       # Баннер напоминания
│   │   └── Sidebar.jsx                # Боковое меню навигации
│   │
│   ├── hooks/                          # 🎣 Кастомные хуки
│   │   ├── useUsers.js                # CRUD пользователей
│   │   ├── useUserFilters.js          # Фильтрация + пагинация
│   │   ├── useCriteria.js             # Управление критериями
│   │   ├── useEvaluationsMatrix.js    # Матрица оценок + фильтры
│   │   ├── useFinalScoresMatrix.js    # Матрица итоговых баллов
│   │   ├── useProfile.js              # Загрузка профиля
│   │   ├── useSelfReview.js           # Логика самооценки
│   │   ├── useAllEvaluations.js       # Все оценки (админ)
│   │   ├── useEvaluationHistory.js    # История оценок
│   │   ├── useDashboardData.js        # Данные дашборда
│   │   ├── useManagerEvaluation.js    # Оценка менеджером
│   │   ├── useHRDashboard.js          # Данные HR дашборда
│   │   └── useScoreCoefficients.js    # Управление коэффициентами
│   │
│   ├── utils/                          # 🔧 Утилиты
│   │   ├── evaluationUtils.js         # calculateFinalScore, filterCriteria, getScoreZone
│   │   ├── matrixUtils.js             # groupCriteria, filterEmployees
│   │   ├── errorHandler.js            # Обработка ошибок API
│   │   ├── logger.js                  # Логирование
│   │   └── permissions.js             # Проверка прав доступа по ролям
│   │
│   ├── config/
│   │   ├── api.js                     # API_ENDPOINTS — все URL эндпоинтов
│   │   └── constants.js               # Константы приложения
│   │
│   ├── context/                        # 🔄 React контексты
│   │   ├── UserContext.jsx            # Контекст пользователя (авторизация)
│   │   ├── ToastContext.jsx           # Контекст уведомлений
│   │   └── TaskStatusContext.jsx      # Контекст статуса задач
│   │
│   ├── api/
│   │   └── client.js                  # HTTP клиент (axios instance)
│   │
│   ├── pages/                          # 📄 Страницы
│   │   ├── Login.jsx                  # Авторизация
│   │   ├── Register.jsx               # Регистрация по инвайт-ссылке
│   │   ├── Welcome.jsx                # Приветственная страница
│   │   ├── Dashboard.jsx              # Главная (список подчиненных)
│   │   ├── TeamView.jsx               # Просмотр команды
│   │   ├── EvaluationHistory.jsx      # История оценок
│   │   ├── Profile.jsx                # Профиль пользователя
│   │   ├── SelfReview.jsx             # Самооценка
│   │   ├── ManagerEvaluation.jsx      # Оценка подчиненных менеджером
│   │   ├── ManagerSubordinatesMatrix.jsx # Матрица подчиненных менеджера
│   │   ├── Analytics.jsx              # Аналитика (admin, c_level)
│   │   ├── BonusCalculation.jsx       # Расчет бонусов
│   │   ├── AdminUsers.jsx             # Управление сотрудниками
│   │   ├── AdminPeriods.jsx           # Управление периодами
│   │   ├── AdminSettings.jsx          # Управление критериями
│   │   ├── AdminScoring.jsx           # Управление коэффициентами оценок
│   │   ├── AdminAllEvaluations.jsx    # Все оценки
│   │   ├── AdminEvaluationsMatrix.jsx # Матрица оценок
│   │   ├── AdminFinalScores.jsx       # Итоговые баллы
│   │   └── HRDashboard.jsx            # HR дашборд (статусы оценок)
│   │
│   ├── App.jsx                        # Роутинг + layout
│   ├── main.jsx                       # Точка входа
│   └── index.css                      # Глобальные стили
│
├── migrations/                        # SQL миграции
│   ├── 001_add_has_subordinates.sql
│   ├── 002_add_evaluation_source.sql
│   ├── 003_add_management_criterion.sql
│   ├── 004_add_hr_role.sql
│   ├── 005_add_weighted_score.sql
│   └── 006_add_hierarchical_corrections.sql
│
├── n8n_workflows/                     # Бэкенд (n8n webhooks) - 35 workflows
│   ├── API_ Auth Login (No Params).json
│   ├── API_ Get Employees (Smart Role Based).json
│   ├── API_ Submit Evaluation.json
│   ├── API_ Register.json
│   ├── API_ Create Invite.json
│   ├── API_ Verify Invite.json
│   ├── API_ Score Correction.json
│   ├── API_ Get Score Coefficients.json
│   ├── API_ Save Score Coefficients.json
│   ├── API_ Manager Subordinates Matrix.json
│   └── ... (и другие)
│
├── schema.sql                         # Схема БД PostgreSQL
├── package.json
├── vite.config.js
├── tailwind.config.js
└── eslint.config.js
```

## 🔗 API Эндпоинты (n8n)

Все запросы идут на `http://92.51.45.147:5678/webhook/...`

### Авторизация и регистрация

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/auth/login` | POST | Авторизация |
| `/api/register` | POST | Регистрация нового пользователя |
| `/api/verify-invite` | POST | Проверка инвайт-токена |
| `/api/admin/create-invite` | POST | Создание инвайт-ссылки |
| `/api/send-verification-code` | POST | Отправка кода верификации |
| `/api/verify-code` | POST | Проверка кода верификации |

### Сотрудники

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/employees` | GET | Список подчиненных |
| `/api/my-profile` | GET | Профиль пользователя |
| `/api/get-my-manager` | GET | Информация о менеджере пользователя |

### Оценки

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/criteria` | GET | Критерии |
| `/api/submit-evaluation` | POST | Отправка оценки |
| `/api/update-evaluation` | POST | Обновление оценки |
| `/api/evaluation-details` | GET | Детали оценки |
| `/api/evaluation-history` | GET | История оценок |
| `/api/check-evaluated` | GET | Проверка статуса оценки |

### Самооценка

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/self-review-submit` | POST | Отправка самооценки |
| `/api/check-self-review` | GET | Проверка самооценки |
| `/api/employee-self-review` | GET | Получение самооценки сотрудника |

### Периоды

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/periods` | GET | Список периодов |
| `/api/periods/create` | POST | Создание периода |
| `/api/periods/activate` | POST | Активация периода |
| `/manage-periods` | POST | CRUD периодов |

### Админ: Пользователи

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/admin-users-data` | GET | Список пользователей |
| `/admin/save-user` | POST | Сохранение пользователя |
| `/manage-criteria` | POST | CRUD критериев |

### Админ: Оценки и аналитика

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/admin/all-evaluations` | GET | Все оценки |
| `/api/admin/evaluation-details-by-user` | GET | Детали оценки по пользователю |
| `/api/admin/evaluations-matrix` | GET | Матрица оценок |
| `/api/admin/score-correction` | POST | Коррекция баллов |
| `/api/score-coefficients` | GET/POST | Коэффициенты оценок |
| `/api/analytics` | GET | Аналитика |

## 📝 Принципы кода

### Комментарии в файлах

Каждый файл начинается с JSDoc комментария:

```javascript
/**
 * [Название компонента/хука]
 * 
 * Назначение: [Что делает]
 * Используется в: [Где используется]
 * 
 * Props/Параметры:
 * - prop1: [тип] - [описание]
 */
```

### Паттерны

1. **Separation of Concerns** — логика в хуках, UI в компонентах
2. **Composition** — страницы компонуют мелкие компоненты
3. **DRY** — общие компоненты в `components/common/`
4. **Single Responsibility** — каждый файл < 300 строк

### Импорты

```javascript
// Из папки с index.js
import { Toast, LoadingSpinner } from '../components/common';
import { UserTable, UserFilters } from '../components/admin';

// Хуки
import { useUsers } from '../hooks/useUsers';

// API
import { API_ENDPOINTS } from '../config/api';
```

## 🎨 Стилизация

- **Tailwind CSS** — все стили через классы
- **Lucide React** — иконки
- **Цветовая схема:**
  - Primary: `indigo-600`
  - Success: `green-500/600`
  - Error: `red-500/600`
  - Warning: `amber/orange`
  - C-level: `purple-600`

## 🚀 Команды

```bash
npm install          # Установка зависимостей
npm run dev          # Запуск dev-сервера (localhost:5173)
npm run build        # Сборка для продакшена
npm run preview      # Превью билда
```

## ⚙️ Переменные окружения

Создайте файл `.env` в корне проекта (опционально):

```env
# API URL (n8n webhook base URL)
# По умолчанию: http://92.51.45.147:5678/webhook
VITE_API_URL=http://92.51.45.147:5678/webhook
```

Если переменная не задана, используется значение по умолчанию из `config/api.js`.

## 📊 Логика оценок

### Типы критериев

| Поле | Описание |
|------|----------|
| `selfassesment` | Доступен для самооценки |
| `for_manager` | Доступен менеджеру |
| `c_level_only` | Только для C-level/Admin |
| `target_audience` | Аудитория: all, project_participants, project, tender, managers_only |

### Типы источников оценки (evaluation_source)

| Значение | Описание |
|----------|----------|
| `manager` | Оценка от непосредственного руководителя |
| `subordinate` | Оценка от подчиненного (оценка менеджера подчиненными) |
| `self` | Самооценка |

### Расчет итогового балла

```javascript
const scores = Object.values(grades); // [8, 7, 9, ...]
const average = scores.reduce((a, b) => a + b, 0) / scores.length;
const finalScore = (average * gradeCoefficient).toFixed(2);
```

### Зоны оценок (для UI)

| Диапазон | Зона | Цвет |
|----------|------|------|
| 0-3 | Критический | red |
| 4-5 | Ниже ожиданий | amber |
| 6-7 | Соответствует | blue |
| 8-10 | Превосходит | green |

---

*Последнее обновление: Декабрь 2025*
