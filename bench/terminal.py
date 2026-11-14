"""The agent's terminal: a tmux pane of fixed size. tmux answers the agent's
terminal queries and keeps its screen. The harness reads the pane's raw output,
keeps it as a log, and types into the pane."""

import fcntl
import os
import re
import select
import shlex
import struct
import subprocess
import tempfile
import termios
import threading
import time
from pathlib import Path

COLUMNS, ROWS = 120, 40
# The key of the startup probe, which no agent draws. A first launch types
# another, so that a draft that the agent keeps cannot pass for the next probe.
PROBE, FIRST_PROBE = "Q", "V"
# After the agent takes a key without drawing it, the probe types the next one
# QUICK later, then waits PAUSE. Two short gaps never follow each other, so
# three keys never come within PAUSE, and no paste detector sees a paste
# (codex: three keys within 8 ms).
QUICK, PAUSE = 0.002, 0.010
# While the agent's tty is out of sight, the probe types a key every PAUSE.
# If it stays out of sight this long, the probe stops looking, and PAUSE is
# the resolution of startup.
TTY_WAIT = 0.1
# Deletes of the probe go in groups, with a gap. Some agents take a fast burst
# of input for a paste, and a paste does not delete.
DELETE_GROUP, DELETE_GAP = 50, 0.02
# Escape sequences, to find text in the raw output.
ANSI = re.compile(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]")
# Scrollback that a turn's done marker is searched in when it is drawn in pieces.
SCREEN_HISTORY = 1000
# The tmux options of the agent's terminal, set once its session exists. The
# window keeps its size when the harness attaches, and the pane stays after the
# agent exits. tmux answers color queries with the pane's colors, a common dark
# theme. All other options keep tmux's defaults.
OPTIONS = (
    ("status", "off"),
    ("window-style", "fg=#d4d4d4,bg=#1e1e1e"),
    ("window-size", "manual"),
    ("remain-on-exit", "on"),
)


def settings():
    """The terminal of every case, for the manifest."""
    return {
        "columns": COLUMNS,
        "rows": ROWS,
        "emulator": subprocess.check_output(["tmux", "-V"], text=True).strip(),
        "options": {**dict(OPTIONS), "history-limit": SCREEN_HISTORY},
    }


# Replay each log this many times and keep the lowest CPU. Noise only adds CPU.
REPLAYS = 5


def server_cpu(pid):
    """Nanoseconds of CPU that the tmux server used, when it stops working."""

    def read():
        return sum(
            int((task / "schedstat").read_text().split()[0])
            for task in Path(f"/proc/{pid}/task").iterdir()
        )

    last = read()
    while True:
        time.sleep(0.05)
        now = read()
        if now == last:
            return now
        last = now


def replay_once(log, cpu, columns, lines):
    """CPU seconds that a new tmux server on core `cpu` spends to parse `log`."""
    # One server per replay. A server that is shutting down refuses new sessions.
    socket = f"bench-replay-{os.getpid()}-{time.monotonic_ns()}"
    tmux = ["tmux", "-L", socket, "-f", "/dev/null"]
    script = (
        f"tmux wait-for go; cat {shlex.quote(str(log))};"
        " tmux wait-for -S replayed; sleep 600"
    )
    subprocess.run(
        ["taskset", "-c", cpu, *tmux, "start-server", ";"]
        + ["set", "-g", "history-limit", "1000000", ";"]
        + ["new-session", "-d", "-x", str(columns), "-y", str(lines), script],
        check=True,
    )
    try:
        pid = subprocess.check_output(
            [*tmux, "display", "-p", "#{pid}"], text=True
        ).strip()
        # Only the replay counts, not the server's start.
        before = server_cpu(pid)
        subprocess.run([*tmux, "wait-for", "-S", "go"], check=True)
        subprocess.run([*tmux, "wait-for", "replayed"], check=True, timeout=600)
        return (server_cpu(pid) - before) / 1e9
    finally:
        subprocess.run([*tmux, "kill-server"], check=False)


def replay_cost(log, cpu, columns=COLUMNS, lines=ROWS):
    """CPU time that a real terminal (tmux) spends to parse the recorded output
    of an agent. The agent does not pay this cost, but the user's machine does."""
    return {
        "terminal_cpu_seconds": min(
            replay_once(log, cpu, columns, lines) for _ in range(REPLAYS)
        ),
        "terminal_bytes": log.stat().st_size,
    }


def tty_state(fd):
    """Whether the tty is in raw mode, and how many bytes wait in its input
    queue. The kernel counts only whole lines outside raw mode."""
    raw = not termios.tcgetattr(fd)[3] & termios.ICANON
    queued = struct.unpack("i", fcntl.ioctl(fd, termios.FIONREAD, b"\0" * 4))[0]
    return raw, queued


class Terminal:
    """Runs `podman start --attach` for `container` in a new tmux server."""

    def __init__(self, container, log):
        self.folder = Path(tempfile.mkdtemp(prefix="harness-terminal-"))
        self.tmux = ["tmux", "-L", f"bench-{os.getpid()}-{time.monotonic_ns()}"]
        self.target = "bench:0.0"
        self.tail = b""
        self.marks = b""
        self.received = 0
        self.launch_time = None
        # Keys that the probes typed, which `erase` deletes.
        self.typed = 0
        # The wall clock when a headless supervisor started the agent.
        self.exec_time = None
        self.watches = {}
        self.errors = []
        self.log = Path(log).open("wb")  # noqa: SIM115 - owned until close()
        # Every log the pane has written to, closed with the terminal.
        self.logs = [self.log]
        self.stop_event = threading.Event()
        # Holds the pid of the container's first process once it starts.
        self.pidfile = Path(
            subprocess.check_output(
                ["podman", "inspect", "--format", "{{.PidFile}}", container],
                text=True,
            ).strip()
        )
        # The pane waits until the harness reads its output, then runs podman in
        # raw mode, as a terminal emulator would.
        go = shlex.join([*self.tmux, "wait-for", "go"])
        attach = shlex.join(["podman", "start", "--attach", "--interactive", container])
        options = [
            arg for key, value in OPTIONS for arg in (";", "set", "-g", key, value)
        ]
        subprocess.run(
            [*self.tmux, "-f", "/dev/null", "start-server", ";"]
            + ["set", "-g", "history-limit", str(SCREEN_HISTORY), ";"]
            + ["new-session", "-d", "-s", "bench", "-x", str(COLUMNS)]
            + ["-y", str(ROWS), f"stty raw -echo; {go}; exec {attach}", *options],
            check=True,
        )
        output = self.folder / "output"
        os.mkfifo(output)
        self.run(
            "pipe-pane", "-O", "-t", self.target, f"cat > {shlex.quote(str(output))}"
        )
        self.output = os.open(output, os.O_RDONLY)
        self.pid = int(self.query("#{pane_pid}"))
        # One control client types for the harness. It gets no pane output.
        self.control = subprocess.Popen(
            [*self.tmux, "-C", "attach-session", "-t", "bench"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.command("refresh-client -f no-output")
        self.threads = [
            threading.Thread(target=self.drain, daemon=True),
            threading.Thread(target=self.listen, daemon=True),
        ]
        for thread in self.threads:
            thread.start()
        self.run("wait-for", "-S", "go")

    def run(self, *args):
        subprocess.run([*self.tmux, *args], check=True, stdout=subprocess.DEVNULL)

    def query(self, format):
        return subprocess.check_output(
            [*self.tmux, "display", "-p", "-t", self.target, format], text=True
        ).strip()

    def command(self, line):
        self.control.stdin.write(line.encode() + b"\n")
        self.control.stdin.flush()

    def listen(self):
        """Keep the control client's replies flowing and remember its errors."""
        reply = []
        for line in self.control.stdout:
            if line.startswith(b"%begin"):
                reply = []
            elif line.startswith(b"%error"):
                self.errors.append(b" ".join(reply).decode("utf-8", "replace"))
            elif not line.startswith(b"%"):
                reply.append(line.strip())

    def drain(self):
        while not self.stop_event.is_set():
            if not select.select([self.output], [], [], 0.05)[0]:
                continue
            data = os.read(self.output, 65536)
            if not data:
                return
            self.log.write(data)
            self.log.flush()
            self.tail = (self.tail + data)[-512_000:]
            self.received += len(data)
            marks = self.marks + data
            if self.launch_time is None:
                match = re.search(rb"BENCH_LAUNCH=(\d+)\x07", marks)
                if match:
                    self.launch_time = int(match[1]) / 1e9
            if self.exec_time is None:
                match = re.search(rb"BENCH_EXEC=(\d+\.\d+)\x07", marks)
                if match:
                    self.exec_time = float(match[1])
            self.marks = marks[-256:]
            if self.watches:
                text = self.text()
                for token in tuple(self.watches):
                    if self.watches[token] is None and token in text:
                        self.watches[token] = time.monotonic()

    def exited(self):
        """Whether podman, and so the agent, has exited."""
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return True
        return False

    def check(self):
        if self.errors:
            raise RuntimeError(f"tmux: {self.errors[0]}")

    def text(self):
        return ANSI.sub(b"", self.tail).decode("utf-8", "replace")

    def screen(self):
        """The pane as tmux draws it, with recent scrollback."""
        return subprocess.check_output(
            [*self.tmux, "capture-pane", "-p", "-t", self.target]
            + ["-S", str(-SCREEN_HISTORY)],
            text=True,
            errors="replace",
        )

    def type(self, keys):
        self.command(f"send-keys -t {self.target} -l -- {shlex.quote(keys)}")

    def quit(self, pid, timeout=10):
        """Type `/quit`, wait until the agent has drawn it, then press Enter.
        Return the seconds from Enter until process `pid` exits."""
        # The exit output goes to its own log, so that the terminal replay of
        # the case leaves it out. Some agents print their transcript on exit.
        self.log = Path(self.logs[0].name).with_name("quit.log").open("wb")
        self.logs.append(self.log)
        self.command(f"send-keys -t {self.target} -l /quit")
        self.settle(quiet=0.3)
        process = os.pidfd_open(pid)
        try:
            start = time.monotonic()
            self.command(f"send-keys -t {self.target} Enter")
            if not select.select([process], [], [], timeout)[0]:
                raise TimeoutError(f"Agent did not quit within {timeout} s")
            return time.monotonic() - start
        finally:
            os.close(process)

    def send(self, value):
        """Paste `value` and press Enter. tmux brackets the paste when the agent
        asks for it."""
        path = self.folder / "paste"
        path.write_text(value)
        self.command(f"load-buffer -b prompt {shlex.quote(str(path))}")
        self.command(f"paste-buffer -p -d -b prompt -t {self.target}")
        # Keep Enter out of paste-burst detection in interactive editors. Under
        # load, fx drops keys that arrive within about 50 ms of a paste.
        self.stop_event.wait(0.2)
        self.command(f"send-keys -t {self.target} Enter")
        self.check()

    def settle(self, quiet=1.0, timeout=30):
        """Wait until the agent has drawn its screen and stopped writing."""
        deadline = time.monotonic() + timeout
        received, changed = self.received, time.monotonic()
        while time.monotonic() < deadline:
            if self.exited():
                raise RuntimeError(
                    "Agent exited before its first prompt; see terminal.log"
                )
            if self.received != received:
                received, changed = self.received, time.monotonic()
            elif received and time.monotonic() - changed >= quiet:
                return
            self.stop_event.wait(0.05)
        raise TimeoutError("Agent screen did not settle; see terminal.log")

    def erase(self, token, timeout=30):
        """Delete the keys that the probe typed, and wait until the screen no
        longer shows `token`. Extra deletes in an empty editor do nothing."""
        for done in range(0, self.typed, DELETE_GROUP):
            count = min(DELETE_GROUP, self.typed - done)
            self.command(f"send-keys -t {self.target} -N {count} BSpace")
            time.sleep(DELETE_GAP)
        self.typed = 0
        self.check()
        deadline = time.monotonic() + timeout
        while token in self.screen():
            if time.monotonic() > deadline:
                raise TimeoutError("Agent editor kept the probe; see terminal.log")
            self.stop_event.wait(0.1)

    def tty(self):
        """The agent's tty, opened from the host, or None until it runs."""
        try:
            pid = int(self.pidfile.read_text())
            return os.open(
                f"/proc/{pid}/fd/0", os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK
            )
        except (OSError, ValueError):
            return None

    def input_ready(self, token=PROBE, timeout=30):
        """Type the key `token` at the exec, as a user who types at once, and
        again only when the agent has taken it without drawing it. Return the
        time from the exec until the agent draws it, and the screen.

        The probe sees the agent's tty from the host: its raw mode, and whether
        the key still waits in its input queue. So at most one key waits for
        the agent. While the tty is out of sight, the probe types a key every
        PAUSE instead."""
        self.watches[token] = None
        deadline = time.monotonic() + timeout
        keys, tty, raw_time = [], None, None
        try:
            while time.monotonic() < deadline:
                if self.exited():
                    raise RuntimeError(
                        "Agent exited before accepting input; see terminal.log"
                    )
                if self.watches[token] is not None:
                    return {
                        "input_ready_seconds": self.watches[token] - self.launch_time,
                        "launch_time": self.launch_time,
                        "input_observed_time": self.watches[token],
                        "probe": "interval" if tty is None else "queue",
                        "probe_keys": len(keys),
                        "raw_mode_seconds": (
                            None if raw_time is None else raw_time - self.launch_time
                        ),
                        "screen": self.text()[-12000:],
                    }
                now = time.monotonic()
                if self.launch_time is None:
                    self.stop_event.wait(0.0005)
                    continue
                if tty is None and now - self.launch_time < TTY_WAIT:
                    tty = self.tty()
                if not keys:
                    send = True
                elif tty is None:
                    send = now - keys[-1] >= PAUSE
                else:
                    raw, queued = tty_state(tty)
                    if raw and raw_time is None:
                        raw_time = now
                    gap = now - keys[-1]
                    previous = keys[-1] - keys[-2] if len(keys) > 1 else PAUSE
                    send = (
                        raw
                        and not queued
                        and gap >= QUICK
                        and (gap >= PAUSE or previous >= PAUSE)
                    )
                if send:
                    self.type(token)
                    self.typed += 1
                    keys.append(now)
                self.stop_event.wait(0.0005)
        finally:
            if tty is not None:
                os.close(tty)
        raise TimeoutError(
            "Agent did not draw the typed probe within 30 seconds; see terminal.log"
        )

    def wait(self, token, model, timeout=300):
        deadline = time.monotonic() + timeout
        received, changed, rendered = self.received, time.monotonic(), None
        while time.monotonic() < deadline:
            if model.error:
                raise RuntimeError(model.error)
            self.check()
            text = self.text()
            if token in text:
                return
            # Diff renderers can draw a token across frames, with cursor moves
            # and other cells between its characters. So when output stops,
            # also check the screen.
            if self.received != received:
                received, changed = self.received, time.monotonic()
            elif rendered != received and time.monotonic() - changed >= 1:
                rendered = received
                if token in self.screen():
                    return
            if "BENCH_EXIT_" in text:
                raise RuntimeError(
                    f"Headless agent exited before {token}; see terminal.log"
                )
            if self.exited():
                raise RuntimeError(f"Agent exited before {token}; see terminal.log")
            self.stop_event.wait(0.05)
        raise TimeoutError(f"Timed out waiting for {token}; see terminal.log")

    def close(self):
        self.stop_event.set()
        subprocess.run(
            [*self.tmux, "kill-server"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.control.wait(timeout=5)
        for thread in self.threads:
            thread.join(timeout=2)
        os.close(self.output)
        for log in self.logs:
            log.close()
        for path in self.folder.iterdir():
            path.unlink()
        self.folder.rmdir()
