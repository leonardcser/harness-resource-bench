# Release a run

The site root shows the newest frozen run. Each run also gets a frozen page at
`runs/ID/`, stored in `results/ID/site/`, which never changes.

## Steps

Do all the work of a release on one branch.

1. **Versions:** set `version` in each agent's file in `bench/agents/`, then
   commit and push the branch. On the benchmark VM, with the branch checked out
   (see step 4), `uv run bench.py check` freezes the new installers in
   `bench/installers/`. Copy them back:
   `rsync -a VM:harness-resource-bench/bench/installers/ bench/installers/`.
   `check` fails if the mock model does not know a request, such as a new
   compaction prompt.
2. **Assumptions:** for each new version, check that:
   - the flags in `command()` and the config in `configure()` still work:
     approvals off, no updates or telemetry. The TUI gets these from the
     config only, the headless mode from the flags.
   - `server` still marks each agent whose TUI starts a shared server, and
     the headless mode still starts none.
   - codex's `tool_output_token_limit` still equals the limit of its real
     models.
   - `background_setup` is still the only work after the prompt shows.
   - the [agent quirks](bench/README.md#agent-quirks) are still true.

   Then do the [recipes](#recipes) that trace the agent: idle, install size,
   startup and CPU time. They need only the new images, so do them now, while
   the VM is free.
3. **Commit and push** all changes to `bench/`.
4. **Run:** on the benchmark VM, in tmux. Do not rebase the branch after this:
   the manifest names its commit.

   ```sh
   git clone https://github.com/leonardcser/harness-resource-bench.git  # once
   cd harness-resource-bench && git checkout BRANCH
   cd bench && ./setup.sh  # once; then log out and in again
   uv run bench.py run     # makes results/ID
   ```

5. **Agents page and findings:** on your machine, copy the run and read it:

   ```sh
   rsync -a VM:harness-resource-bench/results/ID results/
   cd web && bun install && RUN=ID bun run dev
   ```

   Check each cell of `web/src/agents/AGENT.ts` against the release notes and
   docs. Compare the run with the previous one, and update the numbers in
   `web/src/findings.ts`. The session and first-launch recipes read the run.
   If neither a recipe nor the source explains a change, leave its cause out.
   Link the source at the new versions.

6. **Freeze and commit:** `RUN=ID bun run freeze` builds the run's page into
   `results/ID/site/`. Commit the run folder and the other changes.
7. **Land:** fast-forward `main` to the branch and push. CI deploys the site.

Good to know:

- **Link:** "Copy link" next to the run date copies the frozen page's URL.
- **Fixes:** a site fix reaches the root at once, and never a frozen page.
- **Code:** the manifest names the commit that measured the run, and the
  Methodology page links to it. `freeze` refuses a run without one.

## Recipes

Each recipe finds the cause behind one chart, for `web/src/findings.ts`.

**Never attach a tool to `bench.py run`.** strace and perf slow the agent, and
the run would measure that cost. Use the agent's image by hand, or the setup
check.

To start an agent at its prompt:

```sh
podman run --rm -it IMAGE AGENT   # IMAGE from `podman images harness-bench-*`
PID=$(pgrep -n -f AGENT)
```

### Idle: which timers wake the agent

```sh
sudo timeout 3 strace -f -tt -p "$PID" -o idle.txt
```

Find calls that repeat at a fixed interval, or the timeout of `epoll_wait`,
`poll` and `futex`. Then find that interval in the agent's source.

Result: `WAKEUPS[agent].timers` and `IDLE.causes[agent]`.

### Session data: what the files hold

Each checkpoint of the long session keeps `disk_dirs`, the size of each folder
of the HOME. Subtract the first checkpoint from the last to see which folders
the session fills:

```sh
jq -r '.checkpoints | (.[0].disk_dirs) as $a | .[-1].disk_dirs
  | to_entries[] | [.value - ($a[.key] // 0), .key] | @tsv' \
  ../results/RUN/cases/ID/result.json | sort -rn | head   # ID of the long session
```

`session_<kind>_bytes_after_N` splits the bytes by format. Then read in the
agent's source what it writes in those folders.

Result: `SESSION.causes[agent]`.

### Install size: what the files are

```sh
podman run --rm --user root IMAGE \
  find /root /usr/local /opt -type f -size +1M -printf '%s\t%p\n' | sort -rn | head -20
```

`file` tells a native binary from a script. A Bun binary holds the runtime and
its JavaScript in a `.bun` section: `readelf -S BINARY | grep -A1 bun`.

Result: `INSTALL_PIECES[agent]` and `INSTALL.causes[agent]`.

### First launch: what the agent sets up once

```sh
jq .first_launch_dirs ../results/RUN/cases/ID/result.json   # ID of a startup case
```

Name the folders. The run measures their sizes, and a folder without a name
shows as "other files".

Result: `FIRST_LAUNCH_FILES[agent]` and the first launch in
`STARTUP.causes[agent]`.

### Startup: what happens before the prompt

```sh
sudo perf trace -a -e execve,connect -o start.txt -- podman run --rm -it IMAGE AGENT
```

Quit when the prompt shows. Each `execve` is a new program, and the gaps between
them are the steps. A `connect` is a network call that the user waits for.

Then time the runtime alone, on the agent's CPUs, and divide by 20:

```sh
podman run --rm --cpuset-cpus 2,3,4,5 IMAGE \
  bash -c 'time (for i in $(seq 20); do RUNTIME -e 0; done)'
```

`RUNTIME` is `node`, or `BUN_BE_BUN=1 AGENT` for a Bun binary. If the binary
ignores `BUN_BE_BUN`, time `AGENT --version`. That is an upper bound.

Result: `STARTUP.causes[agent]`, with the runtime's time.

### CPU time with the TUI: where it goes

Record the setup check, then look at the agent's own threads:

```sh
sudo perf record -a -g -o check.data -- uv run bench.py check AGENT
sudo perf report -i check.data --comm AGENT --sort sym --stdio | head -60
```

Result: `RENDER.causes[agent]` and `GROWTH.causes[agent]`.
