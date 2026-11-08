"""Read CPU and memory from a container cgroup. Record PSS and disk at checkpoints."""

import csv
import ipaddress
import itertools
import os
import threading
import time
from pathlib import Path


def counters(path):
    return {
        key: int(value)
        for key, value in (line.split() for line in path.read_text().splitlines())
    }


def cgroup_for(pid):
    entry = next(
        line
        for line in Path(f"/proc/{pid}/cgroup").read_text().splitlines()
        if line.startswith("0::")
    )
    path = Path("/sys/fs/cgroup") / entry[3:].lstrip("/")
    if not (path / "cpu.stat").is_file() or not (path / "memory.current").is_file():
        raise RuntimeError("CPU and memory cgroup v2 controllers are required")
    return path


def pss(cgroup):
    pids = set()
    for file in cgroup.rglob("cgroup.procs"):
        pids.update(file.read_text().split())
    total, processes = 0, 0
    components = {"Pss_Anon:": 0, "Pss_File:": 0, "Pss_Shmem:": 0}
    for pid in pids:
        try:
            lines = Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines()
        except (ProcessLookupError, FileNotFoundError):
            continue
        except PermissionError as exc:
            raise RuntimeError(
                "PSS unavailable; check user namespace mapping and ptrace permissions"
            ) from exc
        total += next(
            int(line.split()[1]) * 1024 for line in lines if line.startswith("Pss:")
        )
        for line in lines:
            fields = line.split()
            if fields[0] in components:
                components[fields[0]] += int(fields[1]) * 1024
        processes += 1
    if not processes:
        raise RuntimeError("No live processes at PSS checkpoint")
    return {
        "pss_bytes": total,
        "pss_anon_bytes": components["Pss_Anon:"],
        "pss_file_bytes": components["Pss_File:"],
        "pss_shmem_bytes": components["Pss_Shmem:"],
        "processes": processes,
    }


def disk(path, assets=(), depth=3):
    """Apparent size of the files under `path`. The host reads them without
    following links, so the container runs no helper. `session_bytes` does not
    include the `assets` directories. `disk_dirs` sums each directory up to
    `depth` levels down."""
    total, session, dirs = 0, 0, {}
    for directory, _, files in os.walk(path):
        size = 0
        for name in files:
            try:
                size += os.lstat(os.path.join(directory, name)).st_size
            except FileNotFoundError:
                continue
        total += size
        parts = Path(directory).relative_to(path).parts
        if not any(parts[: len(Path(a).parts)] == Path(a).parts for a in assets):
            session += size
        for level in range(1, min(len(parts), depth) + 1):
            key = "/".join(parts[:level])
            dirs[key] = dirs.get(key, 0) + size
    return {"disk_bytes": total, "session_bytes": session, "disk_dirs": dirs}


class Sampler:
    def __init__(self, cgroup, interval=0.1):
        self.cgroup, self.interval = cgroup, interval
        self.samples = []
        self.error = None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def sample(self):
        cpu = counters(self.cgroup / "cpu.stat")
        memory = counters(self.cgroup / "memory.stat")
        events = counters(self.cgroup / "memory.events")
        return {
            "time": time.monotonic(),
            "cpu_usec": cpu["usage_usec"],
            "user_usec": cpu.get("user_usec", 0),
            "system_usec": cpu.get("system_usec", 0),
            "throttled_usec": cpu.get("throttled_usec", 0),
            "memory_bytes": int((self.cgroup / "memory.current").read_text()),
            "peak_bytes": int((self.cgroup / "memory.peak").read_text()),
            "anon_bytes": memory.get("anon", 0),
            "file_bytes": memory.get("file", 0),
            "oom_kill": events.get("oom_kill", 0),
        }

    def run(self):
        deadline = time.monotonic()
        while not self.stop_event.is_set():
            try:
                self.samples.append(self.sample())
            except FileNotFoundError:
                self.error = "Measured cgroup disappeared before final sample"
                return
            except Exception as exc:  # noqa: BLE001 - propagate sampling thread failures
                self.error = str(exc)
                return
            deadline += self.interval
            self.stop_event.wait(max(0, deadline - time.monotonic()))

    def start(self):
        self.thread.start()

    def stop(self):
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        self.thread.join()
        if not self.error:
            try:
                self.samples.append(self.sample())
            except (OSError, ValueError) as exc:
                self.error = str(exc)


def remote_sockets(pids):
    """The remote end of each socket that `pids` hold, for addresses outside
    the host, as {(protocol, address, port)}."""
    inodes = set()
    for pid in pids:
        try:
            for fd in Path(f"/proc/{pid}/fd").iterdir():
                link = os.readlink(fd)
                if link.startswith("socket:["):
                    inodes.add(link[8:-1])
        except OSError:
            continue
    if not inodes:
        return set()
    found = set()
    for protocol in ("tcp", "tcp6", "udp", "udp6"):
        # The table of the processes' network namespace.
        for pid in pids:
            try:
                table = Path(f"/proc/{pid}/net/{protocol}").read_text()
                break
            except OSError:
                continue
        else:
            return found
        for line in table.splitlines()[1:]:
            fields = line.split()
            # A listening TCP socket has no remote end.
            if fields[9] not in inodes or (protocol[:3] == "tcp" and fields[3] == "0A"):
                continue
            address, port = remote_address(fields[2])
            if port and not address.is_loopback and not address.is_unspecified:
                found.add((protocol[:3], str(address), port))
    return found


def remote_address(field):
    """An address and port from /proc/net, where each 32-bit word of the
    address is in host byte order."""
    raw, port = field.split(":")
    packed = b"".join(
        int(raw[i : i + 8], 16).to_bytes(4, "little") for i in range(0, len(raw), 8)
    )
    address = ipaddress.ip_address(packed)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address, int(port, 16)


class Connections:
    """Every remote address that the processes of a cgroup connect to, polled
    from /proc on the controller's CPUs. A connection that opens and closes
    between two polls is missed. HTTPS connections usually stay open longer."""

    def __init__(self, cgroup, interval=0.2):
        self.cgroup, self.interval = cgroup, interval
        self.started = time.monotonic()
        self.first_seen = {}
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def poll(self):
        pids = set()
        for file in self.cgroup.rglob("cgroup.procs"):
            pids.update(file.read_text().split())
        for remote in remote_sockets(sorted(pids)):
            self.first_seen.setdefault(remote, time.monotonic() - self.started)

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.poll()
            except OSError:
                return
            self.stop_event.wait(self.interval)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join()

    def report(self):
        return [
            {"protocol": p, "address": a, "port": port, "first_seconds": round(t, 1)}
            for (p, a, port), t in sorted(self.first_seen.items(), key=lambda kv: kv[1])
        ]


def summarize(samples):
    if len(samples) < 2:
        raise ValueError("At least two resource samples required")
    first, last = samples[0], samples[-1]
    elapsed = last["time"] - first["time"]
    cpu = (last["cpu_usec"] - first["cpu_usec"]) / 1e6
    area = sum(
        (b["time"] - a["time"]) * (a["memory_bytes"] + b["memory_bytes"]) / 2
        for a, b in itertools.pairwise(samples)
    )
    throttled = (last["throttled_usec"] - first["throttled_usec"]) / 1e6
    return {
        "sampling_started_monotonic": first["time"],
        "sampling_ended_monotonic": last["time"],
        "elapsed_seconds": elapsed,
        "cpu_seconds": cpu,
        "average_cpu_percent": 100 * cpu / elapsed,
        "average_memory_bytes": area / elapsed,
        "peak_memory_bytes": max(s["peak_bytes"] for s in samples),
        "last_memory_bytes": last["memory_bytes"],
        "throttled_seconds": throttled,
        "oom_kills": last["oom_kill"] - first["oom_kill"],
    }


def write_samples(path, samples):
    if not samples:
        return
    first = samples[0]
    with path.open("w", newline="") as out:
        writer = None
        for sample in samples:
            row = {
                "elapsed_seconds": round(sample["time"] - first["time"], 6),
                "cpu_seconds": round((sample["cpu_usec"] - first["cpu_usec"]) / 1e6, 6),
                "memory_bytes": sample["memory_bytes"],
                "peak_memory_bytes": sample["peak_bytes"],
                "anonymous_bytes": sample["anon_bytes"],
                "file_cache_bytes": sample["file_bytes"],
                "throttled_seconds": round(sample["throttled_usec"] / 1e6, 6),
                "oom_kills": sample["oom_kill"],
            }
            if writer is None:
                writer = csv.DictWriter(out, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
