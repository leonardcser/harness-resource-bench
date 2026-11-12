"""Summaries of a run, the terminal replay, and the run that the site shows."""

import json
import statistics
import subprocess
from itertools import pairwise
from pathlib import Path

from case import save
from host import AGENT_CPUS
from measure import SESSION_KINDS
from plan import IDLE_MARKS
from terminal import REPLAYS, replay_cost
from workload import text_bytes

# Results live at the root of the repository, beside the harness and the site.
RESULTS = Path(__file__).resolve().parent.parent / "results"
# Names the run that the site shows.
METRICS = (
    "input_ready_seconds",
    "first_request_seconds",
    "pss_bytes",
    "peak_memory_bytes",
    "cpu_seconds",
    "active_cpu_percent",
    "terminal_cpu_seconds",
    "terminal_bytes",
    "steal_seconds",
)
# Long-session and new-sessions runs also report memory, session data and the
# text of the session at each checkpoint (`..._after_N`, N in turns or
# sessions), and `cpu_seconds_per_turn_A_B` between checkpoints. Idle runs
# report CPU and memory at each idle mark, and `idle_wakeups_per_second`.
CHECKPOINT_METRICS = (
    "pss_bytes_after_",
    "session_",
    "cpu_seconds_per_turn_",
    "idle_",
)
SESSION_SPLIT = (
    "session_bytes",
    "session_files",
    *(f"session_{k}_bytes" for k in SESSION_KINDS),
)
# What makes cases repeats of one another.
GROUP = ("agent", "question", "frontend", "rate", "turns")


def cpu_per_turn(start, end):
    seconds = (end["cpu_usec"] - start["cpu_usec"]) / 1e6
    return seconds / (end["completed_turns"] - start["completed_turns"])


def derived(result, case):
    """The checkpoint metrics of one finished case, from its raw checkpoints."""
    points = result["checkpoints"]
    if case["question"] in ("long-session", "new-sessions"):
        for point in points:
            turns = point["completed_turns"]
            result[f"pss_bytes_after_{turns}"] = point["pss_bytes"]
            for name in SESSION_SPLIT:
                result[f"{name}_after_{turns}"] = point[name]
            result[f"session_text_bytes_after_{turns}"] = text_bytes(
                turns, case["calls"]
            )
        for start, end in pairwise(points):
            span = f"{start['completed_turns']}_{end['completed_turns']}"
            result[f"cpu_seconds_per_turn_{span}"] = cpu_per_turn(start, end)
    if case["question"] == "idle":
        # Idle CPU covers the idle interval only.
        result.update(result["idle"])
        start = result["idle"]["sampling_started_monotonic"]

        def at(seconds):
            return min(points, key=lambda c: abs(c["time"] - start - seconds))

        base = at(0)
        for seconds in IDLE_MARKS:
            if seconds <= case["idle_seconds"]:
                point = at(seconds)
                cpu = (point["cpu_usec"] - base["cpu_usec"]) / 1e6
                result[f"idle_cpu_seconds_after_{seconds}"] = cpu
                result[f"idle_pss_bytes_after_{seconds}"] = point["pss_bytes"]
                result[f"idle_pss_anon_bytes_after_{seconds}"] = point["pss_anon_bytes"]
                result[f"idle_pss_file_bytes_after_{seconds}"] = point["pss_file_bytes"]
        last = max(points, key=lambda c: c["time"])
        if last is not base:
            result["idle_wakeups_per_second"] = (last["wakeups"] - base["wakeups"]) / (
                last["time"] - base["time"]
            )
    return result


def stat(values):
    """The count, median and range of `values`."""
    return {
        "n": len(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def stats(results):
    """The stat of each metric over repeated cases."""
    metrics = {}
    checkpoint_metrics = sorted(
        {k for r in results for k in r if k.startswith(CHECKPOINT_METRICS)}
    )
    for metric in (*METRICS, *checkpoint_metrics):
        values = [r[metric] for r in results if r.get(metric) is not None]
        if values:
            metrics[metric] = stat(values)
    return metrics


def report(out):
    """Write `summary.json` with the median and range of the runs, per agent,
    question and setting. Return whether every planned case passed."""
    manifest = json.loads((out / "manifest.json").read_text())
    planned = manifest["config"]["plan"]
    runs, groups, remotes, canaries = [], {}, {}, []
    for case in planned:
        path = out / "cases" / case["id"] / "result.json"
        if not path.exists():
            continue
        result = json.loads(path.read_text())
        runs.append(
            {"id": case["id"], "status": result["status"], "error": result.get("error")}
        )
        remotes.setdefault(case["agent"], set()).update(
            f"{r['protocol']} {r['address']}:{r['port']}"
            for r in result.get("remote_connections", [])
        )
        if "canary_seconds" in result:
            canaries.append(result["canary_seconds"])
        if result["status"] == "ok":
            key = tuple(case[k] for k in GROUP)
            groups.setdefault(key, []).append(derived(result, case))
    complete = len(runs) == len(planned) and all(r["status"] == "ok" for r in runs)
    save(
        out / "summary.json",
        {
            "planned": len(planned),
            "finished": len(runs),
            "complete": complete,
            "runs": runs,
            "groups": [
                dict(zip(GROUP, key), metrics=stats(results))
                for key, results in sorted(groups.items(), key=lambda kv: str(kv[0]))
            ],
            # The fixed job before every case: the same work over the whole run.
            "canary": stat(canaries) if canaries else None,
            # Addresses outside the host that each agent connected to.
            "remote_connections": {a: sorted(r) for a, r in sorted(remotes.items())},
        },
    )
    return complete


def replay(out):
    """Add the cost of the terminal to every TUI case. Replay its log into tmux
    on the first of the agent's CPUs."""
    manifest = json.loads((out / "manifest.json").read_text())
    cpu = AGENT_CPUS.split(",")[0]
    for case in manifest["config"]["plan"]:
        if case["frontend"] != "tui" or case["question"] == "startup":
            continue
        path = out / "cases" / case["id"] / "result.json"
        result = json.loads(path.read_text())
        if result["status"] != "ok":
            continue
        result.update(replay_cost(path.parent / "terminal.log", cpu))
        save(path, result)
        print(f"REPLAYED {case['id']} {result['terminal_cpu_seconds']:.3f}", flush=True)
    tmux = subprocess.check_output(["tmux", "-V"], text=True).strip()
    manifest["replay"] = {"tmux": tmux, "cpu": cpu, "replays": REPLAYS}
    save(out / "manifest.json", manifest)
    return report(out)
