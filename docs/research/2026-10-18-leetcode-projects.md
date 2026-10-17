# Ресерч: LeetCode Projects (`leetcode.com/project/`)

**Дата:** 18 октября 2026
**Зачем:** референс для подпроекта «Редактор и запуск кода» и практики к модулям «Бэкенд», «Highload», «AI engineering».
**Как собрано:** REA 6.5.0 (`inspect-web-page`, `capture-browser-scenario`, `analyze-web-bundle`) через CDP к залогиненной сессии в Chrome. Пассивный захват каталога и детальной панели, тексты GraphQL-операций и enum'ы из JS-бандлов. Контент и код LeetCode не копируем, берём только механику.

Пометки: **[видел]** — наблюдал в ответах API или UI, **[вывод]** — следует из названий полей и enum'ов, но не проверено, **[не видел]** — открытый вопрос.

## Что это

Раздел «From Coding to Building. Build real-world skills through projects.» Вместо алгоритмических задач здесь практические мини-сервисы на 45–75 минут. Решение пишется в облачной песочнице с таймером, проверяется скрытыми тестами и AI-ревью по разделам. На 18.10.2026 в каталоге 15 проектов, все бесплатные (`paidOnly: false`). **[видел]**

## Модель задачи

Одна сущность, два запроса: `projectProblemList(skip, limit: 200)` для каталога, `projectProblemDetail(problemSlug)` для панели. **[видел]**

| Поле | Пример | Смысл |
|---|---|---|
| `slug`, `title` | `rate-limiter` | |
| `summary` | одна строка | текст карточки |
| `difficulty` | `INTERMEDIATE` / `ADVANCED` / `EXPERT` | в UI Easy / Medium / Hard |
| `estimatedSolvingMin` | 45, 60, 75 | оценка на карточке |
| `practiceMaxMinutes` | 45 | жёсткий таймер сессии |
| `topicTags[]` | `{name, nameTranslated}` | 3–8 тегов |
| `problemType` | `STANDARD` / `AI_COLLABORATION` | для STANDARD в панели «AI agent: Not allowed» |
| `runtimes[]` | `python-3.11`, `java-21` | выбор языка перед стартом |
| `languages[]` | `[]` | пусто, вместо него `runtimes` |
| `description` | markdown | см. шаблон ниже |
| `companyTags[]`, `interviewFrequency` | закрыто Premium | краудсорс через опрос |
| `attempted`, `paidOnly`, `iconUrl` | | |

### Шаблон описания [видел на rate-limiter]

```
### Background                — контекст: какой продукт, какая боль
### Task                      — что реализовать, 1 абзац
### What This Problem Tests   — 5–7 пунктов: проверяемые навыки
```

### Архетипы задач (по глаголу в summary)

- **Build** — сервис с нуля: Rate Limiter, URL Shortener, Feature Flag, File Deduplication, Image Transform Pipeline, Retry-Safe Issue Service.
- **Repair** — готовый сервис с багами: Loan Lifecycle, Comment Moderation, Movie Recommendation, Persistent Watchlists, Password Reset, Return Risk.
- **Investigate & fix** — инцидент плюс безопасная починка прод-данных: Reservation Service Incident.
- **Extend** — доработка существующей системы: Comments & Replies.

У всех Repair-задач и у инцидента стоит тег `AI Coding`. **[вывод]** Это и есть `AI_COLLABORATION`, где агент разрешён.

## Темы

37 тегов на 15 проектов. Список в фильтре Topics строится на клиенте как объединение тегов загруженных проектов. **[видел]**

| Тег | Проектов |
|---|---|
| Concurrency | 10 |
| AI Coding, Debugging | 7 |
| Database, State Management, Input Validation | 4 |
| Backend, System Design | 3 |
| API Design, Full Stack, REST API, Hashing, Memory Management, Authorization, Data Persistence | 2 |
| Infrastructure, File I/O, Locking, Deterministic Assignment, HTTP API, Task Scheduling, Lazy Iteration, Data Modeling, Boundary Conditions, Batch Processing, Stateless Design, Data Isolation, Idempotency, Versioning, Pagination, Recommender Systems, Sorting, Data Processing, Transactions, CRUD, Configuration Management, Datetime Handling | 1 |

Почти везде повторяются конкурентность, детерминизм, валидация и граничные случаи. Алгоритмов почти нет.

## Каталог проектов

| slug | Сложность | Мин | Теги |
|---|---|---|---|
| rate-limiter | INTERMEDIATE | 45 | API Design, Backend, Concurrency, Infrastructure, System Design |
| comments-replies | INTERMEDIATE | 45 | Backend, Database, System Design, Full Stack, REST API |
| url-shortener | ADVANCED | 60 | Backend, Database, System Design, Full Stack, REST API |
| reservation-service | ADVANCED | 60 | AI Coding, Debugging, Concurrency, Database |
| file-deduplication | ADVANCED | 60 | File I/O, Hashing, Memory Management, Concurrency |
| feature-flag | ADVANCED | 60 | Hashing, Locking, Deterministic Assignment, Concurrency, HTTP API |
| image-transform-pipeline | ADVANCED | 45 | Concurrency, Task Scheduling, Memory Management, Lazy Iteration |
| loan-management | ADVANCED | 60 | AI Coding, Debugging, Concurrency, State Management, Data Modeling |
| return-fraud-risk | INTERMEDIATE | 45 | AI Coding, Debugging, Input Validation, Boundary Conditions, Batch Processing, Stateless Design, Data Isolation |
| review-moderation | ADVANCED | 60 | AI Coding, Debugging, Input Validation, State Management, Concurrency |
| issue-creation-api | EXPERT | 75 | API Design, Idempotency, Concurrency, Authorization, Versioning, Pagination |
| movie-recommendations | ADVANCED | 60 | AI Coding, Debugging, Recommender Systems, Sorting, Data Processing, Input Validation |
| keyword-user-blocklists | ADVANCED | 60 | Input Validation, State Management, Concurrency |
| movie-watchlists | ADVANCED | 60 | AI Coding, Debugging, Transactions, Data Persistence, Authorization, Concurrency, Database, CRUD |
| password-reset | INTERMEDIATE | 45 | AI Coding, Debugging, Configuration Management, Datetime Handling, State Management, Data Persistence |

## Как работает

1. **Каталог.** Один запрос на 200 проектов. Фильтры Difficulty, Status, Topics и Sort работают на клиенте: при их открытии новых запросов не было. `projectQuickStartProblem` подсказывает, с чего начать (`rate-limiter`). **[видел]**
2. **Панель задачи.** Модалка открывается по `?detail=<slug>`, ссылкой на неё можно поделиться. Одновременно грузятся `projectProblemDetail`, `projectPracticeQuota`, `projectPracticeSession`, `projectSubmissionList`. **[видел]**
3. **Квота.** `{limit: 2, used, remaining, resetAt: полночь UTC}` на проект в день для free-аккаунта. **[видел]**
4. **Старт.** `startProjectPractice(problemSlug, runtimeKey)` возвращает `{ok, error, errorCode, quota, session, sandboxStatus}`. **[видел в бандле]**
   - Сессия: `PREPARING → ACTIVE → SUBMITTING → ENDED`, поля `readyAt, startedAt, expiresAt, endedAt, endReason, submissionId`.
   - Таймер считает сервер (`remainingSeconds`, `serverNow`).
   - Коды ошибок: `QUOTA_EXHAUSTED`, `OTHER_SESSION_ACTIVE`, `OTHER_RUNTIME_ACTIVE`, `RUNTIME_NOT_OFFERED`, `SANDBOX_UNAVAILABLE`, `SANDBOX_ERROR`, `SESSION_EXPIRED`, `SESSION_NOT_READY`, `SUBMISSION_IN_PROGRESS`, `PREMIUM_REQUIRED`, `PRACTICE_DISABLED`.
   - Одновременно активна только одна сессия.
5. **Песочница.** `createOrGetUserSandbox` и `sandboxStatus` отдают `{status, ready, url, authToken, warmupUrl, repoTag, needsRebuild, resetReason: MANUAL | REPO_UPDATE, backupDirName}`. Восстановление IDE: `IDE_RELOADED`, `RECONNECTED`, `NOT_RECOVERED`. **[видел в бандле]** **[вывод]** У каждого пользователя своё окружение на проект: удалённая IDE по `url`, вход по `authToken`, стартовый код из git-репозитория версии `repoTag`, при сбросе делается бэкап.
6. **Завершение.** `endProjectPractice(problemSlug)`. **[видел в бандле]**
7. **Оценка сабмита.** Стадии: `QUEUED → PREPARING_SNAPSHOT → LAUNCHING_TEST → WAITING_TEST → EXPORTING_SESSIONS → PREPARING_ANALYSIS → STREAMING_ANALYSIS → GENERATING_REPORT → SUCCEEDED | FAILED`. **[видел в бандле]**
   - Результат: `summary.tests {status, passed, total}`, `aiStatus`, `aiSkipReason`, `ratings[{section, rating}]`, `useAi`, `forced`, `reportAvailable`. Отчёт с оглавлением по разделам.
   - **[вывод]** Снимок кода → скрытые тесты → выгрузка сессий AI-агента → потоковый LLM-анализ → отчёт. `forced` означает автосабмит по истечении таймера.
8. **Опрос «встречал на интервью?».** `postProjectInterviewVote(company, position, stage, time, country)` питает `interviewFrequency` и `companyTags`. **[видел в бандле]**

## Рабочее пространство (IDE)

**[не видел]** Заполню после прохода по Practice: структура IDE, файлы стартового репозитория, как запускаются тесты, как выглядит AI-агент.

## Что взять в devplus

- Шаблон задачи-проекта: Background / Task / What This Tests + стартовый репозиторий + скрытые тесты + рубрика AI-ревью по разделам. Хорошо ложится на модули «Бэкенд», «Highload», «AI engineering».
- Три архетипа (Build / Repair / Incident) дают разную практику на одном механизме. Repair и Incident ближе к реальной работе и к работе с AI-агентом.
- Таймер, квоты и одна активная сессия нужны LeetCode из-за дорогих облачных песочниц. Для командной платформы в первой версии это лишнее.
- Самое дорогое — облачная IDE. Дешёвая первая версия: склонировал стартовый репозиторий, сдал код, worker прогнал скрытые тесты и AI-ревью. Это совпадает с планом на Redis и worker в оценщике промптов.

Решение по скоупу принимаем на брейнсторме подпроекта «Редактор и запуск кода».
