import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select, update

from app.modules.evals.graders import ExactGrader
from app.modules.evals.judge import judge_user
from app.modules.evals.models import Prompt, PromptVersion, Run
from app.modules.trainer.tasks import TaskFileError, cached_tasks, load_tasks

FIXTURES = Path(__file__).parent / "fixtures" / "content"
REAL = Path(__file__).parents[3] / "content"
URL = "/api/trainer/tasks/start/iso-dates/attempts"
SYSTEM = "Верни дату в формате ГГГГ-ММ-ДД."
TEMPLATE = "{{text}}"
# the fixture task's cases; the fake answers a rendered `{{text}}` with the reference
HIDDEN = {
    "Секретный вход: 5 марта 2024 года": "2024-03-05",
    "Секретный вход: 17.09.2023": "2023-09-17",
}
HIDDEN_KEYS = {"cases", "input_vars", "output", "grades", "expected"}

MDX = "---\ntitle: T\nsummary: S\n---\n\n## Контекст\n"
YAML = """\
model: claude-haiku-5-5
effort: low
max_tokens: 64
variables: [text]
pass_threshold: 0.8
graders: [{type: exact}]
cases:
  - variables: {text: "a"}
    expected: "b"
"""


@pytest.fixture
def settings(settings):
    return settings.model_copy(update={"content_dir": str(FIXTURES)})


def write_task(root: Path, yaml: str | None = YAML, mdx: str | None = MDX, name: str = "02-bad"):
    folder = root / "00-start" / "tasks"
    folder.mkdir(parents=True, exist_ok=True)
    for suffix, text in (("yaml", yaml), ("mdx", mdx)):
        if text is not None:
            (folder / f"{name}.{suffix}").write_text(text, encoding="utf-8")
    return root


async def attempt(client, system=SYSTEM, template=TEMPLATE, url=URL):
    return await client.post(url, json={"system": system, "user_template": template})


def keys_of(value) -> set[str]:
    match value:
        case dict():
            return set(value) | set().union(*map(keys_of, value.values()))
        case list():
            return set().union(*map(keys_of, value))
        case _:
            return set()


def test_load_tasks_reads_fixture_dir():
    [task] = load_tasks(FIXTURES)
    assert (task.module, task.slug) == ("start", "iso-dates")
    assert (task.title, task.summary) == (
        "Извлеки даты в ISO 8601",
        "Научи модель записывать дату из текста в формате ГГГГ-ММ-ДД.",
    )
    assert (task.model, task.effort, task.max_tokens) == ("claude-haiku-5-5", "low", 64)
    assert (task.variables, task.pass_threshold) == (["text"], 0.5)
    assert task.graders == [ExactGrader(type="exact")]
    assert [(c.variables, c.expected) for c in task.cases] == [
        ({"text": t}, e) for t, e in HIDDEN.items()
    ]


@pytest.mark.parametrize(
    "yaml",
    [
        pytest.param("model: [", id="not yaml"),
        pytest.param("- a\n- b\n", id="not a mapping"),
        pytest.param(YAML.replace("claude-haiku-5-5", "gpt-4"), id="unknown model"),
        pytest.param(YAML + "pass_treshold: 0.5\n", id="unknown field"),
        pytest.param(YAML.replace("0.8", "0"), id="threshold zero"),
        pytest.param(YAML.replace("[text]", "[text, lang]"), id="case without a variable"),
        pytest.param(YAML.replace("[text]", "[a-b]"), id="variable a template cannot name"),
        pytest.param(YAML.replace("graders: [{type: exact}]", "graders: []"), id="no graders"),
        pytest.param(YAML.split("cases:")[0] + "cases: []\n", id="no cases"),
    ],
)
def test_load_tasks_names_bad_file(tmp_path, yaml):
    write_task(tmp_path, yaml)
    with pytest.raises(TaskFileError, match=r"02-bad\.yaml"):
        load_tasks(tmp_path)


@pytest.mark.parametrize(
    ("yaml", "mdx", "bad"),
    [
        pytest.param(YAML, None, "02-bad.yaml", id="yaml without mdx"),
        pytest.param(None, MDX, "02-bad.mdx", id="mdx without yaml"),
        pytest.param(YAML, "## Контекст\n", "02-bad.mdx", id="no frontmatter"),
        pytest.param(YAML, "---\ntitle: T\n---\n", "02-bad.mdx", id="no summary"),
    ],
)
def test_load_tasks_pairs_yaml_with_mdx(tmp_path, yaml, mdx, bad):
    write_task(tmp_path, yaml, mdx)
    with pytest.raises(TaskFileError, match=bad.replace(".", r"\.")):
        load_tasks(tmp_path)


def test_load_tasks_refuses_a_repeated_slug(tmp_path):
    write_task(tmp_path, name="01-same")
    write_task(tmp_path, name="02-same")
    with pytest.raises(TaskFileError, match=r"02-same\.yaml"):
        load_tasks(tmp_path)


def test_load_tasks_orders_by_prefix_and_ignores_other_files(tmp_path):
    write_task(tmp_path, name="10-last")
    write_task(tmp_path, name="02-first")
    (tmp_path / "00-start" / "tasks" / "notes.txt").write_text("x")
    assert [t.slug for t in load_tasks(tmp_path)] == ["first", "last"]


def test_cached_tasks_reads_a_path_once(tmp_path):
    write_task(tmp_path)
    first = cached_tasks(tmp_path)
    (tmp_path / "00-start" / "tasks" / "02-bad.yaml").unlink()
    assert cached_tasks(tmp_path) is first


def test_real_tasks_have_the_agreed_shape():
    iso, polite = load_tasks(REAL)
    assert [(t.module, t.slug) for t in (iso, polite)] == [
        ("start", "iso-dates"),
        ("start", "polite-reply"),
    ]
    assert [(t.model, t.effort, t.max_tokens) for t in (iso, polite)] == [
        ("claude-haiku-5-5", "low", 64),
        ("claude-haiku-5-5", "low", 400),
    ]
    assert [(t.variables, t.pass_threshold, len(t.cases)) for t in (iso, polite)] == [
        (["text"], 0.8, 6),
        (["complaint"], 0.8, 4),
    ]
    assert [g.type for g in iso.graders + polite.graders] == ["exact", "llm_judge"]
    [judge] = polite.graders
    assert (judge.threshold, [s.name for s in judge.rubric]) == (
        0.7,
        ["Вежливость", "Решение проблемы", "Краткость"],
    )


@pytest.mark.parametrize("slug", ["iso-dates", "polite-reply"])
async def test_real_tasks_pass_when_the_model_and_the_judge_are_right(
    slug, fake_llm, run_executor, make_run, db_session
):
    [task] = [t for t in load_tasks(REAL) if t.slug == slug]
    (variable,) = task.variables
    for case in task.cases:
        text = case.variables[variable]
        answer = case.expected or text  # the fake echoes the rendered template back
        fake_llm.responses = {**(fake_llm.responses or {}), text: answer}
        for grader in task.graders:
            if grader.type == "llm_judge":
                verdict = {
                    "sections": [
                        {"name": s.name, "score": 5, "reason": "ok"} for s in grader.rubric
                    ],
                    "comment": "ok",
                }
                prompt = judge_user(grader, case.variables, case.expected, answer)
                fake_llm.responses[prompt] = json.dumps(verdict)
    run = await make_run(
        [c.model_dump() for c in task.cases],
        [g.model_dump(mode="json") for g in task.graders],
        template="{{" + variable + "}}",
        source="trainer",
        pass_threshold=str(task.pass_threshold),
    )
    await run_executor.execute(run.id)
    await db_session.refresh(run)
    assert (run.status, run.pass_rate, run.passed) == ("done", 1, True)


async def test_requires_session(client):
    assert (await client.get("/api/trainer/tasks")).status_code == 401
    assert (await attempt(client)).status_code == 401
    assert (await client.get(URL)).status_code == 401


async def test_submit_creates_trainer_run(client, sign_in, queue, db_session):
    await sign_in("alice")
    first = await attempt(client)
    assert first.status_code == 201, first.text
    second = (await attempt(client, template="Дата: {{text}}")).json()
    first = first.json()
    assert (first["source"], first["status"], first["cases_total"]) == ("trainer", "queued", 2)
    assert first["dataset_id"] is None
    assert queue.ids == [UUID(first["id"]), UUID(second["id"])]

    versions = list(
        await db_session.scalars(
            select(PromptVersion).join(Prompt).where(Prompt.trainer_task == "start/iso-dates")
        )
    )
    versions.sort(key=lambda v: v.number)
    assert [v.number for v in versions] == [1, 2]
    assert [(v.system, v.user_template) for v in versions] == [
        (SYSTEM, TEMPLATE),
        (SYSTEM, "Дата: {{text}}"),
    ]
    assert {(v.model, v.effort, v.max_tokens) for v in versions} == {
        ("claude-haiku-5-5", "low", 64)
    }
    assert [first["prompt_version_id"], second["prompt_version_id"]] == [
        str(v.id) for v in versions
    ]
    runs = await db_session.scalars(select(Run))
    assert {(r.task_slug, r.pass_threshold) for r in runs} == {("start/iso-dates", 0.5)}
    prompt = await db_session.get(Prompt, versions[0].prompt_id)
    assert (prompt.name, prompt.shared) == ("Извлеки даты в ISO 8601", False)

    # every user works on a prompt of their own
    bob = await sign_in("bob")
    third = (await attempt(client)).json()
    [version] = await db_session.scalars(
        select(PromptVersion).where(PromptVersion.id == UUID(third["prompt_version_id"]))
    )
    prompt = await db_session.get(Prompt, version.prompt_id)
    assert (version.number, prompt.owner_id) == (1, bob.id)


async def test_unknown_task_is_404(client, sign_in):
    await sign_in("alice")
    for url in (
        "/api/trainer/tasks/start/nope/attempts",
        "/api/trainer/tasks/nope/iso-dates/attempts",
    ):
        assert (await attempt(client, url=url)).status_code == 404
        assert (await client.get(url)).status_code == 404
    assert (await attempt(client, url="/api/trainer/tasks/start/nope/attempts")).json() == {
        "detail": "Не найдено"
    }


async def test_template_missing_task_variable_is_422(client, sign_in, queue, db_session):
    await sign_in("alice")
    r = await attempt(client, template="Верни дату")
    assert (r.status_code, r.json()) == (422, {"detail": "В шаблоне нет переменных: text"})
    assert queue.ids == []
    assert (
        await db_session.scalar(select(Prompt.id).where(Prompt.trainer_task.is_not(None))) is None
    )


@pytest.mark.parametrize("system", ["я" * 50_000, "a\x00b"], ids=["too long", "NUL"])
async def test_unfit_attempt_is_422(client, sign_in, queue, system):
    await sign_in("alice")
    assert (await attempt(client, system=system)).status_code == 422
    assert queue.ids == []


async def test_hidden_cases_never_leak(client, sign_in, queue, run_executor, db_session):
    await sign_in("alice")
    run = (await attempt(client)).json()
    assert not keys_of(run) & HIDDEN_KEYS
    await run_executor.execute(UUID(run["id"]))  # the fake echoes the case text: stored, not shown
    prompt_id = await db_session.scalar(
        select(Prompt.id).where(Prompt.trainer_task == "start/iso-dates")
    )
    stored = await db_session.scalar(select(Run).where(Run.id == UUID(run["id"])))
    assert stored.status == "done" and stored.cases[0]["expected"] == "2024-03-05"

    urls = [
        f"/api/evals/runs/{run['id']}",
        f"/api/evals/runs?prompt_id={prompt_id}",
        f"/api/evals/prompts/{prompt_id}",
        URL,
    ]
    for url in urls:
        r = await client.get(url)
        assert r.status_code == 200, url
        assert not keys_of(r.json()) & HIDDEN_KEYS, (url, r.text)
        assert not any(s in r.text for s in (*HIDDEN, *HIDDEN.values())), (url, r.text)
    got = (await client.get(f"/api/evals/runs/{run['id']}")).json()
    assert [set(r) for r in got["results"]] == [{"position", "score", "passed"}] * 2

    # the Lab does not list the prompt, and someone else cannot reach it
    assert (await client.get("/api/evals/prompts")).json() == []
    await sign_in("bob")
    assert (await client.get(f"/api/evals/prompts/{prompt_id}")).status_code == 404
    assert (await client.get(f"/api/evals/runs/{run['id']}")).status_code == 404


async def test_solved_flag_after_passing_run(client, sign_in, run_executor, fake_llm, db_session):
    await sign_in("alice")

    async def solved() -> list[dict]:
        r = await client.get("/api/trainer/tasks")
        assert r.status_code == 200
        return r.json()

    assert await solved() == [
        {
            "module": "start",
            "slug": "iso-dates",
            "title": "Извлеки даты в ISO 8601",
            "summary": "Научи модель записывать дату из текста в формате ГГГГ-ММ-ДД.",
            "solved": False,
        }
    ]
    wrong = (await attempt(client)).json()  # the echo is not a date
    await run_executor.execute(UUID(wrong["id"]))
    assert [t["solved"] for t in await solved()] == [False]

    fake_llm.responses = {text: answer for text, answer in HIDDEN.items()}
    right = (await attempt(client)).json()
    await run_executor.execute(UUID(right["id"]))
    assert [t["solved"] for t in await solved()] == [True]

    # a later miss does not take it back, and it is the user's own
    fake_llm.responses = None
    await run_executor.execute(UUID((await attempt(client)).json()["id"]))
    assert [t["solved"] for t in await solved()] == [True]
    await sign_in("bob")
    assert [t["solved"] for t in await solved()] == [False]


async def test_attempts_are_the_users_own_newest_first(client, sign_in, db_session):
    await sign_in("alice")
    old, new = [(await attempt(client)).json() for _ in range(2)]
    # one transaction gives both the same `now()`: age the first one
    long_ago = datetime(2020, 1, 1, tzinfo=UTC)
    await db_session.execute(
        update(Run).where(Run.id == UUID(old["id"])).values(created_at=long_ago)
    )
    listed = (await client.get(URL)).json()
    assert [r["id"] for r in listed] == [new["id"], old["id"]]
    assert {r["source"] for r in listed} == {"trainer"}
    await sign_in("bob")
    assert (await client.get(URL)).json() == []
