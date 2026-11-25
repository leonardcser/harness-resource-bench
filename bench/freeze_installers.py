"""Freeze and verify the installers for all pinned agent versions."""

from agents import AGENTS
from images import InstallerCache

if __name__ == "__main__":
    cache = InstallerCache(
        [(name, agent.version) for name, agent in AGENTS.items()], fetch=True
    )
    cache.close()
