"""Run one earlier session of the agent's TUI, as earlier in a user's day, then
mark and run the launch that counts.

usage: warm.py COMMAND...

The earlier session runs COMMAND in a tmux window like the bench's terminal,
which answers the agent's terminal queries. Once the container is idle, the
window closes, as a user closes it. The shared server that the TUI started
stays, and has served the workspace. Startup time counts from the exec mark of
launch.py, so this does not count.
"""

import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

# Idle: at most one clock tick of CPU in each window, for IDLE_WINDOWS in a row.
WINDOW = 0.25
IDLE_WINDOWS = 4
TIMEOUT = 30
# The bench's terminal: its size and dark theme.
TMUX = ["tmux", "-L", "earlier", "-f", "/dev/null"]
SESSION = ["-x", "120", "-y", "40"]
OPTIONS = (("status", "off"), ("window-style", "fg=#d4d4d4,bg=#1e1e1e"))


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


def settle(what):
    """Wait until the container is idle."""
    deadline, idle, last = time.monotonic() + TIMEOUT, 0, ticks()
    while idle < IDLE_WINDOWS:
        if time.monotonic() > deadline:
            sys.exit(f"The container did not settle {what}")
        time.sleep(WINDOW)
        now = ticks()
        idle = idle + 1 if now - last <= 1 else 0
        last = now


command = sys.argv[1:]
options = [arg for key, value in OPTIONS for arg in (";", "set", "-g", key, value)]
subprocess.run(
    [*TMUX, "new-session", "-d", *SESSION, shlex.join(command), *options],
    check=True,
)
agent = int(subprocess.check_output([*TMUX, "display", "-p", "#{pane_pid}"], text=True))
settle("in the earlier session")
# A closed window: the agent gets SIGHUP. SIGKILL after 5 seconds, as the bench
# stops the first launch.
subprocess.run([*TMUX, "kill-server"], check=True)
deadline = time.monotonic() + 5
while Path(f"/proc/{agent}").exists():
    if time.monotonic() > deadline:
        os.kill(agent, signal.SIGKILL)
        break
    time.sleep(0.05)
settle("after the earlier session")
os.execvp("python3", ["python3", "/tmp/launch.py", *command])
