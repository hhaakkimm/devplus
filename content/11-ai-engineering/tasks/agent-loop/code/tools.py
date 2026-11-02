"""Tools the model may call. A tool takes keyword arguments and returns text."""

import subprocess
from typing import Callable

from config import WORKSPACE

TOOLS: dict[str, Callable[..., str]] = {}
SCHEMAS: list[dict] = []


def tool(name: str, description: str, properties: dict):
    def register(fn: Callable[..., str]) -> Callable[..., str]:
        TOOLS[name] = fn
        SCHEMAS.append(
            {
                "name": name,
                "description": description,
                "parameters": {"type": "object", "properties": properties},
            }
        )
        return fn

    return register


@tool("read_file", "Read a text file from the workspace", {"path": {"type": "string"}})
def read_file(path: str) -> str:
    target = (WORKSPACE / path).resolve()
    if not target.is_relative_to(WORKSPACE):
        raise ValueError(f"{path} is outside of the workspace")
    return target.read_text()


@tool("run_shell", "Run a shell command in the workspace", {"command": {"type": "string"}})
def run_shell(command: str) -> str:
    done = subprocess.run(command, shell=True, cwd=WORKSPACE, capture_output=True, text=True)
    return done.stdout + done.stderr
