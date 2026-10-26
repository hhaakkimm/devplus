# Симулятор system design: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Тренажёр system design: схема из компонентов на canvas, прогон сценариев нагрузки и отказов на сервере, правила архитектуры и AI-разбор, зачёт по задачам модуля 10.

**Architecture:** Новый модуль `apps/api/app/modules/simulator/`. Внутри чистый движок `engine/`, загрузчик задач из `content/` и попытки в Postgres. AI-разбор идёт через судью оценщика (`evals.service`). Веб: `/simulator` и рабочее место на `@xyflow/react`; черновик хранится в `localStorage`.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, dishka; Next.js App Router, TypeScript, Tailwind, shadcn/ui, `@xyflow/react` 12; pytest, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-devplus-simulator-design.md`

**Старт:** после слияния ветки оценщика (`feat/evaluator`) в `main`. План опирается на его модули `evals`, `trainer`, `FakeLLMClient`, `useAction`, `lib/content.ts`.

## Global Constraints

- **Типы узлов:** `User`, `CDN`, `RateLimiter`, `LoadBalancer`, `Server`, `Cache`, `Database`, `Queue`, `Worker`.
- **Ёмкость на копию, rps / задержка, мс:**

  | Тип | Ёмкость | Задержка |
  |---|---|---|
  | CDN | 100 000 | 5 |
  | RateLimiter | 50 000 | 2 |
  | LoadBalancer | 50 000 | 2 |
  | Server | 1 000 | 30 |
  | Cache | 50 000 | 2 |
  | Database | 2 000 | 20 |
  | Queue | 20 000 | 5 |
  | Worker | 500 | 50 |

  У User ёмкости нет.
- **Параметры (пределы, по умолчанию):**
  - CDN: `hit_ratio` 0–0.99 (0.8);
  - RateLimiter: `limit_rps` 1–10 000 000 (1000);
  - LoadBalancer: `replicas` 1–100 (1);
  - Server: `replicas` 1–100 (1);
  - Cache: `hit_ratio` 0–0.99 (0.8), `replicas` 1–100 (1);
  - Database: `read_replicas` 0–100 (0), `shards` 1–100 (1);
  - Queue: `max_size` 1–10 000 000 (100 000);
  - Worker: `replicas` 1–100 (1).
- **Ребро:** `kind` `sync`/`async` (по умолчанию `sync`), `ratio` 0–10 (по умолчанию 1). Рёбра в Queue и Worker всегда `async`: сервер приводит их к `async` при разборе графа.
- **Пределы графа:** до 50 узлов и 100 рёбер. `id` узла — `^[A-Za-z0-9_-]{1,40}$`. Координаты `x`, `y` хранятся для canvas, движок их не читает.
- **Задержка узла:** `base / (1 − min(ρ, 0.95))`. В UI она подписана «средняя задержка».
- **Окраска по `ρ`:** < 0.7 зелёный, < 0.9 жёлтый, < 1 оранжевый, ≥ 1 красный.
- **Ответы студента:** `requirements` («Требования и допущения»), `estimates` («Оценка нагрузки»), `tradeoffs` («Ключевые решения и компромиссы»). Каждый до 5 000 символов, без NUL.
- **AI-разбор:** судья оценщика, модель `claude-sonnet-5-5`, effort `medium`, лимит оценки стоимости $0.10 на попытку.
- **Отправки:** не больше 20 за последние 24 часа на пользователя без `review_error`. Сверх лимита — 429 «Лимит отправок на сегодня исчерпан».
- **Тексты ошибок:**
  - 422 «Схема не прогоняется: …» при структурных ошибках на отправке;
  - 400 «Ожидаемая стоимость разбора $X выше лимита $0.10»;
  - `review_error` при сбое: «AI-разбор не удался: Claude API недоступен», «AI-разбор не удался: <ошибка судьи>».
- **Скрытое:** `review` (рубрика, порог, `reference`) и `reference_graph` не уходят в браузер никогда. Параметры и цели скрытых сценариев не уходят до отправки. После отправки уходят только `id`, `title`, `passed`, `explanation`, и объяснение скрытого сценария не называет цели.
- **Импорты:** `simulator` берёт из оценщика только `app.modules.evals.service`. Нужен контракт import-linter.
- **UI:** только русский. Кнопки, которые шлют запрос, заблокированы на время запроса (`useAction`).
- **Коммиты:** без `Co-Authored-By` и без упоминаний Claude/AI. После изменения API — `make gen-client` и коммит клиента.

## Review Focus

1. **Черновик в `localStorage` от старой версии каталога или испорченный.** Ожидание: черновик сбрасывается с сообщением «Черновик устарел и сброшен», рабочее место открывается. Тест в Task 8.
2. **Сценарий отказа указывает тип, которого нет в схеме студента** (например, «Отказ кэша» без Cache). Ожидание: сценарий считается без отказа с теми же целями, без исключения. Тест в Task 3.
3. **Вырожденные потоки:** ребро с `ratio: 0`, `hit_ratio: 0.99`, узел с `λ = 0`. Ожидание: все числа конечны, у узла с `λ = 0` доля успеха 1 и задержка `base`. Тест в Task 2.
4. **Узел без рёбер рядом с рабочей схемой.** Ожидание: не структурная ошибка, а предупреждение `ISOLATED_NODE`, расчёт идёт без него. Тесты в Task 1 и Task 4.
5. **Двойная отправка** (двойной клик, две вкладки). Ожидание: кнопка заблокирована на время запроса. Гонка суточного лимита между двумя одновременными запросами допустима и помечена `shortcut:`. Тест `toBeDisabled()` в Task 9.

---

## Структура файлов

```
apps/api/app/modules/simulator/
  __init__.py
  engine/__init__.py
  engine/catalog.py     NodeType, Param, ComponentSpec, CATALOG, check_params()
  engine/graph.py       Node, Edge, Graph, structural_errors(), topo_order(), active_nodes()
  engine/solver.py      NodeMetrics, Flow, EngineError, solve()
  engine/scenarios.py   Failure, Scenario, ScenarioResult, apply_failure(), run_scenario()
  engine/lint.py        Finding, lint()
  tasks.py              Scale, ReviewSpec, SimTask, SimTaskFileError, load_sim_tasks(), cached_sim_tasks()
  review.py             graph_text(), review_request(), estimate_review(), review_attempt()
  models.py             SimAttempt
  schemas.py            *In / *Out
  service.py            SimulatorService
  providers.py          SimulatorProvider
  router.py
apps/api/migrations/versions/<rev>_sim_attempts.py
apps/api/tests/test_sim_*.py
content/10-system-design/_module.json
content/10-system-design/simulator/0{1,2,3}-<slug>.{mdx,yaml}
apps/web/app/(app)/simulator/page.tsx
apps/web/app/(app)/simulator/[module]/[task]/page.tsx
apps/web/components/simulator/*.tsx
apps/web/lib/simulator.ts   преобразование граф ↔ API, черновик, окраска
apps/web/test/simulator.test.ts, apps/web/e2e/simulator.spec.ts
```

---

### Task 1: Каталог компонентов и граф

**Files:**
- Create: `apps/api/app/modules/simulator/__init__.py`, `engine/__init__.py`, `engine/catalog.py`, `engine/graph.py`
- Test: `apps/api/tests/test_sim_graph.py`

**Interfaces:**
- Produces:
  - `NodeType = Literal["User","CDN","RateLimiter","LoadBalancer","Server","Cache","Database","Queue","Worker"]`.
  - `@dataclass(frozen=True) Param(key: str, label: str, kind: Literal["int","float"], min: float, max: float, default: float, help: str)`.
  - `@dataclass(frozen=True) ComponentSpec(type: NodeType, label: str, description: str, capacity_rps: int | None, latency_ms: float | None, params: tuple[Param, ...], terminal_ok: bool)`. `terminal_ok` равен True у Database, Cache, CDN, Worker.
  - `CATALOG: dict[NodeType, ComponentSpec]`.
  - `check_params(type: NodeType, params: dict[str, float]) -> dict[str, float]`: дополняет значения по умолчанию; неизвестный ключ, выход за предел или нецелое для `int` дают `ValueError` с русским текстом.
  - Pydantic-модели:
    - `Node(id, type: NodeType, params: dict[str, float] = {}, x: float = 0, y: float = 0)` с валидатором через `check_params`;
    - `Edge(source: str, target: str, kind: Literal["sync","async"] = "sync", ratio: float = Field(1, ge=0, le=10))`;
    - `Graph(nodes: list[Node] = Field(max_length=50), edges: list[Edge] = Field(max_length=100))`. Модель-валидатор проверяет уникальность `id` и существование концов рёбер (иначе `ValueError`) и приводит рёбра в Queue/Worker к `async`.
  - `structural_errors(g: Graph) -> list[str]`, тексты дословно:
    - «Нужен ровно один узел User»;
    - «Схема содержит цикл»;
    - «Узел {id} недостижим от User»;
    - «Запросы из узла {id} уходят в никуда: добавь хранилище или обработчик».
  - `active_nodes(g: Graph) -> list[str]`: узлы, у которых есть хоть одно ребро, плюс User.
  - `topo_order(g: Graph) -> list[str]` по активным узлам; вызывается только для графа без структурных ошибок.

- [ ] **Step 1: Написать падающие тесты.**

```python
def node(id, type, **params): return Node(id=id, type=type, params=params)

def test_catalog_values_match_spec():
    assert CATALOG["Server"].capacity_rps == 1000 and CATALOG["Server"].latency_ms == 30
    assert CATALOG["Database"].capacity_rps == 2000 and CATALOG["Queue"].capacity_rps == 20000
    assert CATALOG["User"].capacity_rps is None

def test_params_defaults_and_limits():
    assert check_params("Cache", {}) == {"hit_ratio": 0.8, "replicas": 1}
    with pytest.raises(ValueError): check_params("Server", {"replicas": 0})
    with pytest.raises(ValueError): check_params("Server", {"replicas": 1.5})
    with pytest.raises(ValueError): check_params("Server", {"cores": 2})

def test_graph_rejects_dangling_edge_and_duplicate_ids(): ...      # ValidationError
def test_edges_into_queue_and_worker_become_async(): ...
def test_structural_errors_texts(): ...  # 0 User, 2 User, cycle, unreachable-with-edges, Server leaf
def test_isolated_node_is_not_structural_error():
    g = Graph(nodes=[node("u","User"), node("s","Server"), node("d","Database"), node("c","Cache")],
              edges=[Edge(source="u", target="s"), Edge(source="s", target="d")])
    assert structural_errors(g) == [] and "c" not in active_nodes(g)
def test_graph_size_limits(): ...        # 51 nodes / 101 edges -> ValidationError
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.** `cd apps/api && uv run pytest tests/test_sim_graph.py -q`: ожидается ImportError.
- [ ] **Step 3: Реализовать** `catalog.py` и `graph.py`. `description` и `help` пишутся по-русски, коротко. Например, Server: «Код приложения. Каждая копия держит 1 000 rps.»
- [ ] **Step 4: Прогнать тесты и `make lint-api`.** Ожидается PASS и чистый вывод.
- [ ] **Step 5: Commit** `feat(simulator): component catalog and graph model`

---

### Task 2: Расчёт потоков

**Files:**
- Create: `engine/solver.py`
- Test: `apps/api/tests/test_sim_solver.py`

**Interfaces:**
- Consumes: `Graph`, `CATALOG`, `topo_order`, `active_nodes`.
- Produces:
  - `class EngineError(Exception)`.
  - `@dataclass(frozen=True) NodeMetrics(id: str, type: NodeType, rps: float, capacity_rps: float | None, rho: float, latency_ms: float, errors_rps: float, rejected_rps: float, backlog: float, message_loss: float)`.
  - `@dataclass(frozen=True) Flow(nodes: dict[str, NodeMetrics], latency_ms: float, error_rate: float, rejected_rate: float, message_loss: float)`.
  - `solve(g: Graph, rps: float, read_ratio: float, duration_s: float, down: frozenset[str] = frozenset()) -> Flow`. `down` — терминальные узлы, которые в отказе: обслуживают 0.

**Алгоритм** (спека, раздел 3). Один проход по `topo_order`, поток узла — пара `(reads, writes)`:
- User порождает `(rps × read_ratio, rps × (1 − read_ratio))`.
- Доля обслуженного `f = min(1, μ / λ)` (при `λ = 0` она равна 1). `μ = capacity × replicas`, у CDN, RateLimiter и Queue копия одна.
- RateLimiter сначала обрезает поток до `limit_rps` пропорционально чтениям и записям, обрезанное идёт в `rejected_rps`. Потом применяется его ёмкость.
- CDN и Cache отвечают сами на `reads × hit_ratio` (доля `h` от их λ) и передают дальше `(reads × (1 − hit), writes) × f`.
- Database: копий на шард `1 + read_replicas`.
  - `λ_primary = (writes + reads / копий) / shards`, `λ_replica = (reads / копий) / shards`, `ρ = max(ρ_primary, ρ_replica)`.
  - Обслуженное считается по отдельности для primary и реплик.
  - Узел из `down` обслуживает 0.
- Queue и Worker. Если Worker получает поток из Queue, то Worker обслуживает `min(λ, μ)`, а лишнее не ошибка, а `backlog = (λ − μ) × duration_s` и `message_loss = max(0, backlog − max_size) / (λ × duration_s)` у этой Queue. Worker без Queue считается как Server.
- Дети получают `обслуженный_выход × ratio` по каждому ребру.
- `latency(v) = base / (1 − min(ρ, 0.95))`.
- `L(v) = latency(v) + (1 − h) × Σ_sync ratio × L(child)`; у User `latency = 0`.
- `s(v) = f × (h + (1 − h) × Π_sync (1 − min(1, ratio × (1 − s(child)))))`, где у RateLimiter `f` включает обрезку.
- `error_rate = 1 − s(User)`, `rejected_rate = Σ rejected_rps / rps`, `message_loss = max` по очередям.
- Любое NaN или inf в результате даёт `EngineError`.

- [ ] **Step 1: Написать падающие golden-тесты** (`pytest.approx(..., rel=1e-3)`).

```python
def test_overloaded_server():
    # User→Server(1)→Database; 1500 rps, read 0.9
    f = solve(chain("Server", "Database"), 1500, 0.9, 60)
    assert f.nodes["server"].rho == approx(1.5) and f.nodes["server"].latency_ms == approx(600)
    assert f.nodes["db"].rps == approx(1000) and f.nodes["db"].latency_ms == approx(40)
    assert f.latency_ms == approx(640) and f.error_rate == approx(1 / 3)

def test_cache_cuts_db_load():
    # User→Server(2)→Cache(hit 0.8)→Database; 1500 rps, read 0.9
    f = solve(...)
    assert f.nodes["db"].rps == approx(420) and f.nodes["db"].latency_ms == approx(25.3165)
    assert f.latency_ms == approx(129.150) and f.error_rate == approx(0)

def test_read_replicas_split_reads():
    # User→Server(3)→Database(read_replicas 2); 2400 rps, read 0.9
    assert f.nodes["db"].rho == approx(0.48) and f.error_rate == approx(0)
    # same without replicas: rho 1.2, error_rate 1/6

def test_queue_backlog_and_loss():
    # User→Server(1)-async→Queue(max_size 10000)→Worker(1)→Database; 800 rps, read 0, 60 s
    assert f.latency_ms == approx(150) and f.error_rate == approx(0)
    assert f.message_loss == approx(1 / 6) and f.nodes["db"].rps == approx(500)

def test_down_terminal_fails_everything():
    # User→Server→Database, down={"db"}: error_rate 1.0

def test_rate_limiter_rejects():
    # User→RateLimiter(limit 1000)→Server(2)→Database; 3000 rps
    assert f.rejected_rate == approx(2 / 3) and f.error_rate == approx(2 / 3)

def test_more_replicas_never_more_errors(): ...  # Server replicas 1..5 under 3000 rps: error_rate non-increasing
def test_cache_never_raises_db_load(): ...       # hit 0..0.99 step: db rps non-increasing
def test_degenerate_flows_are_finite():           # Review Focus 3
    # ratio 0 edge, hit 0.99, a node with λ=0: every metric finite, s=1 and latency=base at λ=0
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать `solve`** по алгоритму выше.
- [ ] **Step 4: Прогнать тесты и `make lint-api`.**
- [ ] **Step 5: Commit** `feat(simulator): flow solver with golden tests`

---

### Task 3: Сценарии и объяснения

**Files:**
- Create: `engine/scenarios.py`
- Test: `apps/api/tests/test_sim_scenarios.py`

**Interfaces:**
- Consumes: `solve`, `Flow`, `Graph`, `CATALOG`.
- Produces:
  - `Failure(BaseModel): type: NodeType, mode: Literal["replica","node"]`.
  - `Scenario(BaseModel)` (`extra="forbid"`): `id: str`, `title: str`, `visible: bool`, `multiplier: float = Field(gt=0, le=100)`, `duration_s: float = Field(60, gt=0, le=3600)`, `failure: Failure | None = None`, `max_latency_ms: float = Field(gt=0)`, `max_error_rate: float = Field(ge=0, le=1)`, `max_message_loss: float = Field(0, ge=0, le=1)`.
  - `@dataclass(frozen=True) ScenarioResult(id, title, visible, passed: bool, latency_ms, error_rate, rejected_rate, message_loss, bottleneck: str | None, explanation: str, nodes: dict[str, NodeMetrics])`.
  - `apply_failure(g: Graph, failure: Failure, normal: Flow) -> tuple[Graph, frozenset[str]]`.
  - `run_scenario(g: Graph, peak_rps: float, read_ratio: float, sc: Scenario) -> ScenarioResult`.
- **Отказ.**
  - Цель — узел типа `failure.type` с наибольшей `ρ` в `normal` (при равенстве первый по `id`). Нет такого узла — граф без изменений (Review Focus 2).
  - `replica`: копий узла (`replicas`, у Database `read_replicas`) становится на одну меньше. Если копий не остаётся (`replicas` был 1, у Database `read_replicas` был 0), режим становится `node`.
  - `node`: у узла есть исходящие рёбра — его входящие рёбра переподключаются к детям с `ratio = r_in × r_out`; `kind` становится `async`, если хотя бы одно из двух рёбер async. Узел без детей попадает в `down`.
- **Объяснение.** Числа форматируются с пробелом-разделителем тысяч. Метка узла — `CATALOG[type].label`, плюс ` {id}`, если узлов этого типа больше одного.
  - Узкое место с `ρ ≥ 1`: «{метка} получает {λ} rps при ёмкости {μ}: {доля}% запросов теряется».
  - Провал по задержке: «Средняя задержка {L} мс{ при цели T мс}; узкое место — {метка} (загрузка {ρ}%)». Скобка с целью есть только при `visible=True`.
  - Потеря сообщений: «Очередь теряет {loss}% сообщений: обработчики успевают {μ} из {λ} в секунду».
  - Пройден: «Схема выдерживает сценарий; самое загруженное — {метка} ({ρ}%)».

- [ ] **Step 1: Написать падающие тесты.**

```python
def test_spike_multiplies_load(): ...                 # multiplier 3 -> user rps ×3
def test_failure_cache_node_bypasses_to_db(): ...      # Server→Cache→DB, Cache down: db rps = server out
def test_failure_db_without_replicas_fails_all(): ...  # replica mode, read_replicas 0 -> error_rate 1, passed False
def test_failure_db_with_replica_keeps_writes(): ...   # read_replicas 1 -> 0, error_rate < 1
def test_failure_type_absent_runs_unchanged(): ...     # Review Focus 2
def test_failure_targets_most_loaded_node(): ...       # two Servers, the hotter one fails
def test_verdict_checks_all_targets(): ...             # latency, error, loss each can fail
def test_hidden_explanation_never_names_target():
    r = run_scenario(g, 1000, 0.9, Scenario(..., visible=False, max_latency_ms=123))
    assert "123" not in r.explanation
def test_explanation_text_overloaded():
    assert r.explanation == "Database получает 3 200 rps при ёмкости 2 000: 38% запросов теряется"
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать.**
- [ ] **Step 4: Прогнать тесты и `make lint-api`.**
- [ ] **Step 5: Commit** `feat(simulator): scenarios, failures and explanations`

---

### Task 4: Правила архитектуры

**Files:**
- Create: `engine/lint.py`
- Test: `apps/api/tests/test_sim_lint.py`

**Interfaces:**
- Consumes: `Graph`, `active_nodes`.
- Produces: `@dataclass(frozen=True) Finding(code: str, severity: Literal["critical","warning"], message: str, node_id: str | None)` и `lint(g: Graph, read_ratio: float) -> list[Finding]`, порядок — по коду, затем по `node_id`.
- **Коды, условия и тексты (дословно):**
  - `STORAGE_EXPOSED` (critical), ребро User → Database или Cache: «Хранилище доступно пользователю напрямую: между ними нужен сервер».
  - `QUEUE_NO_CONSUMER` (critical), у Queue нет ребра в Worker: «Сообщения из очереди никто не обрабатывает: добавь Worker».
  - `CACHE_BEHIND_DB` (critical), есть путь Database → … → Cache: «Кэш стоит после базы и не снимает с неё нагрузку».
  - `SINGLE_SERVER` (warning), Server с `replicas = 1` и без LoadBalancer среди родителей: «Один сервер без балансировщика — единая точка отказа».
  - `REPLICAS_WITHOUT_LB` (warning), Server с `replicas > 1` без LoadBalancer среди родителей: «Копии сервера есть, а балансировщика перед ними нет».
  - `NO_CACHE_READ_HEAVY` (warning), `read_ratio ≥ 0.8` и ни одного Cache или CDN в активных узлах: «Чтений много, а кэша нет».
  - `DB_NO_REPLICAS` (warning), Database с `read_replicas = 0`: «У базы нет реплик: отказ primary остановит систему».
  - `WORKER_WITHOUT_QUEUE` (warning), в Worker не входит ребро из Queue: «Worker получает задачи не из очереди».
  - `DEEP_SYNC_CHAIN` (warning), sync-путь от User длиннее 5 узлов, `node_id` = последний узел пути: «Цепочка синхронных вызовов длиннее 5 узлов».
  - `ISOLATED_NODE` (warning), у узла нет рёбер: «Узел ни с чем не связан и в расчёт не входит».

- [ ] **Step 1: Написать падающие тесты.** На каждый код два теста, «срабатывает» и «не срабатывает», плюс `test_isolated_node_warning_only` (Review Focus 4).
- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать.**
- [ ] **Step 4: Прогнать тесты и `make lint-api`.**
- [ ] **Step 5: Commit** `feat(simulator): architecture rules`

---

### Task 5: Задачи модуля 10

**Files:**
- Create: `tasks.py`, `content/10-system-design/_module.json` (`{"title": "System design интервью", "description": "Фреймворк ответа и разбор классических задач на симуляторе"}`), `content/10-system-design/simulator/01-url-shortener.{mdx,yaml}`, `02-chat.{mdx,yaml}`, `03-news-feed.{mdx,yaml}`
- Test: `apps/api/tests/test_sim_tasks.py`, `apps/api/tests/fixtures/content_sim/…`

**Interfaces:**
- Consumes: `Scenario`, `Graph`, `run_scenario`, `lint`, `RubricSection` (через `evals.service`; Task 7 добавляет экспорт — здесь допустимо добавить `RubricSection` в `__all__` уже сейчас).
- Produces:
  - `Scale(peak_rps: float = Field(gt=0, le=10_000_000), read_ratio: float = Field(ge=0, le=1))`;
  - `ReviewSpec(threshold: float = Field(gt=0, le=1), rubric: list[RubricSection] = Field(min_length=1, max_length=10), reference: str = Field(min_length=1))`;
  - `SimTask(module, slug, title, summary, statement: str, scale: Scale, scenarios: list[Scenario], review: ReviewSpec, reference_graph: Graph)`, где `statement` — тело MDX без frontmatter. Валидатор требует хотя бы один `visible: true` и хотя бы один `visible: false` сценарий и уникальные `id` сценариев;
  - `class SimTaskFileError(Exception)` с путём файла в тексте;
  - `load_sim_tasks(content_dir: Path) -> list[SimTask]` по `content/<NN-модуль>/simulator/<NN-задача>.{yaml,mdx}`. Правила те же, что у `trainer/tasks.py`: пара файлов, `extra="forbid"`, повтор slug, frontmatter `title`/`summary`, `yaml.safe_load`, чтение файла внутри `try` с именем файла в ошибке;
  - `cached_sim_tasks(content_dir: Path) -> tuple[SimTask, ...]` (`functools.cache`), с комментарием `shortcut: задачи кэшируются до рестарта API, перезагрузка без рестарта не нужна команде`.
- **Контент.** Три задачи по шаблону «Контекст / Требования / Что проверяется». В каждой:
  - 2 открытых сценария: `normal` и `spike`;
  - 3–4 скрытых: отказ Database (`replica`), отказ Cache (`node`), всплеск ×10, для чата и ленты — отказ Worker (`replica`) с целью `max_message_loss`;
  - рубрика из 4 разделов с весом 1: «Требования и допущения», «Оценка нагрузки», «Архитектура», «Компромиссы»; `threshold: 0.7`;
  - `reference` — 5–10 строк эталонного решения;
  - `reference_graph`.
- **Масштаб:** сокращатель ссылок `peak_rps: 20000, read_ratio: 0.95`; чат `peak_rps: 8000, read_ratio: 0.5`; лента `peak_rps: 15000, read_ratio: 0.9`. Цели подбираются так, чтобы эталон проходил с запасом, а наивная схема — нет.

- [ ] **Step 1: Написать падающие тесты.**

```python
def test_load_reads_fixture(tmp_path): ...        # module "system-design", slug "url-shortener", statement without frontmatter
def test_bad_files_name_the_file(...): ...         # broken yaml, missing pair, unknown field, no hidden scenario -> message has file name
def test_real_content_reference_passes_everything():
    for t in load_sim_tasks(REAL_CONTENT):
        assert structural_errors(t.reference_graph) == []
        assert not [f for f in lint(t.reference_graph, t.scale.read_ratio) if f.severity == "critical"]
        assert all(run_scenario(t.reference_graph, t.scale.peak_rps, t.scale.read_ratio, s).passed for s in t.scenarios)
def test_real_content_naive_graph_fails():
    # User→Server(1)→Database fails at least one scenario of every task
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать загрузчик и написать три задачи.**
- [ ] **Step 4: Прогнать `make test-api lint-api test-web`.** `test-web` проверяет, что учебная программа принимает модуль без уроков.
- [ ] **Step 5: Commit** `feat(simulator): task loader and module 10 tasks`

---

### Task 6: API — каталог, задачи, прогон

**Files:**
- Create: `schemas.py`, `service.py`, `providers.py`, `router.py`
- Modify: `apps/api/app/core/container.py`, `apps/api/app/factory.py`, `apps/api/pyproject.toml` (контракт import-linter `simulator`, по образцу `review`/`trainer`)
- Test: `apps/api/tests/test_sim_api.py`

**Interfaces:**
- Consumes: всё из Tasks 1–5, `Settings.content_dir`, `CurrentUser` (как в `trainer/router.py`).
- Produces:
  - `SimulatorService(settings)` с методами:
    - `components() -> list[ComponentOut]`;
    - `tasks(user) -> list[TaskSummaryOut]` (`solved` до Task 7 всегда `False`);
    - `task(module, slug) -> TaskOut`;
    - `run(module, slug, RunIn) -> RunOut`.
  - Схемы:
    - `ComponentOut{type, label, description, capacity_rps, latency_ms, params: [{key, label, kind, min, max, default, help}]}`;
    - `TaskSummaryOut{module, slug, title, summary, solved}`;
    - `TaskOut{module, slug, title, summary, scale, scenarios: list[VisibleScenarioOut{id, title, multiplier, duration_s, failure, max_latency_ms, max_error_rate, max_message_loss}]}` — только `visible`;
    - `RunIn{graph: Graph}`;
    - `RunOut{structural_errors: list[str], scenarios: list[ScenarioOut], findings: list[FindingOut]}`. `ScenarioOut` — поля `ScenarioResult` без `visible`, `nodes` списком `NodeMetricsOut`;
    - неизвестная задача — 404.
  - Эндпоинты: `GET /api/simulator/components`, `GET /api/simulator/tasks`, `GET /api/simulator/tasks/{module}/{task}`, `POST /api/simulator/tasks/{module}/{task}/run`. `run` считает только открытые сценарии и ничего не пишет в БД; при структурных ошибках отвечает 200 с пустыми `scenarios` и `findings`.
  - `EngineError` превращается в 500 с записью в лог (обработчик ядра для необработанных исключений уже есть).

- [ ] **Step 1: Написать падающие тесты.**

```python
async def test_components_catalog(client, sign_in): ...      # 9 types, Server capacity 1000
async def test_task_hides_hidden_parts(client, sign_in):
    body = (await client.get("/api/simulator/tasks/system-design/url-shortener")).text
    for secret in ("reference", "rubric", "threshold", "reference_graph", "Отказ базы"):
        assert secret not in body          # + every hidden scenario title from the YAML
async def test_run_returns_visible_scenarios_only(client, sign_in): ...
async def test_run_structural_errors_200(client, sign_in): ...
async def test_run_validation_422(client, sign_in): ...       # bad type, replicas 0, 51 nodes, NUL in id
async def test_unknown_task_404(client, sign_in): ...
async def test_requires_auth(client): ...                     # 401
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать, зарегистрировать провайдер и роутер, добавить контракт import-linter.**
- [ ] **Step 4: Прогнать `make test-api lint-api`, затем `make gen-client`.**
- [ ] **Step 5: Commit** `feat(simulator): components, tasks and run API` (вместе со сгенерированным клиентом)

---

### Task 7: Попытки и AI-разбор

**Files:**
- Create: `models.py`, `review.py`, миграция `sim_attempts`
- Modify: `schemas.py`, `service.py`, `router.py`, `apps/api/app/modules/evals/judge.py` (выделить `judge_request`), `apps/api/app/modules/evals/service.py` (`__all__`)
- Test: `apps/api/tests/test_sim_attempts.py`

**Interfaces:**
- Consumes:
  - из `evals.service` (добавить в `__all__`): `judge`, `judge_request`, `LlmJudgeGrader`, `RubricSection`, `Grade`, `cost_usd`, `LLMClient`;
  - `judge_request(cfg, inputs, expected, output) -> CompletionRequest` — новая функция в `judge.py`, которую `judge()` использует сам (поведение `judge` не меняется, тесты оценщика остаются зелёными).
- Produces:
  - Таблица `sim_attempts` по спеке, раздел 2: `id uuid pk`, `user_id fk users ON DELETE CASCADE`, `task_key text`, `graph jsonb`, `answers jsonb`, `scenarios jsonb`, `findings jsonb`, `review jsonb NULL`, `review_error text NULL`, `score numeric NULL`, `passed bool`, `cost_usd numeric(10,6)`, `created_at timestamptz default now()`, индекс `(user_id, task_key, created_at)`.
  - `review.py`:
    - `graph_text(g: Graph) -> str` — одна строка на ребро, например «Server (копий 2) → Cache (hit 0.8) [sync ×1]», плюс строка на узел без рёбер;
    - `review_request(task: SimTask, g: Graph, results: list[ScenarioResult], findings: list[Finding], answers: Answers) -> tuple[LlmJudgeGrader, CompletionRequest, dict[str, str], str]`. Здесь `inputs = {"Задача": title + statement, "Схема": graph_text, "Результаты сценариев": …, "Находки правил": …}`, `expected = review.reference`, `output` = три ответа с заголовками полей, `cfg = LlmJudgeGrader(rubric=…, threshold=…, model="claude-sonnet-5-5")`;
    - `estimate_review(llm, req) -> Decimal = cost_usd(model, await llm.count_tokens(req), req.max_tokens)`;
    - `review_attempt(...) -> Grade`, внутри `judge(...)`.
  - `AttemptIn{graph: Graph, answers: Answers{requirements, estimates, tradeoffs}}`. Каждое поле — `str`, ≤ 5000, без NUL.
  - `AttemptOut{id, created_at, graph, answers, scenarios: list[VerdictOut{id, title, visible, passed, explanation}], findings, review: ReviewOut{score, passed, sections: [{name, score, comment}], comment} | None, review_error, score, passed, cost_usd}`. Для скрытых сценариев только эти поля; объяснения уже без целей (Task 3).
  - `SimulatorService` получает `session`, `llm`, методы `submit(user, module, slug, AttemptIn) -> AttemptOut` и `attempts(user, module, slug) -> list[AttemptOut]`. `tasks()` заполняет `solved`.
  - Эндпоинты `POST …/attempts` → 201 и `GET …/attempts` (только свои попытки, новые сверху).
  - Доменные ошибки:
    - `SubmitLimitReached` (429, «Лимит отправок на сегодня исчерпан»);
    - `GraphNotRunnable` (422, «Схема не прогоняется: » + ошибки через «; »);
    - `ReviewTooExpensive` (400, «Ожидаемая стоимость разбора $X выше лимита $0.10»).
- **Порядок `submit`** (спека, раздел 6):
  1. Суточный лимит: 20 попыток за 24 часа с `review_error IS NULL`. Пометка `shortcut: лимит в коде и без блокировки строки, вынести в настройки и закрыть гонку при публичном запуске`.
  2. Структурные ошибки дают 422 без вызова Claude.
  3. Все сценарии и правила.
  4. `estimate_review` больше $0.10 — 400.
  5. `review_attempt`. `anthropic.APIError` даёт `review_error` «AI-разбор не удался: Claude API недоступен» с логом и `exc_info`. `Grade.error` даёт «AI-разбор не удался: {error}».
  6. `passed = все сценарии пройдены and нет critical and grade.passed`.
  7. Сохранить попытку; `cost_usd = grade.cost_usd`.
- Логи: `extra={"attempt_id", "task_key"}`, без текстов студента. Синхронный вызов с пометкой `shortcut: синхронный вызов Claude, перенести в worker, если ответы станут дольше минуты`.

- [ ] **Step 1: Написать падающие тесты** (`fake_llm` со скриптованным ответом судьи).

```python
async def test_submit_passes_with_reference_graph_and_good_review(client, sign_in, fake_llm): ...  # passed True, score ≥ 0.7, solved True in list
async def test_submit_fails_on_critical_finding(...): ...
async def test_structural_errors_422_and_no_claude_call(...): ...   # fake_llm.calls == []
async def test_review_api_error_saved_with_review_error(...): ...    # passed False, not counted in limit
async def test_judge_bad_answer_saved_with_review_error(...): ...
async def test_daily_limit_429(...): ...                             # 20 attempts then 429; review_error ones not counted
async def test_review_cost_over_limit_400(...): ...                  # fake count_tokens huge
async def test_attempt_hides_hidden_numbers(...):
    body = r.text
    for secret in ("reference", "rubric", "threshold", "max_latency_ms", <hidden targets from YAML>):
        assert secret not in body
async def test_attempts_private(...): ...                            # bob sees []
async def test_judge_unchanged(...): ...                             # existing evals judge tests still pass (run the suite)
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать. Миграцию сгенерировать через `alembic revision --autogenerate` и прочитать глазами.**
- [ ] **Step 4: Прогнать `make test-api lint-api migrate-check`, затем `make gen-client`.**
- [ ] **Step 5: Commit** `feat(simulator): attempts with AI review, limits and history`

---

### Task 8: Веб — список задач и рабочее место

**Files:**
- Modify: `apps/web/package.json` (`@xyflow/react` 12.x, точная версия), `components/header.tsx` (ссылка «Симулятор» → `/simulator`)
- Create:
  - `app/(app)/simulator/page.tsx`, `app/(app)/simulator/[module]/[task]/page.tsx`;
  - `components/simulator/{workspace,canvas,palette,inspector,edge-popover,sim-node}.tsx`;
  - `lib/simulator.ts`.
- Test: `apps/web/test/simulator.test.ts`

**Interfaces:**
- Consumes: эндпоинты Tasks 6–7 через `serverApi`/`browserApi`; `loadLesson(module, slug, CONTENT_DIR, "simulator")` для условия (как `loadTaskStatement` у Тренажёра); `useAction`.
- Produces (`lib/simulator.ts`):
  - `toApiGraph(nodes: FlowNode[], edges: FlowEdge[]) -> ApiGraph`, `fromApiGraph(g: ApiGraph) -> {nodes, edges}`;
  - `draftKey(module, slug) = "devplus:sim:" + module + "/" + slug`;
  - `loadDraft(key, catalog) -> {graph, answers} | "reset" | null` — `"reset"`, если тип узла не из каталога, параметр вне пределов или JSON битый;
  - `saveDraft(key, draft)`;
  - `heat(rho) -> "ok" | "warm" | "hot" | "fail"` (< 0.7, < 0.9, < 1, ≥ 1);
  - `newNodeId(type, existing)`.
- **Страницы:**
  - `/simulator`: заголовок «Симулятор», задачи по модулям, у решённых «✓ решено».
  - Рабочее место по спеке, раздел 8:
    - слева «Компоненты» (кнопки; Enter или клик ставит узел в центр, есть drag на canvas, описание при наведении) и «Инспектор» (форма из `ComponentOut.params`);
    - центр — React Flow с портами; клик по ребру открывает popover «sync / async» и «ratio»; Delete удаляет; Ctrl+Z / Ctrl+Y; zoom и fit;
    - пустое состояние: «Добавь User и опиши, куда идут запросы»;
    - справа вкладки «Условие», «Ответы», «Результаты», «Попытки» (последние две заполняет Task 9);
    - кнопка «Начать заново»;
    - при ширине < 1024 px показывается «Редактор доступен на компьютере» и вкладка «Условие».
  - Черновик сохраняется при каждом изменении (debounce 500 мс). Сброс показывает «Черновик устарел и сброшен».

- [ ] **Step 1: Написать падающие vitest.**

```ts
test("toApiGraph/fromApiGraph round-trip keeps ids, params, kinds, ratios and positions", ...);
test("loadDraft resets an unknown node type and a param out of range", ...);   // Review Focus 1
test("loadDraft returns null when nothing is stored and 'reset' on broken JSON", ...);
test("heat thresholds", () => { expect(heat(0.69)).toBe("ok"); expect(heat(0.7)).toBe("warm"); expect(heat(0.9)).toBe("hot"); expect(heat(1)).toBe("fail"); });
```

- [ ] **Step 2: Запустить, убедиться, что тесты падают.**
- [ ] **Step 3: Реализовать страницы и компоненты.**
- [ ] **Step 4: Прогнать `make test-web lint-web`.**
- [ ] **Step 5: Commit** `feat(web): simulator task list and workspace`

---

### Task 9: Веб — прогон, отправка, результаты, попытки

**Files:**
- Create: `components/simulator/{results,answers,attempts,scenario-switch}.tsx`, `apps/web/e2e/simulator.spec.ts`
- Modify: `components/simulator/workspace.tsx`, `canvas.tsx`, `sim-node.tsx`

**Interfaces:**
- Consumes: `POST …/run`, `POST …/attempts`, `GET …/attempts`; `heat`, `toApiGraph`, `fromApiGraph`; `useAction`.
- **Поведение и тексты:**
  - «Прогнать» вызывает `run`. Структурные ошибки показываются списком. Иначе по каждому открытому сценарию:
    - ✓ или ✗ и название;
    - «Средняя задержка: N мс», «Ошибки: N%», при потерях «Потеряно сообщений: N%»;
    - объяснение;
    - ниже находки правил («Критично» / «Предупреждение»), клик выделяет и центрирует узел.
  - Переключатель сценария красит узлы по `heat(rho)` и подписывает «λ / μ rps».
  - «Ответы» — три поля с подписями из Global Constraints и счётчиком «N / 5000».
  - «Отправить» вызывает `attempts`. На время запроса текст «Разбираем решение…», кнопки заблокированы. Потом:
    - вердикты всех сценариев, у скрытых пометка «скрытый»;
    - AI-разбор по разделам (балл 1–5 и комментарий), общий комментарий, «Балл: 0.82»;
    - итог «Зачтено» или «Не зачтено»;
    - `review_error` показывается текстом. Ошибки 422, 429 и 400 — `detail` API.
  - «Попытки»: дата, балл, итог. Клик открывает схему попытки на canvas только для просмотра и показывает кнопку «Вернуться к черновику».

- [ ] **Step 1: Написать падающий e2e** (на фейковом LLM; судья отвечает по схеме через `FakeLLMClient`).
  1. Открыть `/simulator`, увидеть «Сокращатель ссылок».
  2. Собрать с клавиатуры и мышью User → Server → Database (порты через `page.mouse`), нажать «Прогнать» и увидеть ✗ и «получает».
  3. Заполнить три ответа, нажать «Отправить»; сразу после клика кнопка `toBeDisabled()` (Review Focus 5). Затем «Не зачтено».
  4. Во вкладке «Попытки» одна строка.
  5. В DOM нет ни одной цели скрытого сценария и ни одной строки `reference` из YAML.
  6. Перезагрузить страницу — схема из черновика на месте.
- [ ] **Step 2: Запустить, убедиться, что тест падает.**
- [ ] **Step 3: Реализовать.**
- [ ] **Step 4: Прогнать `make e2e test-web lint-web`.**
- [ ] **Step 5: Commit** `feat(web): simulator run, submit, results and attempts`

---

### Task 10: Образы, документация, дорожная карта

**Files:**
- Modify: `.dockerignore` и/или `apps/api/Dockerfile` (образ API получает `content/**/simulator/*.yaml` и `*.mdx`), `apps/web/Dockerfile` (без `content/**/simulator/*.yaml`, как уже без `tasks/*.yaml`), `README.md` (симулятор в описании), `docs/roadmap.html`, `docs/superpowers/plans/2026-10-26-devplus-simulator.md`

- [ ] **Step 1: Собрать оба образа и проверить содержимое.** `docker run --rm <api> ls /app/content/10-system-design/simulator` показывает 6 файлов. В образе web нет `*.yaml` под `simulator/`.
- [ ] **Step 2: Обновить `docs/roadmap.html`.** Подпроект 3: «Реализация» done, pill «реализовано», строка «Этап». После коммита перепубликовать артефакт.
- [ ] **Step 3: Commit** `chore: ship simulator tasks in the api image; roadmap`
