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
from contextlib import contextmanager
from pathlib import Path

HARNESS_CPUS = {0, 1}
# Two physical cores, with both threads of each, as podman's --cpuset-cpus
# takes them. Agents that use threads behave as they do for users.
AGENT_CPUS = "2,3,4,5"
# Ticks of /proc/stat per second.
USER_HZ = os.sysconf("SC_CLK_TCK")


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


def steal():
    """Seconds that the hypervisor ran something else on the agent's CPUs,
    since boot. On a VM with reserved cores, this stays near zero."""
    total = 0
    for line in Path("/proc/stat").read_text().splitlines():
        name, *fields = line.split()
        if name.removeprefix("cpu") in AGENT_CPUS.split(","):
            total += int(fields[7])
    return total / USER_HZ


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
