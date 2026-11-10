# Benchmark

Seven coding agents get the same scripted work. The benchmark measures what each
one costs the machine: startup time, memory, CPU time, session data on disk and
install size.

Agents: smelt, pi, omp, codex, Claude Code, opencode and fx.

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
2. The **agent** runs each call for real, with its own tools, in a new
   container. The model checks every result, so an agent cannot skip work.
3. The **host** measures the container from outside. It never runs anything in
   the container.

- The work comes from a seed, so every agent gets the same work.
- Its shape (calls per turn, tool kinds, sizes) comes from real sessions.
- To see it: `uv run bench.py transcript > transcript.json`

## What it measures

| Name            | Case id        | What it measures                                                                            |
| --------------- | -------------- | ------------------------------------------------------------------------------------------- |
| Startup         | `startup`      | Time from exec until a typed key shows in the TUI                                           |
| Memory at start | `start-memory` | Memory (PSS) after the first request, with a cold file cache, headless                      |
| Install size    | -              | Bytes that the install adds under `/root`, `/usr/local` and `/opt`                          |
| Coding task     | `task`         | CPU and memory of one task with 24 tool calls. Headless at 120 tokens/s, TUI at 30 to 1,000 |
| Long session    | `long-session` | Memory, CPU per turn and session data on disk over 64 turns                                 |
| New sessions    | `new-sessions` | Memory over 16 sessions in one process, each started with the agent's new-session command   |
| Idle            | `idle`         | CPU and memory during 5 minutes without input, after a task                                 |

- TUI cases also measure the CPU time that a real terminal (tmux) spends to
  parse the agent's output.
- Every case runs 3 times, and startup and memory at start 10 times. One
  container runs at a time, with the agents in random order. Results show the
  median and the range.

## Run it

Requirements: Linux, rootless podman, cgroup v2 with `cpu`, `cpuset`, `memory`
and `pids` delegated to the user, tmux, [uv](https://docs.astral.sh/uv/), and
CPUs 0 to 5. `run` checks the host first and tells you what is missing.

The host for published results is the benchmark VM. While it runs, a Proxmox
hook reserves its cores on the host (see [The benchmark VM](#the-benchmark-vm)).
On another host, use an idle machine.

```sh
uv run bench.py run          # all agents, about 8.5 hours
uv run bench.py check omp    # build and run the setup check only
uv run bench.py publish      # publish the newest complete run again
```

`run` does these steps:

1. **Build:** it saves the official installer of each agent and builds one image
   per agent, at the version in its file in `agents/`.
2. **Check:** it runs one short case per question (`smoke/`). The coding task of
   the check uses every tool kind once at least. If a check fails, it stops.
3. **Measure:** it runs all cases, then replays the terminal logs to measure the
   terminal.
4. **Publish:** when the run covers all agents, it names the run in
   `results/published.json`. The site shows that run.

Good to know:

- **Output:** `results/DATE` at the root of the repository, or
  `results/DATE-AGENTS` for some agents.
- **Resume:** run the same command again. It continues the newest unfinished run
  of the same agents. If the code, a version or the local build changed, it
  starts a new run.
- **Failures:** a failed case stops the run and stays in `cases/ID/` for you to
  examine. Delete that folder to run the case again.
- **Kept homes:** `--keep-homes` copies each case's HOME to `cases/ID/home`, for
  [ANALYSIS.md](ANALYSIS.md). Never commit it.
- **Local build:** for an agent that ships as one binary, add
  `--local-binary AGENT=PATH`.

Each run writes:

| File            | Contents                                                      | Commit? |
| --------------- | ------------------------------------------------------------- | ------- |
| `manifest.json` | Code digest, versions, images, limits, plan and machine       | Yes     |
| `summary.json`  | Median, min and max per agent, question and setting           | Yes     |
| `profile.json`  | The workload profile that the run used                        | Yes     |
| `cases/ID/`     | The result, the 100 ms resource timeline and the terminal log | No      |

Also commit `results/published.json`. Never commit session stores, credentials
or private history.

## Update an agent

Change `version` in its file in `agents/`, then run all agents again. The site
shows one run only, so every agent is measured in the same session on the same
host. A run of some agents is for testing; it does not publish.

## Code

Everything about one agent is in its file in `agents/`. The rest of the code
knows no agent.

| File                  | Role                                                      |
| --------------------- | --------------------------------------------------------- |
| `bench.py`            | The CLI, the run folder and the loop over the cases       |
| `plan.py`             | Which cases a run measures, and in what order             |
| `case.py`             | Runs one case: container, terminal, model and sampler     |
| `report.py`           | Summaries, the terminal replay and publishing             |
| `host.py`             | Host checks, CPUs, steal time and machine info            |
| `proxmox/`            | The hook that reserves the benchmark VM's cores           |
| `agents/NAME.py`      | Version, install, config, tool calls and request texts    |
| `model/server.py`     | The mock model server and its checks                      |
| `model/requests.py`   | What a request holds: history, results, compaction        |
| `model/formats.py`    | The three API formats of the replies                      |
| `workload/`           | Generates the work from a seed and `profile.json`         |
| `terminal.py`         | The tmux pane, the startup probe and the terminal replay  |
| `measure.py`          | Reads CPU, memory, disk and network from the host         |
| `images.py`           | Saves the installers and builds the images                |
| `container/launch.py` | In the container: marks the exec time for startup         |
| `container/evict.py`  | In the container: empties the file cache for start-memory |
| `workload/fit.py`     | Makes `profile.json` from smelt session stores            |

Lint: `uv run ruff check .`

## Details

Reference material, to check the method or change the harness.

### Fairness

- **Install:** the official installer of each agent. `run` saves it in
  `installers/`, so a resumed run builds the same image.
- **Limits:** 4 CPUs (two physical cores with both threads), 4 GiB of memory, no
  swap and 512 processes per container. The highest peak of any agent is under 1
  GiB.
- **State:** a new HOME, dummy credentials and no personal state.
- **CPUs:** the agent runs on CPUs 2 to 5. The controller, model, sampler and
  terminal run on CPUs 0 and 1. One case runs at a time: in a test with 4
  neighbours on the same CCD, the agents used 6% to 8% more CPU, against under
  1% of noise alone.
- **Order:** each repeat shuffles the agents, with a fixed seed.
- **Defaults:** each agent runs with its defaults. Only telemetry, error
  reporting and automatic updates are off (`ENV` in `agents/__init__.py`). Other
  default requests stay on, such as session titles and catalog downloads.
- **Context window:** 200k tokens for every agent.
- **Warmup:** one practice task per agent and frontend, which does not count.

### The benchmark VM

The published runs come from a VM with 12 vCPUs on a Proxmox host with an AMD
Ryzen 9 7900X: 12 cores in two CCDs, each with its own L3 cache. The hook
`proxmox/bench-isolate` runs when the VM starts and stops. While the VM runs:

- **Reserved cores:** the VM's cgroup is an isolated cpuset partition with the
  whole second CCD (host threads 6 to 11 and 18 to 23). The kernel takes these
  threads away from every other guest and host service, also from guests that
  start later.
- **Own L3:** no other work shares the cache of that CCD.
- **Pinning:** each vCPU runs on one host thread, and each pair 2k, 2k+1 is one
  physical core. QEMU's own threads share the core of vCPUs 0 and 1, so the
  harness runs there and the agent does not.
- **Fixed clock:** the reserved cores are held at 4.7 GHz, the base clock, so
  boost does not change the speed between runs.
- **Interrupts:** hardware interrupts go to the other host threads. NVMe queues
  that the kernel manages keep their affinity, and fire there only for the VM's
  own I/O.
- **Updates:** the VM has no automatic updates, so packages do not change during
  or between runs.

### Workload

`workload/` generates reasoning, assistant text and tool calls from a seed.
`workload/profile.json` sets their shape. It holds only aggregate numbers, never
session text:

- quantiles of tool calls per turn
- the share of each tool kind, and quantiles of its argument and result bytes
- the share of calls with reasoning or text, and quantiles of their bytes
- the same numbers for the answer at the end of a turn

The profile:

- **Source:** the maintainer's own smelt sessions. They average 23 tool calls
  per turn, and a few long turns have hundreds.
- **Rebuild:** `uv run --group fit workload/fit.py > workload/profile.json`
- **Record:** each run keeps a copy of the profile that it used.
- **Sizes:** the bytes that the model saw. A result that the agent cut counts at
  its cut size.
- **Parallel calls:** the mock model serves one call per response. So a response
  with parallel calls becomes one call per step, and its reasoning and text go
  on the first call.
- **Draws:** between the quantile points in log space, up to the 99.9th
  percentile.

Calls per case:

- Coding task and idle: always 24 calls.
- Long session and new sessions: the calls of each turn come from the profile.
  64 turns hold about as much as the 98th percentile of real sessions.

#### Tool calls

Each call uses the agent's own tool for its kind. Without such a tool, it uses
the agent's shell tool, as in real use. Each agent's `call` in `agents/` writes
these out, and the model checks that the tool is on offer with every required
argument:

| Kind   | smelt        | pi      | omp     | codex          | claude code | opencode | fx           |
| ------ | ------------ | ------- | ------- | -------------- | ----------- | -------- | ------------ |
| shell  | `bash`       | `bash`  | `bash`  | `exec_command` | `Bash`      | `shell`  | `shell`      |
| read   | `read_file`  | `read`  | `read`  | shell          | `Read`      | `read`   | `read_file`  |
| edit   | `edit_file`  | `edit`  | `edit`  | shell          | `Edit`      | `edit`   | `edit_file`  |
| write  | `write_file` | `write` | `write` | shell          | `Write`     | `write`  | `write_file` |
| search | `grep`       | shell   | `grep`  | shell          | shell       | `grep`   | `grep_files` |

| Kind   | What it does                                                 | Through the shell |
| ------ | ------------------------------------------------------------ | ----------------- |
| shell  | Prints a prepared fixture with build, test and git lines     | -                 |
| read   | Opens a prepared source file                                 | `cat -n`          |
| search | Opens a prepared source file and prints the lines that match | `grep -n`         |
| edit   | Replaces a block in a file that the turn read before         | `apply_patch`     |
| write  | Creates a file                                               | `apply_patch`     |

Each case result records the tool used for each kind under `tools`.

### Mock model

**Protocol**

- Streams the Chat Completions, Responses or Anthropic Messages format, 32 bytes
  per delta.
- One reference token is 4 bytes, not the count of a provider tokenizer. The
  model reports this count as usage.
- Rejects a request over 200k tokens with the protocol's context-length error.

**Checks** on every tool result, call ID, turn history and request count:

- A missing, failed or unrelated result fails the run.
- The host checks that every edit and write changed the file.
- An agent can cut a large result in its history if it keeps its first line.
  `shortened_tool_results` counts these.
- In new sessions, the first request of each session must have no earlier turn.

**Side requests and compaction**

- Side requests, such as session titles, get a short fixed answer.
- The model knows each agent's compaction prompts (`summaries` in its file) and
  gives all the same structured summary. So the long session measures how the
  client compacts, not the quality of the summary.
- The model checks the tool output in a compaction request before it can replace
  the original.
- An agent can compact before it sends a result. The run continues, and
  `compacted_tool_results` counts these.
- A side request with tool results from several turns but no known compaction
  prompt fails the run.

**Records** per case:

- every side request in short: path, model, tools and the start of its prompts
- the rejected requests, under `auxiliary_requests`
- a count of all requests by path

Check these when an agent changes, to make sure it runs with its default model
requests.

#### Agent quirks

These live in each agent's file in `agents/`.

- **omp** edits with hashline patches.
  - The file tag comes from the newest read or edit result, and the line numbers
    from the file on the host.
  - omp refuses a body that starts with the line above the range. The range then
    also covers that line, and the body keeps it.
  - When omp refuses an edit and asks for a retry, the model sends it once more
    (`retried_edits`).
- **fx**
  - Its TUI takes no prompt argument, so the harness types the first prompt when
    the screen is stable.
  - It writes its history into the terminal scrollback, not into an alternate
    screen.
  - Its compaction asks for notes under each turn heading, and asks again if one
    is missing, so the summary repeats the headings.
- **Claude Code** keeps its session-title requests, because users make them too.

### Measurement

**CPU and memory**

- The host reads the container's cgroup every 100 ms.
- CPU seconds come from cgroup deltas. 100% is one core.
- Memory is PSS: the sum over all processes in the cgroup, with shared pages
  split between them.
- TUI cases record PSS at checkpoints, after 2 seconds of settle time. Idle runs
  split it into file-backed (mostly code) and anonymous (heap) pages.
- `idle_wakeups_per_second`: voluntary context switches of all the agent's
  threads, per second of idle.
- `peak_memory_bytes` is the cgroup's own peak, with file cache.
- `canary_seconds` is the CPU time of a fixed hash of a 4 MiB buffer on CPU 2,
  just before the case. `summary.json` gives its spread over the whole run under
  `canary`. A change of clock or a neighbour on the agent's cores shows there.
- `steal_seconds` is the time that the hypervisor ran something else on the
  agent's CPUs during the case. On the benchmark VM it stays near zero.
- `active_cpu_percent` is the CPU of the coding task divided by the time from
  the first request to the done marker. It compares across streaming rates.

**Startup**

- `launch.py` writes a monotonic timestamp just before the `exec` of the agent,
  with kernel echo off.
- The host types a probe every 5 ms and measures the time until the first echo.
  Differences below 5 ms are not resolved.
- The terminal is a tmux pane of 120 by 40, with a dark theme. tmux answers the
  agent's capability queries, as it does for users.
- `first_request_seconds` is the time from the exec to the agent's first request
  with the task.

**End of a turn:** the agent draws its done marker. A renderer can split the
marker across frames, so when the output stops, the harness also checks the
pane's screen.

**Disk**

- `disk_bytes`: the apparent size of all files in the agent's HOME, a host
  directory mounted into the container. `disk_dirs` gives it per directory.
- `session_bytes`: the same without each agent's `assets` in `agents/`. These
  are plugins, grammars and bundled files that the agent downloads or unpacks in
  every session. The long session reports `session_bytes_after_N`.
- `session_files` counts those files, and `session_<kind>_bytes` splits them by
  format: `sqlite`, `wal` (SQLite `-wal`, `-shm`, `-journal`), `jsonl`, `json`
  and `other`. `session_text_bytes` is the text of the session itself: tool
  calls, tool output and answers.
- The excluded folders have a fixed size that does not grow with the session,
  and `disk_bytes` still counts them:

| Agent       | Folder                        | What it holds                                        | Size in the long session |
| ----------- | ----------------------------- | ---------------------------------------------------- | ------------------------ |
| codex       | `.codex/.tmp`                 | The plugin catalog that codex downloads at start     | 84 MB                    |
| codex       | `.codex/skills/.system`       | The built-in skills that codex unpacks at start      | 0.3 MB                   |
| claude-code | `.claude/plugins`             | The official plugin marketplace, cloned at start     | 15 MB                    |
| opencode    | `.local/share/opentui`        | The syntax grammars that the TUI downloads           | 1.1 MB                   |
| smelt       | `.local/share/smelt/builtins` | The built-in Lua plugins that smelt unpacks at start | 1.2 MB                   |
| omp         | `.omp/natives`                | The native modules that omp unpacks at start         | 129 MB                   |

**Terminal:** the terminal's work does not count against the agent's container.

- After the last case, the host replays the `terminal.log` of each TUI case into
  a new detached tmux of the same size, with a million lines of scrollback.
- The replays run one at a time on CPU 2, and parse each log 5 times.
- `terminal_cpu_seconds` is the lowest CPU time of its server, because noise can
  only add CPU time. It covers parsing and keeping the output, not drawing it.
- `terminal_bytes` is the size of the log.
- tmux memory is not recorded. It depends on how tmux stores cells, not on the
  agent.

**Network:** containers use the host network, so an agent can reach other hosts.

- Every case except startup records them under `remote_connections`, and
  `summary.json` lists them per agent.
- These requests are part of what the agent costs, so they stay on.
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
