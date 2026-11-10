<script lang="ts">
  import Bars from "./charts/Bars.svelte";
  import Beats from "./charts/Beats.svelte";
  import Columns from "./charts/Columns.svelte";
  import Figure from "./charts/Figure.svelte";
  import Lines from "./charts/Lines.svelte";
  import Stack from "./charts/Stack.svelte";
  import {
    FX_WALK,
    GROWTH,
    IDLE,
    INSTALL,
    INSTALL_PIECES,
    MEMORY,
    RENDER,
    SESSION,
    STARTUP,
    TIMERS,
  } from "./findings";
  import Overview from "./Overview.svelte";
  import Section from "./Section.svelte";
  import { agentsOf, marks, pick, rows, series, type Run } from "./lib/data";
  import {
    INSTALL_PARTS,
    MEMORY_PARTS,
    SESSION_PARTS,
    TASK_PARTS,
    idleRates,
    installRows,
    memoryRows,
    sessionRows,
    taskRows,
  } from "./lib/splits";
  import { bytes, count, minutes, percent, seconds } from "./lib/format";
  import Why from "./Why.svelte";

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
  const lastIdle = $derived(
    marks(idle.values(), "idle_pss_bytes_after_").at(-1) ?? 0,
  );
  const install = $derived(installRows(manifest, INSTALL_PIECES));
  const task = $derived(taskRows(tui, headless));
  const memory = $derived(memoryRows(idle, lastIdle));
  const session = $derived(sessionRows(growth, turns));
  /** The same workload for every agent, so any group has it. */
  const text = $derived(
    [...growth.values()]
      .map((g) => g.metrics[`session_text_bytes_after_${turns}`]?.median)
      .find((v) => v !== undefined),
  );
  const idleRate = $derived(idleRates(idle));
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

{#snippet walk()}
  {@const top = Math.max(...FX_WALK)}
  <figure>
    <h4 class="mb-2 text-xs font-medium">fx: blocks rendered for one update</h4>
    <div
      class="flex h-20 items-end gap-[2px]"
      role="img"
      aria-label="From {FX_WALK[0]} to {FX_WALK.at(-1)} blocks"
    >
      {#each FX_WALK as n, i (i)}
        <div class="flex h-full w-8 flex-col justify-end">
          <div
            class="bg-bar"
            style:height="{(n / top) * 100}%"
            title="{count(n)} blocks"
          ></div>
        </div>
      {/each}
      <span class="ml-2 self-center text-xs text-muted tabular-nums"
        >{FX_WALK[0]} → {FX_WALK.at(-1)}</span
      >
    </div>
    <figcaption class="mt-2 text-xs leading-relaxed text-muted">
      The average in each eighth of a 32-turn session, from fx's own trace. The
      work grows with the session, so the cost of a session grows with its
      square.
    </figcaption>
  </figure>
{/snippet}

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
    <a
      href="#/agents"
      class="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
      >Compare their features</a
    >.
  </p>
</Section>

<Section
  title="Start"
  description="How fast each agent starts, and how much memory and disk it needs."
>
  <div
    class="grid grid-cols-1 gap-x-(--gap-x) gap-y-(--gap-y) [--gap-x:--spacing(10)] [--gap-y:--spacing(12)] xl:grid-cols-2"
  >
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
    <!-- Both columns wide, with the rule under the startup chart only. -->
    <div class="-mt-(--gap-y) xl:col-span-2 xl:row-start-2">
      <Why topic={STARTUP} rule="xl:w-[calc(50%-var(--gap-x)/2)]" />
    </div>
    <div class="xl:col-start-2 xl:row-start-1">
      <Figure
        title="Memory at start"
        note="Memory after the first request, with a cold file cache."
      >
        <Bars rows={rows(cold, "pss_bytes")} format={bytes} />
      </Figure>
    </div>
    <div class="xl:col-span-2">
      <Figure
        title="Install size"
        note="Disk space that the official installer uses, split by what the files are. For pi, this includes Node.js, which it needs to run. Hover a part for the files in it."
      >
        <Stack rows={install} parts={INSTALL_PARTS} format={bytes} />
        {#snippet more()}<Why topic={INSTALL} />{/snippet}
      </Figure>
    </div>
  </div>
</Section>

<Section
  title="A coding task"
  description="One task with 24 tool calls. The model streams 120 tokens per second."
>
  <div class="grid grid-cols-1 gap-x-10 gap-y-12 xl:grid-cols-2">
    <div class="xl:col-span-2">
      <Figure
        title="Where the CPU time goes"
        note="The parts add up to the total. Headless is the same task without the TUI. + TUI is the extra CPU time of the agent when it runs with its TUI. + Terminal is the time that tmux needs to draw the output, which your machine also pays. It is much smaller, so it has its own scale. Click a column to sort by it."
      >
        <Columns rows={task} parts={TASK_PARTS} format={seconds} />
        {#snippet more()}<Why topic={RENDER} />{/snippet}
      </Figure>
    </div>
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
  <div class="grid grid-cols-1 gap-y-12">
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
      {#snippet more()}<Why topic={GROWTH}>
          {@render walk()}
        </Why>{/snippet}
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
    {#if session.length}
      <Figure
        title="What the session data holds"
        note="Session data after {turns} turns, split by file format. The line is the text of the session itself: tool calls, tool output and answers."
      >
        <Stack
          rows={session}
          parts={SESSION_PARTS}
          format={bytes}
          mark={text
            ? { value: text, label: "Text of the session" }
            : undefined}
        />
        {#snippet more()}<Why topic={SESSION} />{/snippet}
      </Figure>
    {/if}
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
  <div class="grid grid-cols-1 gap-y-12">
    {#if idleRate.size}
      <Figure
        title="What wakes an idle agent"
        note="Two seconds of idle. Each tick is a timer from the agent's source code, as tall as the CPU time of one wake-up. Wake-ups/s counts all its threads over the whole idle. CPU/s is the CPU time per second of idle, after the first 30 s. A few costly wake-ups can cost more than many cheap ones. No agent draws to the screen while idle."
      >
        <Beats rates={idleRate} timers={TIMERS} />
        {#snippet more()}<Why topic={IDLE} />{/snippet}
      </Figure>
    {/if}
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
    <Figure
      title="What the memory holds"
      note="Memory after {minutes(
        lastIdle,
      )} of idle. Code and mapped files are pages that the kernel can read again from disk, mostly the program itself. Heap and data is all the rest."
    >
      <Stack rows={memory} parts={MEMORY_PARTS} format={bytes} />
      {#snippet more()}<Why topic={MEMORY} />{/snippet}
    </Figure>
  </div>
</Section>

<p class="border-t border-line pt-6 text-xs leading-relaxed text-muted">
  Values are medians of the runs. Whiskers and bands show the range. {manifest
    .machine.cpu}, kernel
  {manifest.machine.kernel}, {manifest.machine.podman}.
</p>
