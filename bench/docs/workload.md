# Workload

`workload/` generates reasoning, text and tool calls from a seed.
`workload/profile.json` sets their shape with aggregate numbers only:

- quantiles of tool calls per turn
- the share of each tool kind, and quantiles of its argument and result bytes
- counts of which tool starts a turn and which tool follows each tool kind
- the share of calls with reasoning or text, and quantiles of their bytes
- the same for the answer at the end of a turn

About the profile:

- **Source:** the maintainer's top-level smelt sessions.
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

## Tool calls

The kind of the first call follows how often each kind starts a real turn. The
kind of each later call follows how often each kind comes after the kind before
it (a first-order Markov chain). The argument and result sizes come from the
quantiles of the kind.

Each call uses the agent's own tool for its kind, or its shell tool if it has
none, as in real use. Each agent's recipe sets them in `[tools]`. The model
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
