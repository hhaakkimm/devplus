"""Component catalog of the simulator: capacity, latency and tunable params per type."""

from dataclasses import dataclass
from typing import Literal

NodeType = Literal[
    "User", "CDN", "RateLimiter", "LoadBalancer", "Server", "Cache", "Database", "Queue", "Worker"
]


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    kind: Literal["int", "float"]
    min: float
    max: float
    default: float
    help: str


@dataclass(frozen=True)
class ComponentSpec:
    type: NodeType
    label: str
    description: str
    capacity_rps: int | None  # per copy; None means unlimited
    latency_ms: float | None  # base latency at no load
    params: tuple[Param, ...]
    terminal_ok: bool  # may end a request path without outgoing edges


def _hit_ratio(help: str) -> Param:
    return Param("hit_ratio", "Доля попаданий", "float", 0, 0.99, 0.8, help)


def _replicas(help: str) -> Param:
    return Param("replicas", "Копий", "int", 1, 100, 1, help)


_SPECS = (
    ComponentSpec("User", "Пользователи", "Источник запросов.", None, None, (), False),
    ComponentSpec(
        "CDN",
        "CDN",
        "Отдаёт статику с ближайшего узла. Каждая копия держит 100 000 rps.",
        100_000,
        5,
        (_hit_ratio("Какая доля запросов отдаётся из CDN, остальные идут дальше."),),
        True,
    ),
    ComponentSpec(
        "RateLimiter",
        "Rate limiter",
        "Отсекает запросы сверх лимита. Каждая копия держит 50 000 rps.",
        50_000,
        2,
        (
            Param(
                "limit_rps",
                "Лимит, rps",
                "int",
                1,
                10_000_000,
                1000,
                "Запросы сверх лимита отбрасываются.",
            ),
        ),
        False,
    ),
    ComponentSpec(
        "LoadBalancer",
        "Балансировщик",
        "Раскладывает запросы по копиям. Каждая копия держит 50 000 rps.",
        50_000,
        2,
        (_replicas("Сколько копий балансировщика работает."),),
        False,
    ),
    ComponentSpec(
        "Server",
        "Сервер",
        "Код приложения. Каждая копия держит 1 000 rps.",
        1000,
        30,
        (_replicas("Сколько копий сервера работает."),),
        False,
    ),
    ComponentSpec(
        "Cache",
        "Кэш",
        "Быстрая память перед базой. Каждая копия держит 50 000 rps.",
        50_000,
        2,
        (
            _hit_ratio("Какая доля запросов находится в кэше, остальные идут дальше."),
            _replicas("Сколько копий кэша работает."),
        ),
        True,
    ),
    ComponentSpec(
        "Database",
        "База данных",
        "Хранит данные. Каждая копия держит 2 000 rps.",
        2000,
        20,
        (
            Param(
                "read_replicas",
                "Реплик для чтения",
                "int",
                0,
                100,
                0,
                "Копии, которые берут на себя чтение.",
            ),
            Param("shards", "Шардов", "int", 1, 100, 1, "На сколько частей разделены данные."),
        ),
        True,
    ),
    ComponentSpec(
        "Queue",
        "Очередь",
        "Буферизует запросы для фоновой обработки. Держит 20 000 rps.",
        20_000,
        5,
        (
            Param(
                "max_size",
                "Размер очереди",
                "int",
                1,
                10_000_000,
                100_000,
                "Сколько сообщений помещается, лишние теряются.",
            ),
        ),
        False,
    ),
    ComponentSpec(
        "Worker",
        "Воркер",
        "Обрабатывает задачи из очереди. Каждая копия держит 500 rps.",
        500,
        50,
        (_replicas("Сколько копий воркера работает."),),
        True,
    ),
)

CATALOG: dict[NodeType, ComponentSpec] = {s.type: s for s in _SPECS}


def check_params(type: NodeType, params: dict[str, float]) -> dict[str, float]:
    """Fill in defaults and reject unknown keys, out-of-range values and fractions for ints."""
    specs = {p.key: p for p in CATALOG[type].params}
    if unknown := sorted(params.keys() - specs.keys()):
        raise ValueError(f"Неизвестный параметр: {', '.join(unknown)}")
    result: dict[str, float] = {}
    for key, p in specs.items():
        value = params.get(key, p.default)
        if not p.min <= value <= p.max:
            raise ValueError(f"{p.label}: допустимо от {p.min:g} до {p.max:g}")
        if p.kind == "int":
            if value != int(value):
                raise ValueError(f"{p.label}: нужно целое число")
            value = int(value)
        result[key] = value
    return result
