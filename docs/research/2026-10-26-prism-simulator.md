# PRISM (prismhld.com): разбор симулятора system design

Снимок сайта от 2026-10-26. Разбор через REA `capture_browser_scenario` (headless Chrome, desktop 1440 и mobile 390) и статический разбор публичных бандлов. Без логина: Simulate/Run/Submit, Interview, платные задачи не запускались. Пометки: **[O]** видел напрямую, **[I]** вывод, **[U]** неизвестно. Скриншоты лежали в scratchpad сессии и в репозиторий не кладутся (чужой UI).

## Кратко

- **Что это.** Тренажёр system design (HLD): рисуешь архитектуру на canvas, прогоняешь трафик (normal, spike, отказ компонента, stress ramp), получаешь score, findings и узкие места. Плюс AI-интервью и платные планы.
- **Стек.** Server-rendered HTML (Cloudflare перед Render), vanilla JS без фреймворка: canvas — это DOM + SVG, без React Flow. Three.js только в hero лендинга. **Симуляция считается на сервере.**
- **Главное:**
  1. 16 типов компонентов, у каждого `capacity` (rps на копию) и `base_latency`, плюс 5–10 параметров.
  2. 4 слоя обратной связи: live lint, Simulate, Run/Submit (10 test cases на задачу), Stress test (ramp 0.25×…5×, точка слома).
  3. 54 задачи, у каждой 5 стадий эволюции архитектуры; режим Design & Fix (инциденты); AI-интервью.
  4. Анимации пакетов по рёбрам в симуляторе **нет**: пульсации нод, плашка статуса, графики на inline-SVG. Стоимость не считается.

## 1. Доступ

- **Без аккаунта [O]:** редактор `/canvas/practice/<problem>` и `/canvas/learn/<problem>` (палитра, canvas, inspector, требования, test cases); Learn подгружает готовый пример (13 нод, 15 рёбер, 5 стадий); live lint `POST /api/validate`; каталог `GET /api/presets` и задача `GET /api/presets/<id>`.
- **За логином:** Simulate/Run/Submit (клиент показывает «Sign in to simulate your design»), Interview (редирект на `/login`), 26 из 54 задач, сохранение, шаринг, Design & Fix.
- **Бизнес-модель [O]:** free («Explorer»: 3 learn-пресета, 5 evaluate в месяц, 5 тем roadmap) → `pro_learner` и выше, оплата Razorpay.

## 2. Симулятор глазами пользователя

### 2.1 Режимы и экран

| Режим | Что это | Без логина |
|---|---|---|
| Learn → System Architectures | эталонная архитектура, 5 стадий эволюции (граф + разбор + learning goal) | да (3 на free) |
| Learn → Design & Fix | дана сломанная архитектура, найти root cause, починить граф, hints, debrief, звёзды [I] | нет |
| Practice → Interview Challenges | пустой canvas + условие, constraints, test cases, Simulate/Run/Submit | редактор да, запуск нет |
| Practice → Build & Stress Test | свободный canvas + вкладка Stress test | [U] |
| Interview → AI Interview | 4 раунда, таймер 60:00, вопросы, MCQ, tradeoff, рефлексия | нет |

**Раскладка desktop [O]:** три колонки.
- Слева «Building Blocks»: поиск, группы Entry & edge / Compute / Data / Async / External; ниже Inspector и Issues.
- Центр: canvas в точечную сетку, плавающий toolbar (undo/redo, zoom, fit, экспорт PNG/JSON, тип связи sync/async/bidirectional, удаление).
- Справа: панель задачи и результатов с табами.
- Сверху action bar: выбор задачи, **Simulate** (превью, не сохраняет), **Run** (3 сценария), **Submit** (полная батарея, сохраняется), секундомер.

### 2.2 Палитра: 16 типов [O]

| Тип (группа) | capacity / base ms | Ключевые параметры |
|---|---|---|
| User (Entry) | — | `number_of_users` 100, `requests_per_user` 1 |
| CDN (Entry) | 100000 / 4 | `cache_hit_ratio` 0.9, `ttl_seconds`, `cache_api_responses`, `ddos_protection`, `geo_routing` |
| Rate Limiter (Entry) | 50000 / 8 | `algorithm` token_bucket…, `window_seconds` 60, `max_tokens` 100, `scope` per_user, `burst_multiplier` 1.5 |
| Load Balancer (Entry) | 50000 / 20 | `replicas` 2, `algorithm` (round_robin, least_connections, weighted, ip_hash, least_response_time), `sticky_sessions`, `connection_draining` |
| API Gateway (Entry) | 20000 / 8 | `auth_enabled`, `rate_limiting`, `https_enabled`, `request_aggregation` |
| Reverse Proxy (Entry) | 30000 / 3 | `https_termination`, `compression`, `static_file_serving` |
| Server (Compute) | 1000 / 50 | `replicas`, `cpu_cores` 2, `autoscaling` + min/max, `timeout_ms` 3000; security: `auth_type`, `https_enabled`, `input_validation` |
| Service (Compute) | 1000 / 22 | `replicas`, `timeout_ms`, `circuit_breaker` (порог 5, восстановление 30 с), `retry_limit` 2, `retry_backoff`, `service_type` |
| WebSocket Server (Compute) | 10000 / 5 | `heartbeat_interval` 30, `replicas` |
| Worker (Compute) | 500 / 25 | `idempotent`, `replicas`, `concurrency` 4, `retry_limit` 3, `timeout_ms` 30000, `autoscaling` |
| Database (Data) | 2000 / 80 | `db_role`, `replicas`, `read_ratio` 80, `shards`, `sharding_strategy`, `connection_pool_size` 20, `max_concurrent_connections`, `replication_mode` async, `index_enabled` |
| Cache (Data) | 50000 / 5 | `hit_ratio` 0.8, `eviction_policy`, `max_memory_mb` 512, `ttl_seconds` 300, `request_coalescing`, `cluster_mode` |
| Search Index (Data) | 5000 / 12 | `replicas`, `shards`, `refresh_interval_sec`, `fuzzy_search` |
| Blob Storage (Data) | 5000 / 30 | `replication_factor` 3, `storage_class`, `versioning`, `cdn_integration` |
| Queue (Async) | 20000 / 30 | `max_queue_size` 10000, `delivery` at_least_once, `visibility_timeout_sec`, `dlq_enabled`, `ordering` |
| 3rd-party API (External) | 100 / 200 | `api_type` (payment, email, sms, ai_llm…), `timeout_ms` 5000, `circuit_breaker`, `retry_limit` 2, `cache_responses` |

Inspector делится на секции «Capacity & scaling / Reliability / поведение по типу / Security» и строится из декларативной схемы параметров (key, label, type, tooltip, unit, min, max, options).

**Модель ноды, которую получает сервер [O]:** `capacity_rps, degradation_slope, latency{base_ms, network_ms}, queue_limit (= 4 × capacity), resource_type (cpu|io|memory|network_bound), behavior{critical, type: sync|async}, retry{enabled, max_retries, backoff}, shards, replicas`.

### 2.3 Соединения [O]

- Тянешь от одного из 4 портов ноды к порту другой, snap 24 px. Двойной клик по палитре ставит ноду в центр.
- Ребро: `{source, target, connection_type: sync|async, direction: single|bidirectional, traffic_split_ratio, network_latency_ms, retry_probability, critical}`. Sync — сплошная синяя, async — фиолетовый пунктир. Ребро в Queue/Worker по умолчанию async.
- `traffic_split_ratio` не нормализован (сумма исходящих 1.38 в примере): это «вызовов по ребру на один входящий запрос», а не доля [I].

### 2.4 Что значит «запустить»

1. **Live lint** (без логина): debounce 450 мс на каждое изменение графа → `POST /api/validate`. Ответ: `structural_errors`, `architectural_violations`, `smells`, `findings[]` (`code, severity, title, reason, impact, recommendation`), `security{score, warnings}`, `score{total, grade, breakdown}`. Находки привязаны к нодам, кнопка «fix» открывает нужное поле inspector. Около 40 правил: `SINGLE_SERVER`, `SINGLE_DATABASE`, `MULTIPLE_SERVERS_NO_LB`, `NO_CACHE_READ_HEAVY`, `CACHE_AFTER_DB`, `QUEUE_NO_WORKER`, `WORKER_NOT_IDEMPOTENT`, `SYNC_TO_QUEUE`, `NOTIFICATION_IN_SYNC_PATH`, `DEEP_SYNC_CHAIN`, `HIGH_FANOUT_NODE`, `CYCLE_DETECTED`, `UNREACHABLE_NODE`, `NO_USER_NODE`, `NO_TERMINAL_STORAGE`, `DIRECT_STORAGE_EXPOSURE`, `COMPONENT_OVERLOADED`, `NEAR_SATURATION`, `NO_REPLICATION`, `SEC_*` и др.
2. **Simulate** (`POST /simulate`): ответ [I] `score`, `performance{total_latency, error_rate, throughput, capacity_headroom, bottleneck_*}`, `node_metrics[{incoming_rps, effective_capacity, utilization}]`, `findings`, `production_risks`.
3. **Run/Submit** (`POST /api/practice/evaluate`): результаты по сценариям, `overall{score, status}`, `component_load`, `overprovisioned`; порог прохождения сценария 60.
4. **Stress test** (`POST /api/stress-test`): ramp нагрузки, точка слома.

Сценарии [O]: `spike` умножает трафик на `traffic_multiplier` (по умолчанию 5); `failure` удаляет ноду и переподключает входящие рёбра к исходящим, выбирая по приоритету (Cache, SearchIndex, Queue, Worker, Service, Server, Database, LB). Отсюда объяснения вида «Your only Database went offline…».

### 2.5 Метрики и визуализация [O]

- **Canvas:** ноды «дышат» зелёным (healthy), пульсируют красным/янтарным на узком месте; плашка статуса «Simulating… → Stable / Under Load / Bottleneck Detected». Stress test красит ноды по utilization: < 0.7 зелёный, ≥ 0.7 тёплый, ≥ 0.9 горячий, > 1.0 красный.
- **Stress test:** вердикт «Holds at N rps / Breaks at about X rps, Nx your load, <component> gives out first»; плитки Served %, Latency, Retries/s, Dropped/s; SVG-график ошибок и latency по нагрузке 0.25×…5× проигрывается шагами по 340 мс, canvas перекрашивается синхронно; таблица компонентов (utilization, latency, retries, dropped, autoscaled to N); кривые capacity / spike timeline / failure до-после; share-ссылка и PDF.
- **Результаты Run/Submit:** Performance, ошибки и нарушения, рекомендации, Production Readiness, Core Concepts, Architecture Evolution, FAQ.

### 2.6 Задачи и scoring

- 54 задачи (URL shortener, Pastebin, rate limiter, news feed, WhatsApp, TikTok, ride sharing, платежи, RAG/LLM chat, distributed cache, job scheduler…), сложность easy/medium/hard.
- **Структура задачи [O]:** `problem_statement, constraints[], functional_requirements[], non_functional_requirements[], concepts[], design_notes, faqs[], scale{concurrent_users, peak_rps, latency_target_ms, regular_spike: 3, mega_spike: 10}, traffic_profile{users, requests_per_user}, stages[5], test_cases[10]`.
- **10 test cases:** 3 базовых (Normal ×1, Spike ×3, Component Failure) + 7 системных (Mega-spike ×10, Database Outage, Cache Down, Search Index Down, Notification Pipeline Down, LB Failure, Peak ×6 с давлением на БД). Поля: `scenario, traffic_multiplier, failure{prefer[], strategy}, tier, weight`.
- **Stages:** 5 снимков графа (3 → 13 нод) с разбором «что добавили, чего не хватало, почему рискованно, tradeoffs».
- Scoring: lint-score 0–100 со штрафами по severity, grade, security score, штраф за подсказки. AI-оценка за логином [U].

### 2.7 UX, который стоит повторить

1. Hover по блоку палитры показывает описание в inspector.
2. Live-проблемы на нодах с кнопкой «fix», ведущей к нужному полю.
3. Focus mode в Learn: всё кроме ноды и соседей затемняется, рядом текст о её роли.
4. «Why» на человеческом языке для каждого провала.
5. Три кнопки разной цены: Simulate / Run / Submit.
6. Пустое состояние подсказывает, с чего начать (пользователи, API, хранилища, трафик).
7. Undo/redo, copy/paste, текстовые аннотации, fit-to-screen, pinch/pan на touch, `prefers-reduced-motion`.

## 3. Как построено

- **Frontend [O]:** vanilla JS без сборки и minify (`canvas-core.js` 1.3 МБ), ноды — `div` с `position:absolute`, pan/zoom через CSS transform, рёбра — Bézier `<path>` в SVG. Состояние — один изменяемый объект, undo — снимок всего графа, события через `CustomEvent`. Графики вручную строками SVG. Web Worker, WASM, WebSocket в редакторе нет: на клиенте ничего не считается.
- **Backend [O/I]:** Cloudflare → Render, HTML из серверных шаблонов, язык бэкенда [U]. Rate limit через `x-ratelimit-*`.
- **API:**

| Метод и путь | Без токена | Назначение |
|---|---|---|
| `GET /api/presets`, `/api/presets/{id}` | да | каталог и задача |
| `POST /api/validate` | да | lint + score |
| `POST /simulate` | нет | полная симуляция |
| `POST /api/practice/evaluate` | нет | Run/Submit |
| `GET /api/stress-test/catalogue`, `POST /api/stress-test` | [U] | stress test |
| `POST /api/stress-report` | нет | share + PDF |
| `/api/workspaces` | нет | сохранённые схемы |
| `/api/design-fix/*`, `/api/evaluation-*` | нет | Design & Fix, AI-интервью |

### 3.1 Модель симуляции (реконструкция по подсказкам UI) [I]

| Подсказка в UI | Что значит для модели |
|---|---|
| Копии сервера делят одну очередь | M/M/c (Erlang-C), а не c независимых M/M/1 |
| Capacity указана для 2 ядер | `eff_capacity = capacity × replicas × cores / 2` |
| Autoscaling держит копии около 70% busy | target utilization 0.7 в пределах min/max |
| Throughput БД ≤ connections × 1000 / query time | Little's law для БД |
| Чтения по всем копиям, записи только в primary, шарды делят и то и другое | `read_ratio` разделяет поток |
| До хранилища доходят только промахи кэша | пропуск `1 − hit_ratio`; холодный старт кэша как сценарий |
| Больше ретраев — больше нагрузки на перегруженную зависимость | retry storm |
| Circuit breaker: быстрый отказ, без ретраев | breaker обнуляет ретраи |
| Медленнее timeout — ошибка | latency > timeout = отказ |
| Очередь дропает сверх `max_queue_size` | потеря при переполнении |

Отображаются детерминированные сводные числа и кривые: похоже на аналитическую (fluid) модель, а не на поштучную дискретно-событийную симуляцию [I].

## 4. Лендинг (коротко)

Server-rendered HTML, IntersectionObserver для появления секций, parallax на CSS-переменной, Three.js r169 в hero: 15-секундный цикл «нормальная нагрузка → spike 10× → БД насыщена → добавили кэш → всё здорово» с частицами-запросами. 3D только при ширине ≥ 1024 и без reduced-motion. Шрифты IBM Plex Sans/Mono и Inter, тёмная тема (`#0e1626`, акцент `#5cc8f2`, primary `#3b82f6`) и светлая. Мобильная версия симулятора: палитра и панель задачи становятся drawers, Simulate/Run/Submit сворачиваются в одну кнопку.

SEO стоит повторить: индексируемая страница на каждую задачу (sitemap на 133 URL), JSON-LD `TechArticle`. Не повторять: 1.3 МБ JS без code splitting и Three.js-hero ради маркетинга.

## 5. Как сделать такой же у нас (Next.js + FastAPI)

### Архитектура

- **web:** `app/simulator/[problem]/page.tsx` (SSR задачи для SEO) + клиентский Workspace: палитра | canvas на `@xyflow/react` (свои типы нод, порты, sync/async рёбра) | inspector из декларативной схемы параметров | панель результатов (вердикт, ramp-график, таблица компонентов). Состояние графа в store с undo/redo и localStorage.
- **api:** модули `problems` (каталог, test cases, стадии — файлы в git, как уроки), `simulator` (router/service/schemas/providers + чистый `engine/`: graph, lint, model, solver, scenarios), `designs` (сохранение и share-ссылки).
- **Эндпоинты:** `POST /api/simulator/analyze` (lint + статический score, быстрый, с debounce), `POST /api/simulator/run` (сценарии → вердикт и метрики по нодам), `GET /api/problems[/{id}]`, `/api/designs`.

### Где считать

На сервере (Python): один источник истины, скрытые test cases не утекают в браузер, fluid-модель считается за миллисекунды, тестируется pytest golden-кейсами. Движок в браузере (TS в Web Worker) — только если понадобится мгновенный отклик слайдеров.

### Модель v1 (детерминированная, fluid)

1. **Граф:** топологическая сортировка; структурные ошибки (нет User, циклы, недостижимые ноды, нет хранилища) блокируют прогон.
2. **Поток:** `λ0 = users × requests_per_user`; по ребру `λ_v += λ_u_served × ratio`; кэш и CDN пропускают `1 − hit_ratio`; rate limiter срезает до лимита; БД делит поток по `read_ratio`; async-рёбра грузят очередь и worker, но не входят в пользовательскую latency.
3. **Ёмкость:** `μ = capacity × copies × cores / 2`; при autoscaling `copies = ceil(λ / (0.7 × capacity))` в пределах min/max.
4. **Очередь и latency:** `ρ = λ / μ`; v1: `latency = base × (1 + ρ² / (1 − ρ))` до ρ < 0.95, дальше кусочно-линейно до `queue_limit`; при ρ ≥ 1 обслуживается `μ`, остальное дропается.
5. **Ретраи и timeouts:** несколько итераций до сходимости, `λ_in = λ_base × (1 + p_fail × retry_limit)`; breaker обнуляет добавку.
6. **Сквозные метрики:** latency по критическому sync-пути, доля ошибок, первая сломавшаяся нода (max ρ), headroom `λ_break / λ0`.
7. **Сценарии:** spike = `λ0 × k`; failure = удалить ноду (или копию) с bypass; ramp 0.25…5× и бисекция точки слома.
8. **Heat:** < 0.7 / ≥ 0.7 / ≥ 0.9 / > 1.0.
9. **Объяснения:** шаблоны из тех же чисел («отброшено N% запросов, X получает a rps при ёмкости b»).

Поштучную симуляцию (SimPy) и анимацию пакетов по рёбрам откладываем: у PRISM их нет, а ценность («где сломается») даёт fluid-модель.

### Компоненты

- **MVP (9):** User, CDN, Load Balancer, Server (replicas, cores), Cache (hit_ratio), Database (replicas, read_ratio, shards), Queue, Worker, Rate Limiter; рёбра sync/async с ratio.
- **Потом:** Service (breaker, retries, timeouts), autoscaling, API Gateway, Reverse Proxy, 3rd-party API, Search Index, Blob Storage, WebSocket.
- **Позже:** security-правила, replication lag, стадии эволюции, Design & Fix, AI-разбор (у нас уже есть движок оценщика), стоимость (у PRISM её нет).

### Оценка (один сильный full-stack, грубо)

| Блок | Срок |
|---|---|
| Canvas, палитра, рёбра, inspector, undo, сохранение (React Flow) | 1–1.5 нед |
| Движок v1 + golden-тесты | 2–2.5 нед |
| Lint-правила (~20) | 1 нед |
| UI результатов | 1 нед |
| Каталог задач + SSR/SEO | 1 нед + контент |
| Сохранение схем, share, лимиты | 1 нед |
| Стадии/Learn, Design & Fix, AI-разбор | 3–4 нед |
| Mobile и полировка | 1 нед |

MVP «нарисуй, прогони 3 сценария, получи вердикт и проблемы»: ~6–8 недель. Уровень PRISM: 3–5 месяцев.

## 6. Пробелы

1. Серверный движок не наблюдался: формулы в 3.1 — реконструкция по подсказкам UI, их нужно проверить своими тестами на реалистичных графах.
2. AI-интервью, платные задачи и Design & Fix видны только по клиентскому коду.
3. Язык бэкенда неизвестен.
4. Roadmap и гайды разобраны поверхностно.

Копируем механику и идеи, но не тексты задач, правила дословно, бренд и ассеты PRISM.
