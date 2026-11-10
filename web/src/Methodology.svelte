<script lang="ts">
  import Kinds from "./charts/Kinds.svelte";
  import {
    CLOCK_GHZ,
    PROFILE as profile,
    REPO,
    RUN as run,
    nameOf,
    type Profile,
  } from "./lib/data";
  import { count, percent, seconds } from "./lib/format";
  import { noise, repeats, spread, steal } from "./lib/measures";
  import Section from "./Section.svelte";

  const calls = (profile: Profile, p: number) =>
    Math.round(profile.turn.calls[profile.points.indexOf(p)]);
  const sentence = (s: string) => s[0].toUpperCase() + s.slice(1);
  const { fewest, most } = repeats(run);
  const RUNS = fewest === most ? `${most}` : `${fewest} to ${most}`;
  const NOISE = noise(run);
  const CANARY = run.summary.canary;
  const QUESTIONS = [
    [
      "Startup",
      "Time from launch until a key typed in the TUI shows on screen, with a warm file cache.",
    ],
    [
      "Memory at start",
      "Memory after the first request, with a cold file cache.",
    ],
    [
      "Install size",
      "Disk space that the official installer adds to the image.",
    ],
    [
      "Coding task",
      "CPU time for one task with 24 tool calls, with and without the TUI. The model streams at 30 to 1,000 tokens per second.",
    ],
    [
      "Long session",
      "Memory, CPU time per turn and session data on disk, over 64 turns. Each agent compacts its history in its own way.",
    ],
    [
      "New sessions",
      "Memory over 16 sessions in one process, each started with the agent's new-session command.",
    ],
    [
      "Idle",
      "CPU time and memory during 5 minutes without input, after a task.",
    ],
  ];
  const CONTROLS = [
    [
      "Reserved cores",
      "While the benchmark VM runs, the host kernel takes its cores away from all other work. Each virtual CPU runs on one fixed host thread, and hardware interrupts go to other cores.",
    ],
    [
      "Fixed clock",
      `The reserved cores run at ${CLOCK_GHZ} GHz, the base clock of the CPU, so boost cannot change the speed between runs.`,
    ],
    [
      "One at a time",
      "One case runs at a time, on two cores. The benchmark runs on a third core. In a test, four neighbours on the same cores made the agents use 6% to 8% more CPU time.",
    ],
    [
      "Same start",
      "Each agent comes from its official installer, at a fixed version, with its defaults. Only telemetry, error reports and updates are off. Each case starts a new container with a new home folder. One practice task per agent does not count.",
    ],
    [
      "Same work",
      `A fixed seed generates the work. Every case runs ${RUNS} times, and each repeat shuffles the order of the agents.`,
    ],
    [
      "Checked work",
      "The scripted model checks every tool result, so an agent cannot skip work. Any failure stops the run, and the site shows only complete runs of all agents.",
    ],
  ];
  // The cores of the host, in two groups that each have their own L3 cache.
  const HOST_CORES = 6;
  const BENCH_CORES = ["benchmark", "agent", "agent", "free", "free", "free"];
</script>

<svelte:head>
  <title>Methodology - Harness resource bench</title>
  <meta
    name="description"
    content="How the benchmark works. A scripted model drives each agent through the same work, in the same container, while the host measures it."
  />
</svelte:head>

{#snippet box(title: string, text: string)}
  <div class="border border-line bg-bg px-3 py-2.5">
    <div class="text-sm font-medium">{title}</div>
    <div class="mt-1 text-xs leading-relaxed text-muted">{text}</div>
  </div>
{/snippet}

{#snippet arrows(forward: string, back: string)}
  <div class="text-center text-xs leading-tight text-muted">
    <div>{forward}</div>
    <div class="text-faint">
      <span class="sm:hidden">↓ ↑</span><span class="hidden sm:inline"
        >⟶<br />⟵</span
      >
    </div>
    <div>{back}</div>
  </div>
{/snippet}

{#snippet definitions(items: string[][])}
  <dl class="max-w-2xl divide-y divide-line text-sm">
    {#each items as [name, what] (name)}
      <div class="grid gap-1 py-2.5 sm:grid-cols-[9rem_1fr] sm:gap-4">
        <dt class="font-medium">{name}</dt>
        <dd class="leading-relaxed text-muted">{what}</dd>
      </div>
    {/each}
  </dl>
{/snippet}

<div class="max-w-3xl">
  <h1 class="text-3xl font-semibold tracking-tight">Methodology</h1>
  <p class="mt-4 leading-relaxed text-muted">
    A scripted model gives every agent the same work. So the benchmark measures
    the agent, not the quality of its answers.
  </p>
</div>

<div class="mt-14">
  <Section title="How a run works" description="One case, from the inside.">
    <figure class="max-w-2xl">
      <div
        class="grid items-center gap-3 sm:grid-cols-[minmax(0,1fr)_5rem_minmax(0,2fr)]"
      >
        {@render box(
          "Scripted model",
          "Asks for the next tool call and checks each result.",
        )}
        {@render arrows("tool call", "result")}
        <div class="border border-dashed border-faint p-3">
          <div class="mb-2.5 text-xs text-faint">
            Container with 2 CPU cores and 4 GiB
          </div>
          <div
            class="grid items-center gap-3 sm:grid-cols-[minmax(0,1fr)_3.5rem_minmax(0,1fr)]"
          >
            {@render box("Agent", "The real agent, with its own tools.")}
            {@render arrows("runs", "output")}
            {@render box("Workspace", "Files and commands that the calls use.")}
          </div>
        </div>
      </div>
    </figure>
    <p class="mt-6 max-w-2xl text-sm leading-relaxed">
      The model is a small local server that replies like a real provider, with
      one tool call per reply. From outside the container, the host reads its
      CPU time and memory every 100 ms. Memory is PSS, which counts memory that
      processes share only once.
    </p>
  </Section>

  <Section
    title="Questions"
    description="What each part of the results measures."
  >
    {@render definitions(QUESTIONS)}
  </Section>

  <Section
    title="Controls"
    description="The same conditions for every agent and every run."
  >
    <figure class="max-w-2xl">
      <div class="grid gap-3 sm:grid-cols-2">
        <div class="border border-dashed border-faint p-3">
          <div class="text-sm font-medium">Other work</div>
          <div class="mt-0.5 text-xs text-muted">
            The host and the other VMs
          </div>
          <div class="mt-3 grid grid-cols-6 gap-1">
            {#each { length: HOST_CORES }, i (i)}
              <div class="aspect-square border border-line bg-soft"></div>
            {/each}
          </div>
        </div>
        <div class="border border-accent p-3">
          <div class="text-sm font-medium">Benchmark VM</div>
          <div class="mt-0.5 text-xs text-muted">
            Reserved cores with their own L3 cache
          </div>
          <div class="mt-3 grid grid-cols-6 gap-1">
            {#each BENCH_CORES as role, i (i)}
              <div
                class={[
                  "aspect-square border",
                  role === "agent" && "border-accent bg-accent",
                  role === "benchmark" && "border-faint bg-faint",
                  role === "free" && "border-faint",
                ]}
                title={role}
              ></div>
            {/each}
          </div>
        </div>
      </div>
      <figcaption
        class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs leading-relaxed text-muted"
      >
        <span>Each square is one physical core of the host.</span>
        <span class="flex gap-x-4">
          <span class="flex items-center gap-1.5"
            ><i class="inline-block size-2.5 bg-accent"></i>Agent</span
          >
          <span class="flex items-center gap-1.5"
            ><i class="inline-block size-2.5 bg-faint"></i>Benchmark</span
          >
          <span class="flex items-center gap-1.5"
            ><i class="inline-block size-2.5 border border-faint"></i>Kept free</span
          >
        </span>
      </figcaption>
    </figure>
    <div class="mt-8">{@render definitions(CONTROLS)}</div>
    <p class="mt-4 max-w-2xl text-xs leading-relaxed text-muted">
      The host hook that reserves the cores is in
      <a href="{REPO}/blob/main/bench/proxmox/bench-isolate" class="link"
        >bench/proxmox</a
      >.
    </p>
  </Section>

  <Section
    title="Noise"
    description="How much the runs of one case differ, in the run on this site."
  >
    <p class="max-w-2xl text-sm leading-relaxed">
      Spread is the range of the runs, as a share of their median. CPU time of
      real work varies little. Short and idle times vary more, because a few
      wake-ups are a large share of them. The hypervisor took at most {seconds(
        steal(run),
      )} from the agent's cores in any case.
      {#if CANARY}
        A fixed CPU job before every case took {seconds(CANARY.median)}, with a
        spread of {percent(spread(CANARY) * 100)} over the {CANARY.n} cases of the
        run.
      {/if}
    </p>
    <table class="mt-6 w-full max-w-2xl text-sm tabular-nums">
      <thead>
        <tr class="border-b border-line text-xs text-muted">
          <th class="py-2 pr-4 text-left font-normal">Result</th>
          <th class="py-2 pr-4 text-right font-normal">Runs</th>
          <th class="py-2 pr-4 text-right font-normal">Typical spread</th>
          <th class="py-2 text-right font-normal">Largest spread</th>
        </tr>
      </thead>
      <tbody>
        {#each NOISE as row (row.measure.name)}
          <tr class="border-b border-line last:border-0">
            <td class="py-2.5 pr-4">{sentence(row.measure.name)}</td>
            <td class="py-2.5 pr-4 text-right">{row.runs}</td>
            <td class="py-2.5 pr-4 text-right">{percent(row.typical * 100)}</td>
            <td class="py-2.5 text-right whitespace-nowrap">
              {percent(row.largest.spread * 100)}
              <span class="text-xs text-faint">{nameOf(row.largest.agent)}</span
              >
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    <p class="mt-4 max-w-2xl text-xs leading-relaxed text-muted">
      Typical is the median over the agents. A lead in the results needs all
      runs of an agent to beat all runs of the next agent, by 10%. With 3 runs
      each, all-beat-all alone is the strongest result that a one-sided
      Mann-Whitney test can give (p = 0.05).
    </p>
  </Section>

  <Section
    title="Workload"
    description="Generated work with the shape of real sessions."
  >
    <p class="max-w-2xl text-sm leading-relaxed">
      I measured {count(profile.source.turns)} turns and {count(
        profile.source.steps,
      )} tool calls from my own coding sessions. The benchmark keeps only their shape:
      tool calls per turn, tool kinds and sizes, but no text. Half of the turns make
      {calls(profile, 0.5)} tool calls or fewer, one in ten makes {calls(
        profile,
        0.9,
      )} or more, and the largest 1% make {calls(profile, 0.99)} or more.
    </p>
    <figure class="mt-8 max-w-2xl">
      <h3 class="mb-3 text-sm font-medium">Tool calls by kind</h3>
      <Kinds {profile} />
      <figcaption class="mt-3 text-xs leading-relaxed text-muted">
        Typical size is the median. For shell, read and search, it is the size
        of the result. For edit and write, it is the size of the change.
      </figcaption>
    </figure>
  </Section>

  <Section title="Causes" description="Where the Why under a chart comes from.">
    <p class="max-w-2xl text-sm leading-relaxed">
      The causes come from separate runs with profilers, never the timed runs:
      perf for CPU time, strace for timers, and the files that the agent saves.
      Each cause links the code in the agent's source, at the version in the
      benchmark. Claude Code is closed source, so its causes come from traces
      only.
      <a href="{REPO}/blob/main/bench/ANALYSIS.md" class="link">ANALYSIS.md</a> tells
      how to find each cause again.
    </p>
  </Section>

  <Section title="Limits" description="What these numbers do not tell you.">
    <ul
      class="max-w-2xl list-disc space-y-2 pl-5 text-sm leading-relaxed marker:text-faint"
    >
      <li>
        Nothing about the quality of answers, because the model is scripted.
      </li>
      <li>
        The workload comes from my own sessions. Its text is filler, and real
        code and Markdown can cost more to render.
      </li>
      <li>
        The model makes one tool call per reply. Real models sometimes make
        several at once.
      </li>
      <li>One Linux machine and one version of each agent.</li>
      <li>
        I wrote the benchmark, and I also build smelt. The setup of each agent
        is in the <a href={REPO} class="link">repository</a>. If one is set up
        unfairly, please open an issue.
      </li>
    </ul>
  </Section>
</div>

<p class="border-t border-line pt-6 text-xs leading-relaxed text-muted">
  The
  <a href="{REPO}/blob/main/bench/README.md" class="link">benchmark README</a> has
  the full details, such as how results are checked and how the cost of the terminal
  is measured.
</p>
