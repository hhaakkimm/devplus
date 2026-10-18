import re

_VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class MissingVariable(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


def template_variables(t: str) -> set[str]:
    return set(_VAR.findall(t))


def render(t: str, variables: dict[str, str]) -> str:
    def value(m: re.Match[str]) -> str:
        if m[1] not in variables:
            raise MissingVariable(m[1])
        return variables[m[1]]

    # one pass: a value containing "{{x}}" is not expanded again
    return _VAR.sub(value, t)
