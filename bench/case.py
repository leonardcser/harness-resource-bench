"""Run one case: the agent's container, its terminal, the mock model and the
sampler. The host measures the container from outside."""

import json
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

from agents import AGENTS, ENV, ROOT
from host import AGENT_CPUS, canary, quiet, steal
from measure import (
    Connections,
    Sampler,
    Wakeups,
    appears,
    cgroup_for,
    disk,
    files_settled,
    pss,
    session,
    settle,
    summarize,
    write_samples,
)
from model import Model
from terminal import FIRST_PROBE, PROBE, Terminal
from workload import PROMPT, digest, files, marker, steps

SETTLE_SECONDS = 2
# Cases that end by quitting the TUI and timing the exit, after one task and
# after a long session. Startup also quits, at the prompt.
QUIT_AFTER = ("task", "long-session")
# Idle cases save a checkpoint this often. Thread switches are read every
# second between them.
IDLE_CHECKPOINT_SECONDS = 30
# The memory limit of each container. The highest peak of any agent is under
# 1 GiB.
MEMORY = "4g"


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def create(root, image_id, env, frontend, entry, helpers=(), init=False):
    """Create a container on the HOME and workspace in `root`. It runs `entry`
    when it is attached, with the `helpers` of container/ in /tmp. With
    `init`, a small init passes SIGTERM on to the agent, which as PID 1 would
    ignore it."""
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
        f"{root / 'home'}:/home/bench:rw",
        "--volume",
        f"{root / 'workspace'}:/workspace:rw",
        "--volume",
        f"{root / 'fixtures'}:/workspace/fixtures:ro",
    ]
    if init:
        command += ["--init"]
    if frontend == "tui":
        command += ["--tty"]
    for key, value in {**ENV, **env}.items():
        command += ["--env", f"{key}={value}"]
    for name in helpers:
        command += ["--volume", f"{ROOT / 'container' / name}:/tmp/{name}:ro"]
    command += [image_id, *entry]
    return subprocess.check_output(command, text=True).strip()


def launched(args):
    """The command that marks the exec of a launch, and its helper."""
    return ["python3", "/tmp/launch.py", *args], ("launch.py",)


def entry(question, frontend, args, server=False):
    """The command of a case's container, and the helpers that it runs. For an
    agent with a shared `server`, the startup first runs an earlier session."""
    if question == "startup":
        if server:
            return ["python3", "/tmp/warm.py", *args], ("launch.py", "warm.py")
        return launched(args)
    if question == "start-memory":
        command = 'python3 /tmp/evict.py && exec "$@" </dev/null'
        return ["bash", "-c", command, "cold", *args], ("evict.py",)
    if frontend == "headless":
        # The shell keeps the cgroup alive after the agent exits and reports its status.
        # It marks the wall clock just before it starts the agent, with a builtin, so
        # no extra process runs in the measured cgroup.
        command = (
            'printf "\\033]777;BENCH_EXEC=%s\\a" "$EPOCHREALTIME"; "$@" </dev/null;'
            ' rc=$?; printf "\\nBENCH_EXIT_%s\\n" "$rc"; read -r _; exit "$rc"'
        )
        return ["bash", "-c", command, "supervisor", *args], ()
    return args, ()


def launch_once(root, image_id, env, agent, model, log):
    """Launch the agent in its TUI for the first time, wait until it is done
    with its setup, and quit, as on an earlier day. Its files stay in the HOME
    and workspace in `root`, and the page cache keeps what it read. Return its
    startup time and what it left, for the result. The model then forgets it."""
    home = root / "home"
    configured = disk(home)
    command = launched(agent.command("tui", []))
    container = create(root, image_id, env, "tui", *command, init=True)
    try:
        terminal = Terminal(container, log)
        try:
            readiness = terminal.input_ready(token=FIRST_PROBE)
            terminal.erase(FIRST_PROBE)
            terminal.settle()
            # Only the next launch types PROBE, so any here is the agent's own,
            # and would pass for the echo of the next probe
            if PROBE in terminal.text():
                raise RuntimeError(f"Agent draws {PROBE} itself; see first-launch.log")
            if agent.background_setup:
                appears(home / agent.background_setup)
            files_settled(home)
            # As the end of a day, at logout: SIGTERM to every process, such as
            # a shared server, then SIGKILL after 5 seconds.
            quit_started = time.monotonic()
            subprocess.run(
                ["podman", "exec", container, "kill", "-TERM", "--", "-1"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                ["podman", "stop", "--time", "5", container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            quit_seconds = time.monotonic() - quit_started
        finally:
            terminal.close()
    finally:
        subprocess.run(
            ["podman", "rm", "--force", container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    # What the agent writes as it quits.
    files_settled(home)
    if model.error:
        raise RuntimeError(f"First launch: {model.error}")
    if model.events:
        raise RuntimeError("First launch sent a workload request")
    after = disk(home)
    left = {
        "first_launch_seconds": readiness["input_ready_seconds"],
        "first_launch_probe": readiness["probe"],
        "first_launch_bytes": after["disk_bytes"] - configured["disk_bytes"],
        "first_launch_dirs": {
            d: size - configured["disk_dirs"].get(d, 0)
            for d, size in after["disk_dirs"].items()
        },
        "first_launch_requests": dict(model.paths),
        # 5 or more mean that the agent ignored SIGTERM.
        "first_launch_quit_seconds": quit_seconds,
    }
    model.forget()
    return left


def checkpoint(sampler, turn, model, home, before):
    """A sample of the agent and of what its session added to the disk since
    `before`."""
    # Sample without launching helpers in the measured container.
    sample = sampler.sample()
    sample.update(pss(sampler.cgroup))
    now = disk(home)
    sample.update(session(now, before))
    sample["disk_bytes"] = now["disk_bytes"]
    sample["disk_dirs"] = now["disk_dirs"]
    sample["completed_turns"] = turn + 1
    sample["request_bytes"] = model.events[-1]["request_bytes"]
    sample["request_history_turns"] = model.events[-1]["history_turns"]
    return sample


def quit_seconds(terminal, container, pid, agent):
    """Wait until the agent's CPU settles, then time how long it takes to quit.
    A quit counts only if the agent exits with status 0, so that a crash does
    not pass for a fast quit."""
    settle(cgroup_for(pid))
    seconds = terminal.quit(pid)
    status = subprocess.check_output(["podman", "wait", container], text=True)
    if status.strip() != "0":
        raise RuntimeError(f"Agent quit with exit status {status.strip()}")
    return seconds


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


def execute(case, folder, image_id, smoke=False, keep_home=False):
    """Measure `case` and save its result in `folder`. With `keep_home`, copy
    the agent's HOME to `folder/home` once the container is gone."""
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
        "quiet_seconds": quiet(),
        "canary_seconds": canary(),
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
            home = root / "home"
            home.mkdir()
            (root / "workspace" / "fixtures").mkdir(parents=True)
            model.workspace = root / "workspace"
            if keep_home:
                # Runs after the container is removed, before the folder is.
                kept = folder / "home"
                shutil.rmtree(kept, ignore_errors=True)
                resources.callback(shutil.copytree, home, kept, symlinks=True)
            env = agent.configure(home, f"http://127.0.0.1:{model.port}")
            log = folder / "first-launch.log"
            result.update(launch_once(root, image_id, env, agent, model, log))
            before = disk(home)
            prompt = [] if question == "startup" else [PROMPT.format(turn=0)]
            args = agent.command(case["frontend"], prompt)
            container = create(
                root,
                image_id,
                env,
                case["frontend"],
                *entry(question, case["frontend"], args, agent.server),
                # As the first launch, so that both times compare.
                init=question == "startup",
            )
            # The case is over by then: kill at once, as an agent that is PID 1
            # ignores SIGTERM, and podman would wait 10 seconds for it.
            resources.callback(
                subprocess.run,
                ["podman", "rm", "--force", "--time", "0", container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
            )
            terminal = Terminal(container, folder / "terminal.log")
            resources.callback(terminal.close)
            if question == "startup":
                readiness = terminal.input_ready()
                # Only the first launch typed FIRST_PROBE, so any here is the
                # agent's own, and could have passed for the echo of that probe
                if FIRST_PROBE in terminal.text():
                    raise RuntimeError(
                        f"Agent draws {FIRST_PROBE} itself; see terminal.log"
                    )
                (folder / "startup-screen.txt").write_text(readiness.pop("screen"))
                result.update(readiness)
                pid = container_pid(container, terminal)
                # The agent takes in all of the probe before the deletes, so
                # that they do not come in one burst with it, like a paste.
                settle(cgroup_for(pid))
                terminal.erase(PROBE)
                result["quit_seconds"] = quit_seconds(terminal, container, pid, agent)
                result["status"] = "ok"
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
            # The model holds the first request while the agent finishes its
            # startup, so that startup work stays out of every measurement.
            result["settle_seconds"] = settle(cgroup_for(pid))
            if question == "start-memory":
                # The agent waits for its first reply; the model never sends it.
                result.update(pss(cgroup_for(pid)), status="ok")
                return result
            sampler = Sampler(cgroup_for(pid))
            sampler.samples.append(sampler.sample())
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
                        checkpoint(sampler, turn, model, home, before)
                    )
            if question == "idle":
                idle_started = time.monotonic()
                deadline = idle_started + case["idle_seconds"]
                switches = Wakeups(sampler.cgroup)
                result["checkpoints"][-1]["wakeups"] = 0
                mark = idle_started + IDLE_CHECKPOINT_SECONDS
                while time.monotonic() < deadline:
                    if terminal.exited() or model.error:
                        raise RuntimeError(
                            model.error or "Agent exited during idle interval"
                        )
                    time.sleep(min(1, max(0, deadline - time.monotonic())))
                    count = switches.read()
                    if time.monotonic() >= min(mark, deadline):
                        point = checkpoint(sampler, 0, model, home, before)
                        result["checkpoints"].append(dict(point, wakeups=count))
                        mark += IDLE_CHECKPOINT_SECONDS
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
            if question in QUIT_AFTER and case["frontend"] == "tui":
                result["quit_seconds"] = quit_seconds(terminal, container, pid, agent)
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
