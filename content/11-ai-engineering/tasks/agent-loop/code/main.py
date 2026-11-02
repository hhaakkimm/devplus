"""Console entry point of the assistant: one conversation until the user quits."""

import logging

from agent import Agent
from config import load_settings
from llm import LLMClient
from memory import History


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    agent = Agent(LLMClient(load_settings()))
    history = History()
    while True:
        question = input("> ").strip()
        if question in {"exit", "quit"}:
            break
        print(agent.run(history, question))


if __name__ == "__main__":
    main()
