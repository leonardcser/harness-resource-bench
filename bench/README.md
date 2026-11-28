# Benchmark

Seven coding agents get the same scripted work: smelt, pi, omp, codex, Claude
Code, opencode and fx. The benchmark measures what each costs the machine:
startup time, memory, CPU time, session data on disk and install size.

## How it works

```
 harness core, CPUs 0-1                    container, CPUs 2-5, 4 GiB
┌──────────────────┐   next tool call    ┌───────────────────────┐
│ mock model       │ ──────────────────▶ │ real agent, pinned    │
│ model/           │ ◀────────────────── │ version, TUI or       │──▶ /workspace
│ checks results   │    tool result      │ headless              │
└──────────────────┘                     └───────────────────────┘
 sampler: reads the container's cgroup every 100 ms        (measure.py)
 terminal: a tmux pane that types prompts and waits for the done marker
                                                           (terminal.py)
```

1. A local **mock model** replies like a real provider. Each reply asks for one
   tool call. The last reply of a turn prints a done marker.
2. The **agent** runs each call for real, with its own tools, in its own
   container. The model checks every result, so an agent cannot skip work.
3. The **host** measures the container from outside. It runs nothing inside.

The work comes from a seed, so every agent gets the same work. Its shape comes
from real sessions. To see it: `uv run bench.py transcript > transcript.json`.

## What it measures

| Name            | Case id        | What it measures                                                                         |
| --------------- | -------------- | ---------------------------------------------------------------------------------------- |
| Startup         | `startup`      | Time from exec until a typed key shows in the TUI, at the first and a warm launch        |
| Headless start  | `task`         | Time from exec until the first request with the task, headless, with flags               |
| Memory at start | `start-memory` | Memory (PSS) once the agent settles after its first request, headless, cold file cache   |
| Install size    | -              | Bytes that the install adds under `/root`, `/usr/local` and `/opt`                       |
| Coding task     | `task`         | CPU and memory of a task with 24 tool calls, headless at 60 tokens/s, TUI at 30 to 1,000 |
| Long session    | `long-session` | Memory, CPU per turn and session data over 64 turns                                      |
| New sessions    | `new-sessions` | Memory over 16 sessions in one process                                                   |
| Idle            | `idle`         | CPU and memory over 5 minutes without input, after a task                                |
| Quit            | -              | Time to quit the TUI at the end of `startup`, `task` and `long-session`                  |

- Every case starts in a HOME that a first launch used, as on a user's machine.
  The HOME is on disk, in `/var/tmp`, not in a tmpfs.
- TUI cases also measure the CPU time that the terminal (tmux) spends.
- Every case runs 3 times. Startup and memory at start run 10 times. Results
  show the median and the range.

## Run it

Requirements: Linux, rootless podman, cgroup v2 with `cpu`, `cpuset`, `memory`
and `pids` delegated to the user, tmux, [uv](https://docs.astral.sh/uv/), and
CPUs 0 to 5. On a fresh Ubuntu VM, `./setup.sh` sets this up. `run` checks the
host and tells you what is missing.

Published runs come from [the benchmark VM](docs/vm.md). Elsewhere, use an idle
machine.

```sh
uv run bench.py run          # all agents, about 8.5 hours
uv run bench.py run omp      # one agent
uv run bench.py check omp    # build and run the setup check only
```

`run` does three steps:

1. **Build:** it builds one image per agent, at the version of its recipe, with
   the official installer frozen in `installers/`.
2. **Check:** it runs one short case per question (`smoke/`), which uses every
   tool kind. It stops if a check fails.
3. **Measure:** it runs all cases, then replays the terminal logs.

Good to know:

- **Output:** `results/DATE`, or `results/DATE-AGENTS` for some agents. `check`
  writes to `results/check`, in place of the previous check.
- **One session:** a run has no resume, so all its cases come from one session.
  A measured case that fails stops the run, which stays in its folder. The setup
  check runs all its cases, then names the failed ones.
- **Code:** if `bench/` has no changes, `run` records the commit. Only such a
  run can be published.
- **Installers:** `installers/` holds each agent's official installer, frozen at
  its version, so an old commit installs as its run did. When a version changes,
  `check` freezes the new installer; commit it.
- **Local build:** `--local-binary AGENT=PATH` installs a local build of an
  agent that ships as one binary.
- **Release:** [RELEASE.md](../RELEASE.md) gives every step, from the version
  bump to the published results.

Each run writes:

| File            | Contents                                                      | Commit? |
| --------------- | ------------------------------------------------------------- | ------- |
| `manifest.json` | Commit, versions, images, limits, plan, machine               | Yes     |
| `summary.json`  | Median, min and max per agent, question and setting           | Yes     |
| `profile.json`  | The workload profile of the run                               | Yes     |
| `cases/ID/`     | The result, the 100 ms resource timeline and the terminal log | No      |

Never commit session stores, credentials or private history.

## Add an agent

An agent is a TOML recipe in `agents/`: version, install command, config files,
commands and tool calls. Copy the closest recipe, for example `agents/pi.toml`,
and change it. [`agents/agent.py`](agents/agent.py) lists the fields and
placeholders, and the loader rejects an unknown field. A Python file of the same
name beside the recipe holds what a template cannot say (`omp.py`).

To measure it without adding it to the repository, and only it:

```sh
uv run bench.py check --recipe mine.toml   # build, freeze the installer, setup check
uv run bench.py run --recipe mine.toml
```

Such a run records no commit, so it cannot be published.

## Reproduce a run

On a fresh Ubuntu VM with 6 CPUs or more:

```sh
git checkout COMMIT       # the "commit" in results/ID/manifest.json
cd bench && ./setup.sh    # once; then log out and in again
uv run bench.py run
```

The commit holds the code, versions and installers of run ID. Your machine gives
other numbers, but the order of the agents should hold.

## Code

Each agent's recipe in `agents/` holds everything about it. The rest of the code
knows no agent.

| File                  | Role                                                      |
| --------------------- | --------------------------------------------------------- |
| `bench.py`            | The CLI, the run folder and the loop over the cases       |
| `plan.py`             | Which cases a run measures, and in what order             |
| `case.py`             | Runs one case: container, terminal, model and sampler     |
| `report.py`           | Summaries and the terminal replay                         |
| `host.py`             | Host checks, CPUs, steal time and machine info            |
| `proxmox/`            | The hook that reserves the benchmark VM's cores           |
| `agents/NAME.toml`    | Version, install, config, tool calls and request texts    |
| `agents/agent.py`     | The format of a recipe, and how it becomes an agent       |
| `model/server.py`     | The mock model server and its checks                      |
| `model/requests.py`   | What a request holds: history, results, compaction        |
| `model/formats.py`    | The three API formats of the replies                      |
| `workload/`           | Generates the work from a seed and `profile.json`         |
| `workload/fit.py`     | Makes `profile.json` from smelt session stores            |
| `terminal.py`         | The tmux pane, the startup probe and the terminal replay  |
| `measure.py`          | Reads CPU, memory, disk and network from the host         |
| `images.py`           | Freezes the installers and builds the images              |
| `installers/`         | The frozen installer of each agent                        |
| `setup.sh`            | Prepares a fresh Ubuntu VM                                |
| `container/launch.py` | In the container: marks the exec time of a launch         |
| `container/warm.py`   | In the container: an earlier session before a launch      |
| `container/evict.py`  | In the container: empties the file cache for start-memory |

Lint: `uv run ruff check .`

## Details

- [Fairness](docs/fairness.md): what keeps the comparison fair
- [The benchmark VM](docs/vm.md): the machine that publishes runs
- [Workload](docs/workload.md): the scripted work and its tool calls
- [Mock model](docs/mock-model.md): the model, its replies and the agent quirks
- [Measurement](docs/measurement.md): how each number is read from the host
