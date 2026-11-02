"""The agent loop: ask the model, run the tools it asks for, repeat until it answers."""

import logging

from llm import LLMClient
from memory import History
from tools import SCHEMAS, TOOLS

log = logging.getLogger("assistant.agent")


class Agent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, history: History, question: str) -> str:
        history.add_user(question)
        while True:
            reply = self._llm.complete(history.messages, SCHEMAS)
            history.add_assistant(reply.text, reply.tool_calls)
            if not reply.tool_calls:
                return reply.text
            for call in reply.tool_calls:
                log.info("tool call: %s %s", call.name, call.arguments)
                result = TOOLS[call.name](**call.arguments)
                history.add_tool_result(call.id, result)
