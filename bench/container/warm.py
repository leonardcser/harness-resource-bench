"""Start the agent's shared background server, as an earlier launch of the day
would, and wait until the container is idle. Then run the command after `--`.

usage: warm.py SERVER... -- COMMAND...

Startup time counts from the exec mark of COMMAND, so this does not count.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Idle: at most one clock tick of CPU in each window, for IDLE_WINDOWS in a row.
WINDOW = 0.25
IDLE_WINDOWS = 4
TIMEOUT = 30


def ticks():
    """The CPU ticks of every process in the container but this one."""
    total = 0
    for stat in Path("/proc").glob("[0-9]*/stat"):
        if stat.parent.name == str(os.getpid()):
            continue
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        total += int(fields[11]) + int(fields[12])
    return total


split = sys.argv.index("--")
server, command = sys.argv[1:split], sys.argv[split + 1 :]
started = subprocess.run(
    server, check=False, stdin=subprocess.DEVNULL, capture_output=True, text=True
)
if started.returncode:
    sys.exit(f"{' '.join(server)} failed: {started.stdout}{started.stderr}")
deadline, idle, last = time.monotonic() + TIMEOUT, 0, ticks()
while idle < IDLE_WINDOWS:
    if time.monotonic() > deadline:
        sys.exit(f"The server of {' '.join(server)} did not settle")
    time.sleep(WINDOW)
    now = ticks()
    idle = idle + 1 if now - last <= 1 else 0
    last = now
os.execvp(command[0], command)
