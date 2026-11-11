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

| Name            | Case id        | What it measures                                                                          |
| --------------- | -------------- | ----------------------------------------------------------------------------------------- |
| Startup         | `startup`      | Time from exec until a typed key shows in the TUI                                         |
| Memory at start | `start-memory` | Memory (PSS) after the first request, headless, with a cold file cache                    |
| Install size    | -              | Bytes that the install adds under `/root`, `/usr/local` and `/opt`                        |
| Coding task     | `task`         | CPU and memory of a task with 24 tool calls, headless at 120 tokens/s, TUI at 30 to 1,000 |
| Long session    | `long-session` | Memory, CPU per turn and session data over 64 turns                                       |
| New sessions    | `new-sessions` | Memory over 16 sessions in one process                                                    |
| Idle            | `idle`         | CPU and memory over 5 minutes without input, after a task                                 |

- TUI cases also measure the CPU time that the terminal (tmux) spends.
- Every case runs 3 times. Startup and memory at start run 10 times. Results
  show the median and the range.

## Run it

Requirements: Linux, rootless podman, cgroup v2 with `cpu`, `cpuset`, `memory`
and `pids` delegated to the user, tmux, [uv](https://docs.astral.sh/uv/), and
CPUs 0 to 5. On a fresh Ubuntu VM, `./setup.sh` sets this up. `run` checks the
host and tells you what is missing.

Published runs come from [the benchmark VM](#the-benchmark-vm). Elsewhere, use
an idle machine.

```sh
uv run bench.py run          # all agents, about 8.5 hours
uv run bench.py check omp    # build and run the setup check only
```

`run` does three steps:

1. **Build:** it builds one image per agent, at the version in `agents/`, with
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
  run can be frozen for the site.
- **Installers:** `installers/` holds each agent's official installer, frozen at
  its version, so an old commit installs as its run did. When a version changes,
  `check` freezes the new installer; commit it.
- **Kept homes:** `--keep-homes` copies each case's HOME to `cases/ID/home`, for
  the [recipes](../RELEASE.md#recipes). Never commit it.
- **Local build:** `--local-binary AGENT=PATH` installs a local build of an
  agent that ships as one binary.
- **Release:** [RELEASE.md](../RELEASE.md) gives every step, from the version
  bump to the site.

Each run writes:

| File            | Contents                                                      | Commit? |
| --------------- | ------------------------------------------------------------- | ------- |
| `manifest.json` | Commit, versions, images, limits, plan, machine               | Yes     |
| `summary.json`  | Median, min and max per agent, question and setting           | Yes     |
| `profile.json`  | The workload profile of the run                               | Yes     |
| `cases/ID/`     | The result, the 100 ms resource timeline and the terminal log | No      |

Never commit session stores, credentials or private history.

## Reproduce a run

On a fresh Ubuntu VM with 6 CPUs or more:

```sh
git checkout COMMIT       # the "commit" in results/ID/manifest.json
cd bench && ./setup.sh    # once; then log out and in again
uv run bench.py run
cd ../web && RUN=ID bun run dev  # ID: the folder that run made in results/
```

The commit holds the code, versions and installers of run ID. Your machine gives
other numbers, but the order of the agents should hold.

## Code

Each agent's file in `agents/` holds everything about it. The rest of the code
knows no agent.

| File                  | Role                                                      |
| --------------------- | --------------------------------------------------------- |
| `bench.py`            | The CLI, the run folder and the loop over the cases       |
| `plan.py`             | Which cases a run measures, and in what order             |
| `case.py`             | Runs one case: container, terminal, model and sampler     |
| `report.py`           | Summaries and the terminal replay                         |
| `host.py`             | Host checks, CPUs, steal time and machine info            |
| `proxmox/`            | The hook that reserves the benchmark VM's cores           |
| `agents/NAME.py`      | Version, install, config, tool calls and request texts    |
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
| `container/evict.py`  | In the container: empties the file cache for start-memory |

Lint: `uv run ruff check .`

## Details

### Fairness

- **Install:** each agent's official installer, frozen in `installers/`.
- **Limits:** per container, 4 CPUs (two physical cores), 4 GiB of memory, no
  swap and 512 processes. No agent peaks above 1 GiB.
- **State:** a new HOME, dummy credentials and no personal state.
- **CPUs:** the agent runs on CPUs 2 to 5, the harness on CPUs 0 and 1. One case
  runs at a time. In a test, 4 neighbours on the same CCD added 6% to 8% CPU,
  against under 1% of noise.
- **Order:** each repeat shuffles the agents, with a fixed seed.
- **Defaults:** each agent runs with its defaults, except:
  - telemetry, error reports and automatic updates are off (`ENV` in
    `agents/__init__.py`). Other requests stay on, such as session titles.
  - approvals and the sandbox are off, so the run needs no person.
  - opencode runs with `--standalone` and codex with `--no-daemon`. Their
    default shared server would stay after quit.
- **Context window:** 200k tokens for every agent. codex also gets the tool
  output limit of its real models (`tool_output_token_limit`), because it does
  not know the mock model.
- **Warmup:** one practice task per agent and frontend, which does not count.

### The benchmark VM

A VM with 12 vCPUs on a Proxmox host with an AMD Ryzen 9 7900X (12 cores in two
CCDs, each with its own L3). The hook `proxmox/bench-isolate` runs when the VM
starts and stops. While the VM runs:

- **Reserved cores:** the VM owns the whole second CCD (host threads 6 to 11 and
  18 to 23). No other guest or host service runs there.
- **Own L3:** no other work shares that cache.
- **Pinning:** each vCPU runs on one host thread. Each pair 2k, 2k+1 is one
  physical core. QEMU's threads share the core of vCPUs 0 and 1, where the
  harness runs.
- **Fixed clock:** the reserved cores stay at 4.7 GHz, the base clock.
- **Interrupts:** hardware interrupts go to other host threads. NVMe queues fire
  there only for the VM's own I/O.
- **Updates:** off, so packages do not change between runs.

### Workload

`workload/` generates reasoning, text and tool calls from a seed.
`workload/profile.json` sets their shape with aggregate numbers only:

- quantiles of tool calls per turn
- the share of each tool kind, and quantiles of its argument and result bytes
- the share of calls with reasoning or text, and quantiles of their bytes
- the same for the answer at the end of a turn

About the profile:

- **Source:** the maintainer's smelt sessions. They average 23 tool calls per
  turn, and a few turns have hundreds.
- **Rebuild:** `uv run --group fit workload/fit.py > workload/profile.json`
- **Record:** each run keeps a copy.
- **Sizes:** the bytes that the model saw. A result that the agent cut counts at
  its cut size.
- **Parallel calls:** the mock model serves one call per response. A response
  with parallel calls becomes several steps. Its reasoning and text go on the
  first.
- **Draws:** between the quantile points in log space, up to the 99.9th
  percentile.

The coding task and idle always make 24 calls. The long session and new sessions
take the calls of each turn from the profile. 64 turns hold about as much as the
98th percentile of real sessions.

#### Tool calls

Each call uses the agent's own tool for its kind, or its shell tool if it has
none, as in real use. Each agent's `call` in `agents/` writes them. The model
checks that the tool is on offer, with every required argument.

| Kind   | smelt        | pi      | omp     | codex          | claude code | opencode | fx           |
| ------ | ------------ | ------- | ------- | -------------- | ----------- | -------- | ------------ |
| shell  | `bash`       | `bash`  | `bash`  | `exec_command` | `Bash`      | `shell`  | `shell`      |
| read   | `read_file`  | `read`  | `read`  | shell          | `Read`      | `read`   | `read_file`  |
| edit   | `edit_file`  | `edit`  | `edit`  | shell          | `Edit`      | `edit`   | `edit_file`  |
| write  | `write_file` | `write` | `write` | shell          | `Write`     | `write`  | `write_file` |
| search | `grep`       | shell   | `grep`  | shell          | shell       | `grep`   | `grep_files` |

| Kind   | What it does                                    | Through the shell |
| ------ | ----------------------------------------------- | ----------------- |
| shell  | Prints a fixture with build, test and git lines | -                 |
| read   | Opens a source file                             | `cat -n`          |
| search | Prints the lines of a source file that match    | `grep -n`         |
| edit   | Replaces a block in a file that the turn read   | `apply_patch`     |
| write  | Creates a file                                  | `apply_patch`     |

Each result records the tool used for each kind under `tools`.

### Mock model

**Protocol**

- It streams the Chat Completions, Responses or Anthropic Messages format, 32
  bytes per delta.
- One token is 4 bytes, not a provider's tokenizer count. Usage reports this
  count.
- It rejects a request over 200k tokens with the protocol's context-length
  error.

**Checks** on every tool result, call ID, turn history and request count:

- A missing, failed or unrelated result fails the run.
- The host checks that every edit and write changed the file.
- An agent can cut a large result in its history if it keeps the first line.
  `shortened_tool_results` counts these.
- In new sessions, the first request of each session must hold no earlier turn.

**Side requests and compaction**

- Side requests, such as session titles, get a short fixed answer.
- The model knows each agent's compaction prompts (`summaries` in its file) and
  gives every agent the same summary. So the long session measures how the agent
  compacts, not the quality of the summary.
- The model checks the tool output in a compaction request before it can replace
  the original.
- An agent can compact before it sends a result. `compacted_tool_results` counts
  these.
- A side request with results from several turns but no known compaction prompt
  fails the run.

**Records** per case: each side request in short (path, model, tools, start of
its prompts), the rejected requests under `auxiliary_requests`, and a count of
all requests by path.

#### Agent quirks

These live in each agent's file in `agents/`.

- **omp** edits with hashline patches.
  - The file tag comes from the newest read or edit result. The line numbers
    come from the file on the host.
  - omp refuses a body that starts with the line above the range. The range then
    covers that line too, and the body keeps it.
  - When omp refuses an edit and asks for a retry, the model sends it once more
    (`retried_edits`).
- **fx**
  - Its TUI takes no prompt argument, so the harness types the first prompt when
    the screen is stable.
  - It writes its history to the terminal scrollback, not to an alternate
    screen.
  - Its compaction asks for notes under each turn heading, and asks again if one
    is missing. So the summary repeats the headings.
- **Claude Code** keeps its session-title requests, because users make them too.

### Measurement

**CPU and memory**

- The host reads the container's cgroup every 100 ms.
- CPU seconds come from cgroup deltas. 100% is one core.
- Memory is PSS: the sum over all processes in the cgroup, with shared pages
  split between them.
- TUI cases record PSS at checkpoints, after 2 seconds of settle time. Idle runs
  split it into file pages (mostly code) and anonymous pages (heap).
- `idle_wakeups_per_second`: voluntary context switches of all the agent's
  threads, per second of idle.
- `quiet_seconds`: how long the host waited before the case for the agent's CPUs
  to stay idle for 0.5 s, at most 30 s.
- `peak_memory_bytes`: the cgroup's own peak, with file cache.
- `canary_seconds`: the CPU time of a fixed hash of 4 MiB on CPU 2, just before
  the case. `summary.json` gives its spread under `canary`. A clock change or a
  neighbour on the agent's cores shows there.
- `steal_seconds`: the time the hypervisor ran something else on the agent's
  CPUs. On the benchmark VM it stays near zero.
- `active_cpu_percent`: the CPU of the coding task, divided by the time from the
  first request to the done marker. It compares across streaming rates.

**Startup**

- `launch.py` writes a monotonic timestamp just before the agent's `exec`, with
  kernel echo off.
- The host types a probe every 5 ms and measures the time until its echo.
  Differences below 5 ms are not resolved.
- The terminal is a tmux pane of 120 by 40, with a dark theme. tmux answers the
  agent's capability queries, as it does for users.
- `first_request_seconds`: the time from the exec to the first request with the
  task.

**End of a turn:** the agent draws its done marker. A renderer can split the
marker across frames, so when the output stops, the harness also checks the
screen.

**Disk**

- `disk_bytes`: the size of all files in the agent's HOME, a host folder mounted
  into the container. `disk_dirs` gives it per folder.
- `session_bytes`: the same without each agent's `assets` in `agents/`. These
  are plugins, grammars and bundled files that the agent downloads or unpacks in
  every session. They do not grow with the session, and `disk_bytes` still
  counts them. The long session reports `session_bytes_after_N`.
- `session_files` counts those files. `session_<kind>_bytes` splits the bytes by
  format: `sqlite`, `wal` (SQLite `-wal`, `-shm`, `-journal`), `jsonl`, `json`
  and `other`.
- `session_text_bytes`: the text of the session itself (tool calls, tool output
  and answers).

**Terminal:** its work does not count against the agent's container.

- After the last case, the host replays each TUI case's `terminal.log` into a
  new tmux of the same size, with a million lines of scrollback.
- The replays run one at a time on CPU 2, 5 times each.
- `terminal_cpu_seconds`: the lowest CPU time of the tmux server, because noise
  only adds time. It covers parsing and keeping the output, not drawing it.
- `terminal_bytes`: the size of the log.
- tmux memory is not recorded. It depends on how tmux stores cells, not on the
  agent.

**Network:** containers use the host network, so an agent can reach other hosts.
These requests are part of the agent's cost, so they stay on.

- Every case except startup records them under `remote_connections`, and
  `summary.json` lists them per agent.
- The host reads the sockets of the agent's processes from `/proc` every 200 ms.
  A connection that opens and closes between two reads is missed.
- DNS lookups and loopback addresses, such as the model, are not recorded.

At the versions in `agents/`:

| Agent       | Hosts                       | What it fetches                  |
| ----------- | --------------------------- | -------------------------------- |
| claude code | `api.anthropic.com`         | The registry of MCP servers      |
|             | `raw.githubusercontent.com` | The changelog, in the TUI        |
|             | `downloads.claude.ai`       | The official plugin marketplace  |
| codex       | `github.com`                | The plugin catalog               |
|             | `chatgpt.com`               | Its backend, in some TUI cases   |
| omp         | About 10 providers          | Their catalogs of models         |
| opencode    | `models.opencode.ai`        | The catalog of models            |
|             | GitHub                      | Grammars for syntax highlighting |

omp asks, among others, `api.anthropic.com`, `api.openai.com`, Alibaba
DashScope, ZenMux, Venice, Command Code, Stencil and the Vercel AI Gateway.

**Valid samples:** a sample is invalid only when the work fails, for example an
OOM kill, a tool error, an unexpected request or a changed image. Throttling is
recorded, but it does not make a sample invalid.
