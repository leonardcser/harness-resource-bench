# Measurement

**CPU and memory**

- The host reads the container's cgroup every 100 ms.
- CPU seconds come from cgroup deltas. 100% is one core.
- Memory is PSS: the sum over all processes in the cgroup, with shared pages
  split between them.
- TUI cases record PSS at checkpoints, after 2 seconds of settle time. Idle runs
  split it into file pages (mostly code) and anonymous pages (heap).
- `idle_wakeups_per_second`: voluntary context switches of all the agent's
  threads, per second of idle. The host reads each thread every second, and a
  thread that exits keeps its last count, so the total never drops.
- `quiet_seconds`: how long the host waited before the case for the agent's CPUs
  to stay idle for 0.5 s, at most 30 s.
- `settle_seconds`: how long the model held the agent's first request, until the
  agent used less than 10% of a core in each of 3 s in a row, at most 30 s. So
  startup work, such as codex's background work, stays out of every measurement.
  Memory at start is read at its end.
- `peak_memory_bytes`: the cgroup's own peak, with file cache.
- `canary_seconds`: the CPU time of a fixed hash of 4 MiB on CPU 2, just before
  the case. `summary.json` gives its range and 95th percentile under `canary`. A
  clock change or a neighbour on the agent's cores shows there.
- `steal_seconds`: the time the hypervisor ran something else on the agent's
  CPUs. On the benchmark VM it stays near zero.
- `cpu_wait_seconds`: the time that at least one of the agent's threads was
  ready to run but had no free CPU (`cpu.pressure`, "some"). It shows when 2
  cores are too few for the agent.
- `active_cpu_percent`: the CPU of the coding task, divided by the time from the
  first request to the done marker. It compares across streaming rates.

**Startup**

- `launch.py` writes a monotonic timestamp just before the agent's `exec`, with
  kernel echo off.
- The probe is one key, typed at the exec. Startup is the time until the agent
  draws it.
- The host sees the agent's tty input queue in `/proc`. It types the next key
  only when the agent took the last one without drawing it. Three keys never
  come within 10 ms, so no agent takes them for a paste. Startup resolves about
  1 ms.
- If the host cannot see the tty, it types a key every 10 ms, and `probe` is
  `interval`.
- The terminal is a tmux pane of 120 by 40, with a dark theme. tmux answers the
  agent's capability queries, as it does for users.
- The startup case times two launches: `first_launch_seconds` and
  `input_ready_seconds`. Both run with podman's `--init`, so the first can quit
  with SIGTERM.
- The first launch is cold: it starts the shared server of opencode and codex.
  The next launch is warm, as later in a user's day: `warm.py` first runs an
  earlier session of the TUI until the container is idle, and closes its
  terminal. The server stays, and has served the workspace. This happens before
  the exec mark, so it does not count.
- The first launch types its own probe key and deletes it before it quits. So a
  draft that the agent keeps cannot pass for the next probe.
- Each launch stops with an error if the agent draws the key of the other
  launch, which it never got. A key that the agent draws itself would pass for
  an echo.
- `first_request_seconds`: the time from the exec to the first request with the
  task. Headless startup is this time, with the flags.

**Quit**

- At the end of the TUI startup, task and long-session cases, the host waits
  until the agent's CPU settles. Then it types `/quit` and waits until the agent
  has drawn it.
- `quit_seconds`: the time from Enter until the agent's main process exits, read
  from a pidfd. The agent must exit with status 0.
- After startup, the host first deletes the probe and waits until the screen no
  longer shows it.
- The quit comes after the last sample, so it does not count in CPU, memory or
  the terminal replay.

**End of a turn:** the agent draws its done marker. A renderer can split the
marker across frames, so when the output stops, the harness also checks the
screen.

**Disk**

- `disk_bytes`: the size of all files in the agent's HOME, a host folder mounted
  into the container. `disk_dirs` gives it per folder.
- `first_launch_bytes`: what the first launch adds to the HOME, beside the
  config. `first_launch_dirs` gives it per folder.
- `session_bytes`: the net growth of the HOME since the first launch. The long
  session reports `session_bytes_after_N`.
- `session_files` counts the files the same way. `session_<kind>_bytes` splits
  the bytes by format: `sqlite`, `wal` (SQLite `-wal`, `-shm`, `-journal`),
  `jsonl`, `json` and `other`.
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

- Every case except startup records them under `remote_connections`, without the
  first launch. `summary.json` lists them per agent.
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
