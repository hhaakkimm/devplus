"""Public schemas of the simulator. Every OpenAPI name has the `Sim` prefix: `TaskOut` and `RunOut`
already belong to other modules, and a clash silently renames a type in the generated client."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.simulator.engine.catalog import NodeType
from app.modules.simulator.engine.graph import Edge, Graph, Node
from app.modules.simulator.engine.scenarios import Failure
from app.modules.simulator.tasks import Scale


class SimParamOut(BaseModel):
    key: str
    label: str
    kind: Literal["int", "float"]
    min: float
    max: float
    default: float
    help: str


class SimComponentOut(BaseModel):
    type: NodeType
    label: str
    description: str
    capacity_rps: int | None
    latency_ms: float | None
    params: list[SimParamOut]


class SimTaskSummaryOut(BaseModel):
    module: str
    slug: str
    title: str
    summary: str
    solved: bool


class SimScale(Scale):
    pass


class SimFailure(Failure):
    pass


class SimVisibleScenarioOut(BaseModel):
    id: str
    title: str
    multiplier: float
    duration_s: float
    failure: SimFailure | None
    max_latency_ms: float
    max_error_rate: float
    max_message_loss: float


class SimTaskOut(BaseModel):
    module: str
    slug: str
    title: str
    summary: str
    scale: SimScale
    scenarios: list[SimVisibleScenarioOut]


class SimNode(Node):
    pass


class SimEdge(Edge):
    pass


class SimGraph(Graph):
    nodes: list[SimNode] = Field(max_length=50)  # type: ignore[assignment]
    edges: list[SimEdge] = Field(max_length=100)  # type: ignore[assignment]


class SimRunIn(BaseModel):
    graph: SimGraph


class SimNodeMetricsOut(BaseModel):
    id: str
    type: NodeType
    rps: float
    capacity_rps: float | None
    rho: float
    latency_ms: float
    errors_rps: float
    rejected_rps: float
    backlog: float
    message_loss: float


class SimScenarioOut(BaseModel):
    id: str
    title: str
    passed: bool
    latency_ms: float
    error_rate: float
    rejected_rate: float
    message_loss: float
    bottleneck: str | None
    explanation: str
    nodes: list[SimNodeMetricsOut]


class SimFindingOut(BaseModel):
    code: str
    severity: Literal["critical", "warning"]
    message: str
    node_id: str | None


class SimRunOut(BaseModel):
    structural_errors: list[str]
    scenarios: list[SimScenarioOut]
    findings: list[SimFindingOut]


MAX_ANSWER_CHARS = 5000


class SimAnswers(BaseModel):
    requirements: str
    estimates: str
    tradeoffs: str

    @field_validator("requirements", "estimates", "tradeoffs")
    @classmethod
    def check_answer(cls, v: str) -> str:
        if len(v) > MAX_ANSWER_CHARS:
            raise ValueError(f"ответ не длиннее {MAX_ANSWER_CHARS} символов")
        if "\x00" in v:  # Postgres jsonb cannot hold NUL, it would be a 500 on insert
            raise ValueError("символ NUL не допускается")
        return v


class SimAttemptIn(BaseModel):
    graph: SimGraph
    answers: SimAnswers


class SimVerdictOut(BaseModel):
    """A scenario after a submission: for a hidden one its targets and parameters stay out."""

    id: str
    title: str
    visible: bool
    passed: bool
    explanation: str


class SimReviewSectionOut(BaseModel):
    name: str
    score: int
    comment: str


class SimReviewOut(BaseModel):
    score: float
    passed: bool
    sections: list[SimReviewSectionOut]
    comment: str


class SimAttemptOut(BaseModel):
    id: UUID
    created_at: datetime
    graph: SimGraph
    answers: SimAnswers
    scenarios: list[SimVerdictOut]
    findings: list[SimFindingOut]
    review: SimReviewOut | None
    review_error: str | None
    score: float | None
    passed: bool
    cost_usd: Decimal
