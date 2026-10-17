# Ресерч: LeetCode Projects (`leetcode.com/project/`)

**Дата:** 18 октября 2026
**Зачем:** референс для подпроекта «Редактор и запуск кода» и практики к модулям «Бэкенд», «Highload», «AI engineering».
**Как собрано:** REA 6.5.0 (`inspect-web-page`, `capture-browser-scenario`, `analyze-web-bundle`) через CDP к залогиненной сессии в Chrome. Пассивный захват каталога и детальной панели, тексты GraphQL-операций и enum'ы из JS-бандлов. IDE живёт в кросс-доменном iframe, куда REA не заходит, поэтому её читали через Playwright в той же вкладке: дерево доступности и read-only команды в терминале песочницы. Контент и код LeetCode не копируем, берём только механику.

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

У всех Repair-задач и у инцидента стоит тег `AI Coding`. У `password-reset` **[видел]** `problemType: AI_COLLABORATION`, и в IDE есть агент. У `rate-limiter` (`STANDARD`) указано «AI agent: Not allowed». **[вывод]** Тег `AI Coding` соответствует `AI_COLLABORATION`.

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

Снято на `password-reset` (Python 3.11, `AI_COLLABORATION`) в живой practice-сессии. **[видел]**

### Запуск

- Practice открывает диалог подтверждения: «тратит одну из сегодняшних попыток, максимум 45 минут, таймер стартует, когда песочница готова, без паузы, язык потом не сменить». Кнопки «Start practice» и «Not now».
- Через ~15 секунд страница переходит на `/project/<slug>/`: шапка LeetCode (Run, Submit, таймер, End this run, Feedback) и IDE в iframe с `https://<id>.sandbox.leetpad.com/?token=…`.
- Песочница открывается только встроенной в страницу: та же ссылка в отдельной вкладке отдаёт `Forbidden`.

### Окружение

- IDE — **Eclipse Theia** (в домашней папке лежит сборка Theia IDE, тесты описаны в `.theia/tasks.json`).
- Под в **Kubernetes**, 4 CPU, пользователь `LeetCode`, проект в `/home/project/<slug>`, заранее готовый `venv`.
- Панели: Explorer, Search, API Request (HTTP-клиент), терминал (Ports, Task: Setup, bash), Outline, Changes (git-дифф от стартовой версии).
- **AI-агент: OpenCode с UI OpenChamber**, панель «OpenChamber: Chat» справа. Есть шаблоны «Explore the codebase», «Catch me up», «Weigh my options», «Start feature planning», «Debug an issue», «Review my changes». Ввод «Use @ / ! # for helpers», текущий файл прикрепляется к контексту автоматически.
- По именам переменных окружения (значения не смотрели): `OPENCODE_*` (в том числе `OPENCODE_DISABLE_CLAUDE_CODE`, `OPENCODE_DISABLE_PROJECT_CONFIG`), `SANDBOX_GATEWAY_BASE_URL` и `SANDBOX_GATEWAY_API_KEY`. **[вывод]** Агент ходит к LLM через их шлюз, поэтому сессии агента можно выгрузить на оценку (`EXPORTING_SESSIONS`).
- Модель агента **[не видел]**: конфиг не читали, он рядом с ключами шлюза.

### Стартовый репозиторий (181 строка)

| Файл | Права | Роль |
|---|---|---|
| `README.md` | read-only | полная спецификация (ниже) |
| `auth_service.py` | редактируемый | сервис с заложенными багами (31 строка) |
| `REFLECTION.essay` | редактируемый | 3 вопроса на рассуждение |
| `database.py` | read-only | фиксированная граница хранилища, in-memory mock |
| `test_client.py` | read-only | 4 публичных smoke-теста на `unittest` |
| `test_support.py` | read-only | фикстуры и управляемые часы (`clock`) |
| `requirements.txt` | read-only | `pytest`, `pytest-timeout` |
| `validation/` | пустая | **[вывод]** сюда при сабмите подкладываются скрытые тесты (pytest + timeout) |
| `.theia/run_tests.sh`, `.theia/tasks.json` | read-only | задача «Run Tests» → `python3 -B test_client.py` |

Фиксированные файлы принадлежат root и в Explorer помечены замком.

### Шаблон README (это и есть задача)

1. **What you should know** — режим (`Mode: Debugging`) и нужные знания.
2. **Scenario** — жалобы пользователей, что починить и в каком файле.
3. **Files** — что можно править (сервис, эссе, свои хелперы и регрессионные тесты), что нельзя.
4. **Public API** — сигнатуры класса, контракт инъекции `clock`.
5. **Requirements** — 6 пронумерованных разделов с точными граничными условиями (например, `0 <= age < 30`, где 30 уже просрочено; наивный timestamp считается UTC; повторное использование кода через другой инстанс должно отклоняться).
6. **Implementation checklist** — 5 пунктов, все обязательные.
7. **Estimated completion time** и **Running locally**. Прямо сказано, что стартовый код намеренно падает, а публичные тесты покрывают только часть требований.

### Планирование багов

В стартовом `auth_service.py` по одному багу на требование: подмена URL при чтении env, фиксированный код `"123456"`, наивный `datetime.now` вместо UTC, отсутствие сохранения пароля и сброса кода. Каждый публичный тест ловит ровно один баг, его docstring сформулирован как требование: «A code older than the validity window cannot change a password».

### REFLECTION.essay

JSON `{version, questions: [{id, title, prompt: {en, zh-cn}, answer}]}`. Theia показывает его кастомным редактором-формой с полем ответа на каждый вопрос. Вопросы касаются того, что сознательно вынесено за рамки реализации: атомарность при конкурентной проверке, что поменять перед продом (генерация и хранение кодов, хеширование), лимит попыток и надёжная экспирация при нескольких инстансах. **[вывод]** Ответы оценивает AI-ревью, отсюда `ratings[{section}]`.

## Что взять в devplus

- Шаблон задачи-проекта: Background / Task / What This Tests + стартовый репозиторий + скрытые тесты + рубрика AI-ревью по разделам. Хорошо ложится на модули «Бэкенд», «Highload», «AI engineering».
- Анатомия стартового репозитория дёшево копируется и без облачной IDE: README-спецификация с точными граничными условиями, один редактируемый файл, фиксированная граница хранилища и инъекция часов, публичные smoke-тесты (по одному на баг) плюс скрытые тесты, `REFLECTION` с вопросами про то, что вынесено за скоуп.
- Три архетипа (Build / Repair / Incident) дают разную практику на одном механизме. Repair и Incident ближе к реальной работе и к работе с AI-агентом.
- Таймер, квоты и одна активная сессия нужны LeetCode из-за дорогих облачных песочниц. Для командной платформы в первой версии это лишнее.
- Самое дорогое — облачная IDE. Дешёвая первая версия: склонировал стартовый репозиторий, сдал код, worker прогнал скрытые тесты и AI-ревью. Это совпадает с планом на Redis и worker в оценщике промптов.

Решение по скоупу принимаем на брейнсторме подпроекта «Редактор и запуск кода».
