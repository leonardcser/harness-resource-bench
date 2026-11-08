<script lang="ts">
  import Bars from "./charts/Bars.svelte";
  import Figure from "./charts/Figure.svelte";
  import Lines from "./charts/Lines.svelte";
  import Overview from "./Overview.svelte";
  import Section from "./Section.svelte";
  import {
    agentsOf,
    nameOf,
    pick,
    rows,
    series,
    single,
    type Run,
  } from "./lib/data";
  import { bytes, count, minutes, percent, seconds } from "./lib/format";

  let { run }: { run: Run } = $props();

  const { summary, manifest } = $derived(run);
  const agents = $derived(agentsOf(manifest));
  const startup = $derived(pick(summary, "startup", "tui", 0));
  const cold = $derived(pick(summary, "start-memory", "headless", 0));
  const tui = $derived(pick(summary, "task", "tui", 120));
  const headless = $derived(pick(summary, "task", "headless", 120));
  const growth = $derived(pick(summary, "long-session", "tui", 1000));
  const retention = $derived(pick(summary, "new-sessions", "tui", 1000));
  const idle = $derived(pick(summary, "idle", "tui", 1000));
  const turns = $derived(
    Math.max(0, ...[...growth.values()].map((g) => g.turns)),
  );
  const sessions = $derived(
    Math.max(0, ...[...retention.values()].map((g) => g.turns)),
  );
  const rates = $derived(
    [
      ...new Set(
        summary.groups
          .filter((g) => g.question === "task" && g.frontend === "tui")
          .map((g) => g.rate),
      ),
    ].sort((a, b) => a - b),
  );
  const byRate = $derived(
    agents.map((agent) => ({
      agent,
      points: rates.flatMap((rate) => {
        const stat = pick(summary, "task", "tui", rate).get(agent)?.metrics
          .active_cpu_percent;
        return stat ? [{ x: rate, stat }] : [];
      }),
    })),
  );
  const install = $derived(
    Object.entries(manifest.config.images.agents).map(([agent, image]) => ({
      agent,
      stat: single(image.install_bytes),
    })),
  );
  const facts = $derived([
    ["Run", manifest.started_utc.slice(0, 10)],
    ["Agents", String(agents.length)],
    ["Cases", count(summary.planned)],
    ["Machine", manifest.machine.cpu.replace(/ \d+-Core Processor$/, "")],
    ["Per agent", "2 CPU cores, 4 GiB memory"],
  ]);
  const ZONES = [
    { from: 0.01, label: "feels instant" },
    { from: 0.1, label: "noticeable" },
    { from: 1, label: "waiting" },
  ];
  const MIB = 2 ** 20;
</script>

<svelte:head>
  <title>Resource use of coding agents - Harness resource bench</title>
  <meta
    name="description"
    content="Startup time, memory, CPU time, session data and install size of Claude Code, Codex, fx, omp, opencode, pi and smelt, measured on the same scripted work."
  />
</svelte:head>

<div class="max-w-3xl">
  <h1 class="text-3xl font-semibold tracking-tight">
    Resource use of coding agents
  </h1>
  <p class="mt-4 leading-relaxed text-muted">
    How much each coding agent costs your machine. Every agent does the same
    scripted work in the same container. Lower is better.
  </p>
</div>
<dl class="mt-8 mb-14 grid grid-cols-2 gap-x-8 gap-y-4 text-sm sm:grid-cols-5">
  {#each facts as [label, value] (label)}
    <div class="border-l border-line pl-3">
      <dt class="text-xs text-muted">{label}</dt>
      <dd class="mt-0.5">{value}</dd>
    </div>
  {/each}
</dl>

<Section
  title="Overview"
  description="The median of each question. Blue marks a lead: the agent is clearly lowest, because all its runs beat all runs of the next agent by at least 10%. Agents with as many leads share a rank. Click a column to sort by it."
  wide
>
  <Overview {run} />
  <p class="mt-6 text-xs leading-relaxed text-muted">
    The agents do not all do the same things, and an agent with fewer features
    can cost less.
    <a href="#/agents" class="text-accent hover:underline"
      >Compare their features</a
    >.
  </p>
</Section>

<Section
  title="Start"
  description="How fast each agent starts, and how much memory and disk it needs."
>
  <div class="grid gap-x-10 gap-y-12 xl:grid-cols-2">
    <Figure
      title="Startup"
      note="Time from launch until a typed key shows on screen. Log scale."
    >
      <Bars
        rows={rows(startup, "input_ready_seconds")}
        format={seconds}
        zones={ZONES}
      />
    </Figure>
    <Figure
      title="Memory at start"
      note="Memory after the first request, with a cold file cache."
    >
      <Bars rows={rows(cold, "pss_bytes")} format={bytes} />
    </Figure>
    <Figure
      title="Install size"
      note="Disk space that the official installer uses. For pi, this includes Node.js, which it needs to run."
    >
      <Bars rows={install} format={bytes} />
    </Figure>
  </div>
</Section>

<Section
  title="A coding task"
  description="One task with 24 tool calls. The model streams 120 tokens per second."
>
  <div class="grid gap-x-10 gap-y-12 xl:grid-cols-2">
    <Figure
      title="CPU time, TUI"
      note="CPU time of all the agent's processes during the task."
    >
      <Bars rows={rows(tui, "cpu_seconds")} format={seconds} />
    </Figure>
    <Figure
      title="CPU time, headless"
      note="The same task without the terminal UI."
    >
      <Bars rows={rows(headless, "cpu_seconds")} format={seconds} />
    </Figure>
    <Figure
      title="Terminal CPU time"
      note="CPU time that the terminal (tmux) needs to draw the agent's output. Your machine pays this cost, not the agent."
    >
      <Bars rows={rows(tui, "terminal_cpu_seconds")} format={seconds} />
    </Figure>
    <Figure
      title="Terminal output"
      note="Bytes that the agent writes to the terminal, with escape codes."
    >
      <Bars rows={rows(tui, "terminal_bytes")} format={bytes} />
    </Figure>
    <div class="xl:col-span-2">
      <Figure
        title="CPU use while streaming"
        note="Average CPU use during the task, at different streaming speeds."
      >
        <Lines series={byRate} xLabel="tokens/s" yFormat={percent} log />
      </Figure>
    </div>
  </div>
</Section>

<Section
  title="A long session"
  description={`One session of ${turns} turns. Each turn has as many tool calls as a real one. Each agent compacts its history when it gets near the context limit.`}
>
  <div class="grid gap-y-12">
    <Figure title="Memory" note="Memory after each checkpoint.">
      <Lines
        series={series(growth, "pss_bytes_after_")}
        xLabel="turns"
        yFormat={bytes}
        unit={MIB}
        log
      />
    </Figure>
    <Figure title="CPU time per turn" note="Average between two checkpoints.">
      <Lines
        series={series(growth, "cpu_seconds_per_turn_")}
        xLabel="turns"
        yFormat={seconds}
        log
      />
    </Figure>
    <Figure
      title="Session data on disk"
      note="Transcripts, history, databases and logs that the agent saves."
    >
      <Lines
        series={series(growth, "session_bytes_after_")}
        xLabel="turns"
        yFormat={bytes}
        unit={MIB}
        log
      />
    </Figure>
  </div>
</Section>

<Section
  title="New sessions"
  description={`${sessions} sessions in one process, each started with the agent's new-session command. This shows memory that a finished session leaves behind.`}
>
  <Figure title="Memory" note="Memory after each session.">
    <Lines
      series={series(retention, "pss_bytes_after_")}
      xLabel="sessions"
      yFormat={bytes}
      unit={MIB}
    />
  </Figure>
</Section>

<Section title="Idle" description="An open session, left alone after a task.">
  <div class="grid gap-y-12">
    <Figure title="CPU time" note="CPU time since the agent went idle.">
      <Lines
        series={series(idle, "idle_cpu_seconds_after_")}
        xLabel="idle for"
        xFormat={minutes}
        yFormat={seconds}
      />
    </Figure>
    <Figure title="Memory" note="Memory while idle.">
      <Lines
        series={series(idle, "idle_pss_bytes_after_")}
        xLabel="idle for"
        xFormat={minutes}
        yFormat={bytes}
        unit={MIB}
      />
    </Figure>
  </div>
</Section>

<p class="border-t border-line pt-6 text-xs leading-relaxed text-muted">
  Values are medians of the runs. Whiskers and bands show the range. {manifest
    .machine.cpu}, kernel
  {manifest.machine.kernel}, {manifest.machine.podman}.
</p>
