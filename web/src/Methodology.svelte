<script lang="ts">
  import Kinds from "./charts/Kinds.svelte";
  import { PROFILE as profile, REPO, type Profile } from "./lib/data";
  import { count } from "./lib/format";
  import Section from "./Section.svelte";

  const calls = (profile: Profile, p: number) =>
    Math.round(profile.turn.calls[profile.points.indexOf(p)]);
  const QUESTIONS = [
    [
      "Startup",
      "Time from launch until a key typed in the TUI shows on screen.",
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

<div class="max-w-3xl">
  <h1 class="text-3xl font-semibold tracking-tight">Methodology</h1>
  <p class="mt-4 leading-relaxed text-muted">
    A scripted model gives every agent the same work. So the benchmark measures
    the agent, not the quality of its answers.
  </p>
</div>

<div class="mt-14">
  <Section
    title="How a run works"
    description="A scripted model drives a real agent."
  >
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
            {@render box("Agent", "The real agent, at a fixed version.")}
            {@render arrows("runs", "output")}
            {@render box("Workspace", "Files and commands that the calls use.")}
          </div>
        </div>
      </div>
      <figcaption class="mt-3 text-xs leading-relaxed text-muted">
        The host measures the container from outside.
      </figcaption>
    </figure>

    <div class="mt-8 max-w-2xl space-y-3 text-sm leading-relaxed">
      <p>
        The model is a small local server that replies like a real provider.
        Each reply asks for one tool call, and the last reply ends the turn.
      </p>
      <p>
        The agent runs each call for real, with its own tools. The model checks
        every result, so an agent cannot skip work.
      </p>
      <p>
        The host reads the CPU time and memory of the container every 100 ms.
        Memory is PSS, which counts memory shared between processes only once.
      </p>
    </div>
  </Section>

  <Section
    title="Questions"
    description="What each part of the results measures."
  >
    <dl class="max-w-2xl divide-y divide-line text-sm">
      {#each QUESTIONS as [name, what] (name)}
        <div class="grid gap-1 py-2.5 sm:grid-cols-[9rem_1fr] sm:gap-4">
          <dt class="font-medium">{name}</dt>
          <dd class="leading-relaxed text-muted">{what}</dd>
        </div>
      {/each}
    </dl>
  </Section>

  <Section
    title="Setup"
    description="The same conditions for every agent and every run."
  >
    <ol
      class="max-w-2xl list-decimal space-y-2 pl-5 text-sm leading-relaxed marker:text-faint"
    >
      <li>
        Each agent is installed with its official installer, at a fixed version,
        in its own container image.
      </li>
      <li>
        Each case uses a new container with 2 CPU cores and 4 GiB of memory, on
        cores that no other work shares. One case runs at a time.
      </li>
      <li>
        Every case runs 3 times, in random order. The results show the median
        and the range.
      </li>
    </ol>
  </Section>

  <Section
    title="Workload"
    description="Generated work with the shape of real sessions."
  >
    <div class="max-w-2xl space-y-3 text-sm leading-relaxed">
      <p>
        I measured {count(profile.source.turns)} turns and {count(
          profile.source.steps,
        )} tool calls from my own coding sessions. The benchmark keeps only numbers
        from them, such as how many tool calls a turn makes, which tools they use,
        and how large their arguments and results are. It keeps no text.
      </p>
      <p>
        From those numbers, the benchmark generates new work with a fixed seed.
        So every agent gets the same work. Half of the turns make {calls(
          profile,
          0.5,
        )} tool calls or fewer. One turn in ten makes {calls(profile, 0.9)} or more,
        and the largest 1% make {calls(profile, 0.99)} or more. The text in the work
        is generated filler.
      </p>
    </div>

    <figure class="mt-10 max-w-2xl">
      <h3 class="mb-3 text-sm font-medium">Tool calls by kind</h3>
      <Kinds {profile} />
      <figcaption class="mt-3 text-xs leading-relaxed text-muted">
        Typical size is the median. For shell, read and search, it is the size
        of the result. For edit and write, it is the size of the change.
      </figcaption>
    </figure>
  </Section>

  <Section title="Causes" description="Where the Why under a chart comes from.">
    <div class="max-w-2xl space-y-3 text-sm leading-relaxed">
      <p>
        The timed runs measure the split of memory, the session files by format,
        and the idle wake-ups. The causes behind them come from separate runs
        with profilers, never the timed ones: perf for CPU time, strace for
        timers, and the files that the agent saves. Then I found the code behind
        each result in the agent's source, at the version in the benchmark, and
        linked the line.
      </p>
      <p>
        Claude Code is closed source, so its causes come from traces only. The
        split of install size comes from the installed files.
        <a
          href="{REPO}/blob/main/bench/ANALYSIS.md"
          class="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
          >ANALYSIS.md</a
        > tells how to find each cause again.
      </p>
    </div>
  </Section>

  <Section title="Limits" description="What these numbers do not tell you.">
    <ul
      class="max-w-2xl list-disc space-y-2 pl-5 text-sm leading-relaxed marker:text-faint"
    >
      <li>
        The model is scripted, so this says nothing about the quality of
        answers.
      </li>
      <li>
        The text is filler. Real code and Markdown can cost more to render.
      </li>
      <li>
        The model makes one tool call per reply. Real models sometimes make
        several at once.
      </li>
      <li>The workload comes from my own sessions.</li>
      <li>It uses one Linux machine and one version of each agent.</li>
      <li>
        I wrote the benchmark, and I also build smelt. The setup of each agent
        is in the
        <a
          href={REPO}
          class="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
          >repository</a
        >. If one is set up unfairly, please open an issue.
      </li>
    </ul>
  </Section>
</div>

<p class="border-t border-line pt-6 text-xs leading-relaxed text-muted">
  The
  <a
    href="{REPO}/blob/main/bench/README.md"
    class="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
    >benchmark README</a
  > has the full details, such as how results are checked and how the cost of the
  terminal is measured.
</p>
