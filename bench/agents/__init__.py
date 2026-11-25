"""The agents. `NAME.toml` holds everything about one agent; the rest of the
harness knows no agent. See `agent.py` for the format."""

from pathlib import Path

from agents.agent import ENV, ROOT, Agent

AGENTS = {}


def register(path):
    """Add the agent of the recipe at `path` to `AGENTS`."""
    agent = Agent.load(path)
    if agent.name in AGENTS:
        raise ValueError(f"{path}: an agent named {agent.name} exists")
    AGENTS[agent.name] = agent
    return agent


for recipe in sorted(Path(__file__).parent.glob("*.toml")):
    register(recipe)

__all__ = ["AGENTS", "ENV", "ROOT", "register"]
