<p align="center">
  <img src=".github/readme/logo.svg" width="56" alt="" />
</p>

<h1 align="center">harness resource bench</h1>

<p align="center">
  Benchmarking CPU, memory and disk use of coding agents.
  <br />
  <a href="https://leonardcser.github.io/harness-lab/resources/"><strong>See the results</strong></a>
</p>

Every agent gets the same scripted work from a local mock model, at a pinned
version in its own container. The host measures the container from outside:
Claude Code, codex, fx, omp, opencode, pi and smelt, side by side.

| Measure      | Question                                       |
| ------------ | ---------------------------------------------- |
| Startup      | How long until the agent takes a key?          |
| Memory       | How much does it hold, at start and over time? |
| CPU time     | How much work does a task cost?                |
| Session data | How much does a long session write to disk?    |
| Install size | How much does the install add?                 |

## Quick start

On a fresh Ubuntu VM with 6 CPUs or more:

```sh
cd bench && ./setup.sh        # once; then log out and in again
uv run bench.py run omp       # one agent; leave out the name for all
```

## Docs

- [How it works](bench/README.md): the cases, the commands and the code
- [Release a run](RELEASE.md): from a version bump to published results
- [Results](https://leonardcser.github.io/harness-lab/resources/): the numbers
  and their analysis

## License

[MIT](LICENSE)
