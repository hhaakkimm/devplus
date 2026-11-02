from dataclasses import asdict
from pathlib import Path

from app.core.config import Settings
from app.core.errors import NotFound
from app.modules.auth.service import CurrentUser
from app.modules.simulator.engine.catalog import CATALOG
from app.modules.simulator.engine.graph import structural_errors
from app.modules.simulator.engine.lint import lint
from app.modules.simulator.engine.scenarios import ScenarioResult, run_scenario
from app.modules.simulator.schemas import (
    SimComponentOut,
    SimFindingOut,
    SimNodeMetricsOut,
    SimParamOut,
    SimRunIn,
    SimRunOut,
    SimScale,
    SimScenarioOut,
    SimTaskOut,
    SimTaskSummaryOut,
    SimVisibleScenarioOut,
)
from app.modules.simulator.tasks import SimTask, cached_sim_tasks


def _scenario_out(r: ScenarioResult) -> SimScenarioOut:
    # an explicit list: `visible` stays out, and a field added to ScenarioResult stays hidden
    return SimScenarioOut(
        id=r.id,
        title=r.title,
        passed=r.passed,
        latency_ms=r.latency_ms,
        error_rate=r.error_rate,
        rejected_rate=r.rejected_rate,
        message_loss=r.message_loss,
        bottleneck=r.bottleneck,
        explanation=r.explanation,
        nodes=[SimNodeMetricsOut(**asdict(m)) for m in r.nodes.values()],
    )


class SimulatorService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def components(self) -> list[SimComponentOut]:
        return [
            SimComponentOut(
                type=c.type,
                label=c.label,
                description=c.description,
                capacity_rps=c.capacity_rps,
                latency_ms=c.latency_ms,
                params=[SimParamOut(**asdict(p)) for p in c.params],
            )
            for c in CATALOG.values()
        ]

    async def tasks(self, user: CurrentUser) -> list[SimTaskSummaryOut]:
        # shortcut: `solved` is False until submissions exist, then it reads them for `user`
        return [
            SimTaskSummaryOut(
                module=t.module, slug=t.slug, title=t.title, summary=t.summary, solved=False
            )
            for t in self._tasks()
        ]

    def task(self, module: str, slug: str) -> SimTaskOut:
        t = self._task(module, slug)
        # the schema is the whitelist: attributes it does not list (`visible`, targets of hidden
        # scenarios, `review`, `reference_graph`) never reach the response
        return SimTaskOut(
            module=t.module,
            slug=t.slug,
            title=t.title,
            summary=t.summary,
            scale=SimScale.model_validate(t.scale, from_attributes=True),
            scenarios=[
                SimVisibleScenarioOut.model_validate(s, from_attributes=True)
                for s in t.scenarios
                if s.visible
            ],
        )

    def run(self, module: str, slug: str, body: SimRunIn) -> SimRunOut:
        """Visible scenarios only, nothing is stored. An `EngineError` is a bug, so a 500."""
        t = self._task(module, slug)
        graph = body.graph
        if errors := structural_errors(graph):
            return SimRunOut(structural_errors=errors, scenarios=[], findings=[])
        return SimRunOut(
            structural_errors=[],
            scenarios=[
                _scenario_out(run_scenario(graph, t.scale.peak_rps, t.scale.read_ratio, s))
                for s in t.scenarios
                if s.visible
            ],
            findings=[SimFindingOut(**asdict(f)) for f in lint(graph, t.scale.read_ratio)],
        )

    def _tasks(self) -> tuple[SimTask, ...]:
        return cached_sim_tasks(Path(self.settings.content_dir))

    def _task(self, module: str, slug: str) -> SimTask:
        # matched against the loaded list only: the URL never becomes a path
        for t in self._tasks():
            if (t.module, t.slug) == (module, slug):
                return t
        raise NotFound("Не найдено")
