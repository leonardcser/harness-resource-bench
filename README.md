<p align="center">
  <img src="web/public/favicon.svg" width="56" alt="" />
</p>

<h1 align="center">Harness resource bench</h1>

<p align="center">
  Benchmarking CPU, memory and disk use of coding agents.
  <br />
  <a href="https://leonardcser.github.io/harness-resource-bench"><strong>See the results</strong></a>
  ·
  <a href="bench/README.md">How it works</a>
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/readme/overview-dark.png" />
  <img src=".github/readme/overview-light.png" alt="Overview: the median startup, memory, install size, CPU and disk of each agent, with the clear leads in blue" />
</picture>

How much does a coding agent cost your machine? This benchmark measures the
startup time, memory, CPU time, session data on disk and install size of Claude
Code, codex, fx, omp, opencode, pi and smelt.

A local mock model gives every agent the same scripted work: real tool calls
against real files, with the shape of real sessions. Each agent runs at a pinned
version in its own container, and the host measures the container from outside.

| Folder     | What it holds                                                    |
| ---------- | ---------------------------------------------------------------- |
| `bench/`   | The harness: agents, mock model, workload and measurement        |
| `results/` | One folder per run: manifest, summary, workload profile and page |
| `web/`     | The site, which shows the newest frozen run                      |

## Run the benchmark

On a fresh Ubuntu VM with 6 CPUs or more, to reproduce a released run:

```sh
git checkout COMMIT          # the commit on the Methodology page of the run
cd bench && ./setup.sh       # once; then log out and in again
uv run bench.py run          # all agents, about 8.5 hours
cd ../web && RUN=ID bun run dev   # ID: the folder that run made in results/
```

`run` checks the host, builds the images and measures, all in one session.
[`bench/README.md`](bench/README.md) explains how it works and what each case
measures.

## Build the site

With [bun](https://bun.sh):

```sh
cd web
bun install
bun run dev    # or: bun run build
```

`bun run lint` checks formatting and types. To release a new run and share it,
see [RELEASE.md](RELEASE.md).

## License

[MIT](LICENSE)
