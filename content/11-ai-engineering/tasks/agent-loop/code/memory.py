"""Message history of one conversation."""

import json

SYSTEM_PROMPT = "You are an assistant of the platform team. Use tools when you need facts."


class History:
    def __init__(self) -> None:
        self._messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    @property
    def messages(self) -> list[dict]:
        return self._messages

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str, tool_calls: list) -> None:
        message: dict = {"role": "assistant", "content": text}
        if tool_calls:
            message["tool_calls"] = [
                {"id": c.id, "name": c.name, "arguments": json.dumps(c.arguments)}
                for c in tool_calls
            ]
        self._messages.append(message)

    def add_tool_result(self, call_id: str, content: str) -> None:
        self._messages.append({"role": "tool", "tool_call_id": call_id, "content": content})
