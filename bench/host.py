"""The measurement host: its checks, its CPUs and what it records.

CPUs 0 and 1 are the harness core: the controller, the mock model, the sampler
and the terminal run there. The agent's container runs on AGENT_CPUS. On the
benchmark VM, these are both threads of two physical cores that nothing else
uses, and one case runs at a time.
"""

import fcntl
import os
import platform
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

HARNESS_CPUS = {0, 1}
# Two physical cores, with both threads of each, as podman's --cpuset-cpus
# takes them. Agents that use threads behave as they do for users.
AGENT_CPUS = "2,3,4,5"
# A fixed amount of CPU work, which prints its own CPU time. It hashes a 4 MiB
# buffer, more than a core's L2 cache, so both the clock and the L3 cache show
# in its time. The hash runs in C: a pure Python loop varies by 5% to 10% from
# one process to the next, with the memory layout.
CANARY = """
import hashlib, time
data = bytes(range(256)) * (1 << 14)
start = time.process_time()
for _ in range(64):
    hashlib.blake2b(data).digest()
print(time.process_time() - start)
"""
# Ticks of /proc/stat per second.
USER_HZ = os.sysconf("SC_CLK_TCK")
# Fields of a CPU line in /proc/stat: busy time (user, nice, system, irq,
# softirq) and steal time.
BUSY = (0, 1, 2, 5, 6)
STEAL = (7,)
# The window in which the agent's CPUs must stay idle before a case.
QUIET_SECONDS = 0.5


def check():
    """Stop before any work, with every reason, if this host cannot measure."""
    problems = [
        f"{tool} is not installed"
        for tool in ("podman", "tmux")
        if not shutil.which(tool)
    ]
    if shutil.which("podman"):
        info = subprocess.run(
            ["podman", "info", "--format", "{{.Host.Security.Rootless}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if info.returncode:
            problems.append(f"podman does not work: {info.stderr.strip()}")
        elif info.stdout.strip() != "true":
            problems.append("podman must run rootless")
        elif subprocess.check_output(["podman", "ps", "-q"], text=True).strip():
            problems.append("other containers are running")
    uid = os.getuid()
    delegated = Path(
        f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service/cgroup.controllers"
    )
    if not delegated.exists():
        problems.append("cgroup v2 is required")
    elif missing := {"cpu", "cpuset", "memory", "pids"} - set(
        delegated.read_text().split()
    ):
        problems.append(f"systemd does not delegate {sorted(missing)} to the user")
    needed = HARNESS_CPUS | {int(cpu) for cpu in AGENT_CPUS.split(",")}
    if missing := needed - os.sched_getaffinity(0):
        problems.append(f"CPUs {sorted(missing)} are missing")
    if problems:
        raise RuntimeError("This host cannot run the benchmark: " + "; ".join(problems))


@contextmanager
def exclusive():
    """One benchmark or image preparation per host at a time."""
    with open("/tmp/harness-bench.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                "Another benchmark or image preparation is running"
            ) from exc
        yield


def stay_on_harness_core():
    """Keep the calling process and its threads off the agent's CPUs."""
    os.sched_setaffinity(0, HARNESS_CPUS)


def canary():
    """CPU seconds of a fixed job on the agent's first CPU. Over a run, its
    spread shows whether the clock and the isolation held."""
    cpu = int(AGENT_CPUS.split(",")[0])
    return float(
        subprocess.check_output(
            [sys.executable, "-c", CANARY],
            preexec_fn=lambda: os.sched_setaffinity(0, {cpu}),
            text=True,
        )
    )


def ticks(fields):
    """The sum of `fields` of /proc/stat over the agent's CPUs, in ticks."""
    total = 0
    for line in Path("/proc/stat").read_text().splitlines():
        name, *values = line.split()
        if name.removeprefix("cpu") in AGENT_CPUS.split(","):
            total += sum(int(values[i]) for i in fields)
    return total


def steal():
    """Seconds that the hypervisor ran something else on the agent's CPUs,
    since boot. On a VM with reserved cores, this stays near zero."""
    return ticks(STEAL) / USER_HZ


def quiet(timeout=30):
    """Wait until the agent's CPUs are idle, so that work left from the last
    case, such as the kernel freeing its memory, does not run into the next.
    Return the seconds waited."""
    start = time.monotonic()
    before = ticks(BUSY)
    while time.monotonic() - start < timeout:
        time.sleep(QUIET_SECONDS)
        now = ticks(BUSY)
        if now - before <= 1:
            break
        before = now
    return time.monotonic() - start


def machine():
    cpu = next(
        line.split(":", 1)[1].strip()
        for line in Path("/proc/cpuinfo").read_text().splitlines()
        if line.startswith("model name")
    )
    return {
        "hostname": platform.node(),
        "cpu": cpu,
        "kernel": platform.release(),
        "python": platform.python_version(),
        "podman": subprocess.check_output(["podman", "--version"], text=True).strip(),
        "cpu_topology": subprocess.check_output(
            ["lscpu", "-p=CPU,CORE,SOCKET,ONLINE"], text=True
        ),
    }
