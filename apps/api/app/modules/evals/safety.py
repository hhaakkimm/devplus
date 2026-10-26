"""Guards for regexes and JSON schemas that come from users and run inside the worker.

Two ways to take the worker down: a pattern that blows up memory when it compiles (the
`regex` library unrolls repeats: `a{100000000}` needs ~30 GB, and so does `(?:(?:a+)+)+` nested
24 deep), and a pattern or schema that never finishes matching (ReDoS, `$ref` chains).
Compile-time is covered by measuring the pattern before compiling it, match-time by `regex`'s
timeout and by running every schema `pattern` through it.
"""

import importlib
import time
from collections.abc import Iterator
from typing import Any

import regex
from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import ValidationError

MAX_PATTERN_BYTES = 1024
MAX_REPEAT = 1000  # largest counted bound: {n}, {n,}, {n,m}
MAX_EXPANSION = 10_000  # atoms a pattern may unroll to: nested repeats multiply, siblings add
MAX_SCHEMA_DEPTH = 32
TOO_BIG = f"pattern раскрывается больше чем в {MAX_EXPANSION} повторов"
REGEX_BUDGET_S = 1.0  # all pattern matching of one schema validation together

_REF_KEYWORDS = {"$ref", "$dynamicRef", "$recursiveRef"}

# shortcut: leans on the parser inside `regex` (it has no public parse tree), so the size check
# sees exactly what compile will unroll; every pattern test fails if an upgrade moves it, replace
# with a public API when one appears
_core: Any = importlib.import_module("regex._regex_core")


def _parse(pattern: str) -> Any:
    """The parse tree `regex.compile` builds first, before anything is unrolled."""
    flags = 0
    while True:
        source = _core.Source(pattern)
        info = _core.Info(flags, source.char_type)
        info.guess_encoding = regex.UNICODE
        source.ignore_space = bool(info.flags & regex.VERBOSE)
        try:
            tree = _core._parse_pattern(source, info)
        except _core._UnscopedFlagSet:  # a global flag mid-pattern: compile parses again with it
            flags = info.global_flags
            continue
        if not source.at_end():
            raise regex.error("unbalanced parenthesis", pattern, source.pos)
        return tree


def _expansion(node: Any) -> int:
    """Atoms the compiler unrolls `node` to. Measured on `regex`: a repeat makes `min + 1`
    copies of its body (`{2}` and `{2,9}` make 3, `+` makes 2, `*`, `?` and `{0,n}` make 1;
    the part above `min` is a loop, not copies). A character class is shared by its copies."""
    if isinstance(node, _core.SetBase):
        return 1
    kids = [k for v in vars(node).values() for k in (v if isinstance(v, list) else [v])]
    total = sum(_expansion(k) for k in kids if isinstance(k, _core.RegexBase)) or 1
    if isinstance(node, _core.GreedyRepeat):  # lazy and possessive repeats are subclasses
        low, high = node.min_count, node.max_count  # high is None when unbounded
        if max(low, high or 0) > MAX_REPEAT:
            raise ValueError(f"повтор в pattern не больше {MAX_REPEAT}")
        total *= low + 1
    if total > MAX_EXPANSION:
        raise ValueError(TOO_BIG)
    return total


def check_regex(pattern: str) -> None:
    """Raise ValueError unless the pattern is small, cheap to compile and valid."""
    if len(pattern.encode()) > MAX_PATTERN_BYTES:
        raise ValueError("pattern не больше 1 КБ")
    try:
        _expansion(_parse(pattern))  # before compiling: compiling is what runs out of memory
        regex.compile(pattern)
    except regex.error as e:
        raise ValueError(f"pattern не компилируется: {e}") from e
    except KeyError:  # (?V0)(?V1): regex raises a bare KeyError for conflicting version flags
        raise ValueError("pattern не компилируется: конфликт флагов V0 и V1") from None
    except RecursionError:
        raise ValueError("pattern слишком глубоко вложен") from None


def check_grader_schema(schema: dict[str, Any]) -> None:
    """Raise ValueError for what could hang or overload validation of the model's output."""
    has_pattern_props = has_additional = False
    stack: list[tuple[Any, int]] = [(schema, 1)]
    while stack:  # iterative: a hostile depth must not hit the recursion limit
        node, depth = stack.pop()
        if isinstance(node, dict | list) and depth > MAX_SCHEMA_DEPTH:
            raise ValueError(f"schema вложена глубже {MAX_SCHEMA_DEPTH} уровней")
        if isinstance(node, dict):
            if _REF_KEYWORDS & node.keys():
                raise ValueError("$ref, $dynamicRef и $recursiveRef в schema не поддерживаются")
            if isinstance(node.get("pattern"), str):
                check_regex(node["pattern"])
            if isinstance(node.get("patternProperties"), dict):
                has_pattern_props = True
                for key in node["patternProperties"]:
                    check_regex(key)
            has_additional |= "additionalProperties" in node or "unevaluatedProperties" in node
            stack.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            stack.extend((v, depth + 1) for v in node)
    if has_pattern_props and has_additional:
        # shortcut: jsonschema matches those two against patternProperties with the stdlib `re`,
        # which has no timeout; refused until they are overridden to use `regex` like `pattern`
        raise ValueError(
            "patternProperties нельзя сочетать с additionalProperties и unevaluatedProperties"
        )


def schema_validator(schema: dict[str, Any]) -> Draft202012Validator:
    """Validator whose `pattern` and `patternProperties` run on `regex` under one time budget."""
    deadline = time.monotonic() + REGEX_BUDGET_S

    def search(pattern: str, text: str) -> bool:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError
        return regex.search(pattern, text, timeout=left) is not None

    def pattern(v: Any, patrn: str, instance: Any, _: Any) -> Iterator[ValidationError]:
        if v.is_type(instance, "string") and not search(patrn, instance):
            yield ValidationError(f"{instance!r} does not match {patrn!r}")

    def pattern_properties(
        v: Any, props: dict[str, Any], instance: Any, _: Any
    ) -> Iterator[ValidationError]:
        if v.is_type(instance, "object"):
            for patrn, sub in props.items():
                for key, value in instance.items():
                    if search(patrn, key):
                        yield from v.descend(value, sub, path=key, schema_path=patrn)

    cls = validators.extend(  # type: ignore[no-untyped-call]
        Draft202012Validator, {"pattern": pattern, "patternProperties": pattern_properties}
    )
    return cls(schema)  # type: ignore[no-any-return]
