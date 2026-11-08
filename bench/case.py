"""Run one case: the agent's container, its terminal, the mock model and the
sampler. The host measures the container from outside."""

import json
import subprocess
import tempfile
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

from agents import AGENTS, ENV, ROOT
from host import AGENT_CPUS, steal
from measure import (
    Connections,
    Sampler,
    cgroup_for,
    disk,
    pss,
    summarize,
    write_samples,
)
from model import Model
from terminal import Terminal
from workload import PROMPT, digest, files, marker, steps

SETTLE_SECONDS = 2
# The memory limit of each container. The highest peak of any agent is under
# 1 GiB.
MEMORY = "4g"


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def create(case, root, port, image_id, prompt):
    """Create the container of a case. The agent starts when it is attached."""
    frontend = case["frontend"]
    home, workspace = root / "home", root / "workspace"
    home.mkdir()
    (workspace / "fixtures").mkdir(parents=True)
    env, args = AGENTS[case["agent"]].configure(
        frontend,
        home,
        f"http://127.0.0.1:{port}",
        [] if case["question"] == "startup" else [prompt],
    )
    command = [
        "podman",
        "create",
        "--interactive",
        "--userns=keep-id",
        # The mock model listens on the host loopback.
        "--network=host",
        "--cpuset-cpus",
        AGENT_CPUS,
        "--memory",
        MEMORY,
        # The same as the memory limit, so a case cannot swap.
        "--memory-swap",
        MEMORY,
        "--pids-limit",
        "512",
        "--cap-drop=all",
        "--security-opt=no-new-privileges",
        "--log-driver=none",
        "--env",
        "HOME=/home/bench",
        "--volume",
        f"{home}:/home/bench:rw",
        "--volume",
        f"{workspace}:/workspace:rw",
        "--volume",
        f"{root / 'fixtures'}:/workspace/fixtures:ro",
    ]
    if frontend == "tui":
        command += ["--tty"]
    for key, value in {**ENV, **env}.items():
        command += ["--env", f"{key}={value}"]
    if case["question"] == "startup":
        command += ["--volume", f"{ROOT / 'container/launch.py'}:/tmp/launch.py:ro"]
        args = ["python3", "/tmp/launch.py", *args]
    elif case["question"] == "start-memory":
        command += ["--volume", f"{ROOT / 'container/evict.py'}:/tmp/evict.py:ro"]
        args = [
            "bash",
            "-c",
            'python3 /tmp/evict.py && exec "$@" </dev/null',
            "cold",
            *args,
        ]
    elif frontend == "headless":
        # The shell keeps the cgroup alive after the agent exits and reports its status.
        # It marks the wall clock just before it starts the agent, with a builtin, so
        # no extra process runs in the measured cgroup.
        args = [
            "bash",
            "-c",
            (
                'printf "\\033]777;BENCH_EXEC=%s\\a" "$EPOCHREALTIME"; "$@" </dev/null;'
                ' rc=$?; printf "\\nBENCH_EXIT_%s\\n" "$rc"; read -r _; exit "$rc"'
            ),
            "supervisor",
            *args,
        ]
    command += [image_id, *args]
    return subprocess.check_output(command, text=True).strip()


def checkpoint(sampler, turn, model, home, assets):
    # Sample without launching helpers in the measured container.
    sample = sampler.sample()
    sample.update(pss(sampler.cgroup))
    sample.update(disk(home, assets))
    sample["completed_turns"] = turn + 1
    sample["request_bytes"] = model.events[-1]["request_bytes"]
    sample["request_history_turns"] = model.events[-1]["history_turns"]
    return sample


def container_pid(container, terminal):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        pid = int(
            subprocess.check_output(
                ["podman", "inspect", "--format", "{{.State.Pid}}", container],
                text=True,
            )
        )
        if pid:
            return pid
        if terminal.exited():
            raise RuntimeError("Container failed to start; see terminal.log")
        time.sleep(0.05)
    raise RuntimeError("Container failed to start")


def execute(case, folder, image_id, smoke=False):
    """Measure `case` and save its result in `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    question = case["question"]
    agent = AGENTS[case["agent"]]
    model = Model(agent, case["rate"], case["calls"])
    # The model holds the first workload request until the sampler runs.
    model.ready.clear()
    sampler = connections = None
    result = {
        "case": case,
        "status": "failed",
        "checkpoints": [],
        "workload_sha256": digest(case["turns"], case["calls"]),
    }
    stolen = steal()
    try:
        with (
            tempfile.TemporaryDirectory(prefix="harness-bench-") as tmp,
            ExitStack() as resources,
        ):
            root = Path(tmp)
            (root / "fixtures").mkdir()
            for turn in range(case["turns"]):
                for name, content in files(turn, case["calls"]).items():
                    (root / name).parent.mkdir(parents=True, exist_ok=True)
                    (root / name).write_text(content)
            model.workspace = root / "workspace"
            container = create(case, root, model.port, image_id, PROMPT.format(turn=0))
            resources.callback(
                subprocess.run,
                ["podman", "rm", "--force", container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
            )
            terminal = Terminal(container, folder / "terminal.log")
            resources.callback(terminal.close)
            if question == "startup":
                readiness = terminal.input_ready()
                (folder / "startup-screen.txt").write_text(readiness.pop("screen"))
                result.update(readiness, status="ok")
                return result
            pid = container_pid(container, terminal)
            # Startup leaves this out, so that the poller cannot delay its probe.
            connections = Connections(cgroup_for(pid))
            connections.start()
            resources.callback(connections.stop)
            if case["frontend"] == "tui" and agent.typed_prompt:
                terminal.settle()
                terminal.send(PROMPT.format(turn=0))
            if not model.received.wait(30):
                raise RuntimeError(
                    model.error or "Agent never reached inference; see terminal.log"
                )
            if question == "start-memory":
                # The agent waits for its first reply; the model never sends it.
                time.sleep(SETTLE_SECONDS)
                result.update(pss(cgroup_for(pid)), status="ok")
                return result
            sampler = Sampler(cgroup_for(pid))
            sampler.samples.append(sampler.sample())
            assets = agent.assets
            sampler.start()
            resources.callback(sampler.stop)
            model.ready.set()
            for turn in range(case["turns"]):
                if turn:
                    if question == "new-sessions":
                        # Each turn is a new session in the same process.
                        terminal.send(agent.reset)
                        time.sleep(SETTLE_SECONDS)
                    terminal.send(PROMPT.format(turn=turn))
                terminal.wait(marker(turn), model, timeout=120 if smoke else 600)
                if question == "task":
                    active = sampler.sample()
                if case["frontend"] == "headless":
                    terminal.wait("BENCH_EXIT_", model, timeout=30)
                    if "BENCH_EXIT_0" not in terminal.text():
                        raise RuntimeError(
                            "Headless agent returned nonzero exit status"
                        )
                if turn + 1 in case["checkpoints"]:
                    time.sleep(0.2 if smoke else SETTLE_SECONDS)
                if model.progress.get(turn) != len(steps(turn, case["calls"])) + 1:
                    raise RuntimeError(
                        "Workload did not execute expected number of requests"
                    )
                if question == "new-sessions":
                    first = next(e for e in model.events if e["turn"] == turn)
                    if first["history_turns"] != [turn]:
                        raise RuntimeError("New session kept earlier turns")
                if turn + 1 in case["checkpoints"]:
                    result["checkpoints"].append(
                        checkpoint(sampler, turn, model, root / "home", assets)
                    )
            if question == "idle":
                idle_started = time.monotonic()
                deadline = idle_started + case["idle_seconds"]
                while time.monotonic() < deadline:
                    if terminal.exited() or model.error:
                        raise RuntimeError(
                            model.error or "Agent exited during idle interval"
                        )
                    time.sleep(min(30, max(0, deadline - time.monotonic())))
                    result["checkpoints"].append(
                        checkpoint(sampler, 0, model, root / "home", assets)
                    )
            if model.error:
                raise RuntimeError(model.error)
            sampler.stop()
            if sampler.error:
                raise RuntimeError(sampler.error)
            result.update(summarize(sampler.samples))
            if terminal.exec_time and model.first_request:
                # From the start of the agent to its first request with the task.
                result["first_request_seconds"] = (
                    model.first_request - terminal.exec_time
                )
            if question == "task":
                # CPU use while the agent works, without the settle or exit.
                first = sampler.samples[0]
                result["active_cpu_percent"] = (
                    100
                    * (active["cpu_usec"] - first["cpu_usec"])
                    / 1e6
                    / (active["time"] - first["time"])
                )
            if result["oom_kills"]:
                raise RuntimeError("Container memory limit killed the agent")
            if question == "idle":
                result["idle"] = summarize(
                    [s for s in sampler.samples if s["time"] >= idle_started]
                )
            result["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - keep failed-run diagnostics
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["steal_seconds"] = steal() - stolen
        if sampler:
            sampler.stop()
            write_samples(folder / "samples.csv", sampler.samples)
        if connections:
            connections.stop()
            result["remote_connections"] = connections.report()
        result["model_requests"] = len(model.events)
        result["stream_deltas"] = model.deltas
        result["tools"] = model.tools
        result["shortened_tool_results"] = len(model.shortened)
        result["compacted_tool_results"] = len(model.compacted)
        result["auxiliary_requests"] = dict(
            Counter(e["kind"] for e in model.auxiliary_events)
        )
        # What each side request was, in short, and every request by path.
        result["auxiliary_model_events"] = model.auxiliary_events
        result["requests_by_path"] = dict(model.paths)
        result["retried_edits"] = model.retried_edits
        # Full request logs are kept only to diagnose failures.
        if result["status"] != "ok":
            result["model_events"] = model.events
            if model.error_details is not None:
                result["diagnostics"] = model.error_details
        model.close()
        save(folder / "result.json", result)
    return result
