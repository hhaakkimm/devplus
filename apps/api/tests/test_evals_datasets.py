import json

import pytest

from app.core.errors import NotFound
from app.modules.evals.schemas import CaseIn
from app.modules.evals.service import DatasetService

NDJSON = {"Content-Type": "application/x-ndjson"}
NOT_AUTHOR = {"detail": "Только автор может изменять"}
MAX_CASE = 32 * 1024


async def make_dataset(client, name="D"):
    r = await client.post("/api/evals/datasets", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


async def put_jsonl(client, ds, body):
    return await client.put(f"/api/evals/datasets/{ds['id']}/cases", content=body, headers=NDJSON)


async def get_dataset(client, ds):
    return (await client.get(f"/api/evals/datasets/{ds['id']}")).json()


def line(**variables):
    return json.dumps({"variables": variables}, ensure_ascii=False)


async def test_requires_session(client):
    assert (await client.get("/api/evals/datasets")).status_code == 401


async def test_create_returns_empty_detail(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    assert (ds["name"], ds["shared"], ds["owner_login"], ds["case_count"], ds["cases"]) == (
        "D",
        False,
        "alice",
        0,
        [],
    )
    assert (await client.get("/api/evals/datasets")).json()[0]["id"] == ds["id"]


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
async def test_dataset_name_validation(client, sign_in, name):
    await sign_in("alice")
    assert (await client.post("/api/evals/datasets", json={"name": name})).status_code == 422


async def test_patch_name_and_shared(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    url = f"/api/evals/datasets/{ds['id']}"
    r = await client.patch(url, json={"name": "  New "})
    assert (r.json()["name"], r.json()["shared"]) == ("New", False)
    r = await client.patch(url, json={"shared": True})
    assert (r.json()["name"], r.json()["shared"]) == ("New", True)
    assert (await client.patch(url, json={"name": " "})).status_code == 422


async def test_import_accepts_bom_crlf_and_blank_lines(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    r = await put_jsonl(client, ds, b'\xef\xbb\xbf{"variables":{"t":"a"}}\r\n\r\n')
    assert (r.status_code, r.json()) == (200, {"count": 1})
    r = await put_jsonl(client, ds, b'\n{"variables":{"t":"a"}}\r\n  \r\n{"variables":{}}')
    assert r.json() == {"count": 2}
    detail = await get_dataset(client, ds)
    assert detail["case_count"] == 2
    assert [(c["position"], c["variables"], c["expected"]) for c in detail["cases"]] == [
        (1, {"t": "a"}, None),
        (2, {}, None),
    ]


async def test_import_reports_line_numbers(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    r = await put_jsonl(
        client, ds, '{"variables":{"t":"a"}}\n{"variables":{"t":5}}\n{"variables":{},"x":1}\n'
    )
    detail = r.json()["detail"]
    assert r.status_code == 422
    assert "Строка 2" in detail and "Строка 3" in detail and "Строка 1" not in detail
    assert "; " in detail  # every error at once, not just the first
    r = await put_jsonl(client, ds, 'not json\n\n{"variables":{}}\n[1]\n')
    assert r.status_code == 422
    assert "Строка 1" in r.json()["detail"] and "Строка 4" in r.json()["detail"]  # raw numbering


async def test_import_rejects_non_utf8_and_nul(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    r = await put_jsonl(client, ds, b'{"variables":{"t":"\xff"}}\n')
    assert r.status_code == 422
    assert "UTF-8" in r.json()["detail"]
    r = await put_jsonl(client, ds, '{"variables":{"t":"a\\u0000"}}\n')
    assert r.status_code == 422 and "Строка 1" in r.json()["detail"]


async def test_import_replaces_cases_atomically(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    await put_jsonl(client, ds, line(t="old1") + "\n" + line(t="old2") + "\n")
    r = await put_jsonl(client, ds, line(t="new") + "\n" + '{"variables":{"t":1}}\n')
    assert r.status_code == 422
    kept = await get_dataset(client, ds)
    assert [c["variables"]["t"] for c in kept["cases"]] == ["old1", "old2"]
    r = await put_jsonl(client, ds, line(t="new") + "\n")
    assert r.json() == {"count": 1}
    assert [c["variables"]["t"] for c in (await get_dataset(client, ds))["cases"]] == ["new"]
    assert (await put_jsonl(client, ds, "")).json() == {"count": 0}  # empty file clears the set


async def test_export_roundtrips(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    src = (
        '{"variables":{"text":"Привет, мир","n":"1"},"expected":"Ответ"}\n'
        '{"variables":{"text":"line\\nbreak"}}\n'
    )
    await put_jsonl(client, ds, src)
    before = (await get_dataset(client, ds))["cases"]
    r = await client.get(f"/api/evals/datasets/{ds['id']}/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")
    assert "Привет, мир" in r.text  # not \u-escaped
    assert r.text.endswith("\n") and r.text.count("\n") == 2
    assert (await put_jsonl(client, ds, r.content)).json() == {"count": 2}
    after = (await get_dataset(client, ds))["cases"]
    key = lambda cs: [(c["position"], c["variables"], c["expected"]) for c in cs]  # noqa: E731
    assert key(after) == key(before)
    empty = await make_dataset(client, "E")
    assert (await client.get(f"/api/evals/datasets/{empty['id']}/export")).text == ""


def padded_case(size):
    overhead = len(json.dumps({"variables": {"a": ""}, "expected": None}))
    return {"variables": {"a": "x" * (size - overhead)}}


async def test_limits(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    ok = "\n".join([line(t="a")] * 1000)
    assert (await put_jsonl(client, ds, ok)).json() == {"count": 1000}
    r = await put_jsonl(client, ds, "\n".join([line(t="a")] * 1001))
    assert r.status_code == 422 and "1000" in r.json()["detail"]
    assert (await get_dataset(client, ds))["case_count"] == 1000  # old cases kept
    # a 33 KB case is rejected, exactly 32 KB is accepted
    assert (await put_jsonl(client, ds, json.dumps(padded_case(MAX_CASE)))).json() == {"count": 1}
    r = await put_jsonl(client, ds, json.dumps(padded_case(MAX_CASE + 1)))
    assert r.status_code == 422 and "Строка 1" in r.json()["detail"]
    assert (await put_jsonl(client, ds, json.dumps(padded_case(33 * 1024)))).status_code == 422


async def test_import_size_limit_is_checked_before_parsing(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    r = await put_jsonl(client, ds, b"x" * (5 * 1024 * 1024 + 1))
    assert r.status_code == 422
    assert r.json()["detail"] == "Файл больше 5 МБ"  # not a pile of per-line errors


async def test_case_size_counts_utf8_bytes_not_escapes(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    # 30 000 Cyrillic letters: 60 KB as UTF-8 -> too big; 15 000: 30 KB -> fits (180 KB if escaped)
    big = {"variables": {"a": "я" * 30_000}}
    r = await client.post(f"/api/evals/datasets/{ds['id']}/cases", json=big)
    assert r.status_code == 422
    fits = {"variables": {"a": "я" * 15_000}}
    assert (
        await client.post(f"/api/evals/datasets/{ds['id']}/cases", json=fits)
    ).status_code == 201
    assert (await put_jsonl(client, ds, json.dumps(fits, ensure_ascii=False))).json() == {
        "count": 1
    }


async def test_case_crud(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    base = f"/api/evals/datasets/{ds['id']}/cases"
    r = await client.post(base, json={"variables": {"t": "a"}, "expected": "A"})
    assert r.status_code == 201
    first = r.json()
    assert (first["position"], first["variables"], first["expected"]) == (1, {"t": "a"}, "A")
    second = (await client.post(base, json={"variables": {"t": "b"}})).json()
    assert second["position"] == 2
    r = await client.put(f"{base}/{first['id']}", json={"variables": {"t": "z"}})
    assert (r.status_code, r.json()["variables"], r.json()["expected"]) == (200, {"t": "z"}, None)
    assert (await client.delete(f"{base}/{first['id']}")).status_code == 204
    third = (await client.post(base, json={"variables": {"t": "c"}})).json()
    assert third["position"] == 3  # positions never repeat after a delete
    cases = (await get_dataset(client, ds))["cases"]
    assert [c["variables"]["t"] for c in cases] == ["b", "c"]
    assert (await get_dataset(client, ds))["case_count"] == 2
    unknown = "00000000-0000-0000-0000-000000000000"
    assert (await client.delete(f"{base}/{unknown}")).status_code == 404
    assert (await client.put(f"{base}/{unknown}", json={"variables": {}})).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"variables": {"t": 5}},
        {"variables": {}, "x": 1},
        {"expected": "a"},
        {"variables": []},
        {"variables": {"t": "a\u0000"}},
        {"variables": {"a\u0000": "t"}},
        {"variables": {}, "expected": "\u0000"},
    ],
)
async def test_case_body_validation(client, sign_in, body):
    await sign_in("alice")
    ds = await make_dataset(client)
    base = f"/api/evals/datasets/{ds['id']}/cases"
    assert (await client.post(base, json=body)).status_code == 422
    case = (await client.post(base, json={"variables": {}})).json()
    assert (await client.put(f"{base}/{case['id']}", json=body)).status_code == 422


async def test_add_case_respects_case_limit(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    await put_jsonl(client, ds, "\n".join([line(t="a")] * 1000))
    r = await client.post(f"/api/evals/datasets/{ds['id']}/cases", json={"variables": {}})
    assert r.status_code == 422 and "1000" in r.json()["detail"]


async def test_case_of_another_dataset_is_404(client, sign_in):
    await sign_in("alice")
    a, b = await make_dataset(client, "A"), await make_dataset(client, "B")
    case = (
        await client.post(f"/api/evals/datasets/{a['id']}/cases", json={"variables": {}})
    ).json()
    url = f"/api/evals/datasets/{b['id']}/cases/{case['id']}"
    assert (await client.put(url, json={"variables": {"t": "x"}})).status_code == 404
    assert (await client.delete(url)).status_code == 404
    assert (await get_dataset(client, a))["case_count"] == 1


async def test_dataset_permissions(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    await put_jsonl(client, ds, line(t="a") + "\n")
    url = f"/api/evals/datasets/{ds['id']}"
    case_id = (await get_dataset(client, ds))["cases"][0]["id"]
    body = {"variables": {"t": "b"}}

    # private: every endpoint is a 404 for others
    await sign_in("bob")
    assert (await client.get(url)).status_code == 404
    assert (await client.get(f"{url}/export")).status_code == 404
    assert (await client.patch(url, json={"shared": True})).status_code == 404
    assert (await client.put(f"{url}/cases", content="", headers=NDJSON)).status_code == 404
    assert (await client.post(f"{url}/cases", json=body)).status_code == 404
    assert (await client.put(f"{url}/cases/{case_id}", json=body)).status_code == 404
    assert (await client.delete(f"{url}/cases/{case_id}")).status_code == 404
    assert (await client.post(f"{url}/copy")).status_code == 404
    assert (await client.get("/api/evals/datasets")).json() == []

    # shared: bob can view, export and copy, but not edit
    await sign_in("alice")
    await client.patch(url, json={"shared": True})
    await sign_in("bob")
    assert (await client.get(url)).status_code == 200
    assert (await client.get(f"{url}/export")).status_code == 200
    listed = (await client.get("/api/evals/datasets")).json()
    assert [(x["name"], x["owner_login"], x["case_count"]) for x in listed] == [("D", "alice", 1)]
    for r in (
        await client.patch(url, json={"name": "mine"}),
        await client.put(f"{url}/cases", content=line() + "\n", headers=NDJSON),
        await client.post(f"{url}/cases", json=body),
        await client.put(f"{url}/cases/{case_id}", json=body),
        await client.delete(f"{url}/cases/{case_id}"),
    ):
        assert (r.status_code, r.json()) == (403, NOT_AUTHOR)
    assert (await get_dataset(client, ds))["cases"][0]["variables"] == {"t": "a"}


async def test_copy_creates_own_dataset_with_cases(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client)
    await put_jsonl(client, ds, '{"variables":{"t":"a"},"expected":"A"}\n' + line(t="b") + "\n")
    await client.patch(f"/api/evals/datasets/{ds['id']}", json={"shared": True})
    await sign_in("bob")
    r = await client.post(f"/api/evals/datasets/{ds['id']}/copy")
    assert r.status_code == 201
    c = r.json()
    assert c["id"] != ds["id"]
    assert (c["owner_login"], c["name"], c["shared"]) == ("bob", "D (копия)", False)
    assert [(x["position"], x["variables"], x["expected"]) for x in c["cases"]] == [
        (1, {"t": "a"}, "A"),
        (2, {"t": "b"}, None),
    ]
    # editing the copy leaves the original alone
    await client.put(f"/api/evals/datasets/{c['id']}/cases", content="", headers=NDJSON)
    assert (await get_dataset(client, ds))["case_count"] == 2


async def test_copy_keeps_name_within_limit(client, sign_in):
    await sign_in("alice")
    ds = await make_dataset(client, "n" * 200)
    r = await client.post(f"/api/evals/datasets/{ds['id']}/copy")
    assert len(r.json()["name"]) == 200 and r.json()["name"].endswith(" (копия)")


async def test_get_cases_follows_dataset_access(client, sign_in, db_session):
    alice = await sign_in("alice")
    ds = await make_dataset(client)
    await put_jsonl(client, ds, '{"variables":{"t":"a"},"expected":"A"}\n' + line(t="b") + "\n")
    bob = await sign_in("bob")
    service = DatasetService(db_session)
    assert await service.get_cases(alice, ds["id"]) == [
        CaseIn(variables={"t": "a"}, expected="A"),
        CaseIn(variables={"t": "b"}),
    ]
    with pytest.raises(NotFound):
        await service.get_cases(bob, ds["id"])
    await sign_in("alice")
    await client.patch(f"/api/evals/datasets/{ds['id']}", json={"shared": True})
    assert len(await service.get_cases(bob, ds["id"])) == 2
