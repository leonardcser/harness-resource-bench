# Fairness

- **Install:** each agent's official installer, frozen in `installers/`.
- **Limits:** per container, 4 CPUs (two physical cores), 4 GiB of memory, no
  swap and 512 processes. No agent peaks above 1 GiB.
- **State:** dummy credentials and no personal state. The first launch starts
  the TUI in a new HOME, waits until it takes input and its files stop changing,
  then quits with SIGTERM. codex and Claude Code clone a plugin repository in
  the background, so their first launch also waits for that
  (`background_setup`).
- **CPUs:** the agent runs on CPUs 2 to 5, the harness on CPUs 0 and 1. One case
  runs at a time. In a test, 4 neighbours on the same CCD added 6% to 8% CPU,
  against under 1% of noise.
- **Order:** each repeat shuffles the agents, with a fixed seed. start-memory
  runs last, because it empties the file cache.
- **Defaults:** each agent runs with its defaults, except:
  - telemetry, error reports and automatic updates are off (`ENV` in
    `agents/agent.py`, and each recipe's `[environment]`). Other requests stay
    on, such as session titles.
  - approvals and the sandbox are off, so the run needs no person.
  - codex's shared server does not update itself.
- **Launch:** the TUI starts as a user starts it each day: the bare command,
  with the model and approvals in the agent's config. opencode and codex start
  their shared background server, which stays after quit, as for a user.
  Headless starts as automation starts it: the same settings as flags, and no
  shared server. OpenCode's `--standalone` starts a private child server that
  exits with the CLI. Its resource use counts toward the headless measurement.
- **Context window:** 200k tokens for every agent. codex also gets the tool
  output limit of its real models (`tool_output_token_limit`), because it does
  not know the mock model.
- **Warmup:** one practice task per agent and frontend, which does not count.
