"""Freeze and verify the installers for all pinned agent versions."""

from agents import VERSIONS
from images import InstallerCache

if __name__ == "__main__":
    cache = InstallerCache(list(VERSIONS.items()), fetch=True)
    cache.close()
