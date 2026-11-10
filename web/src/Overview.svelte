<script lang="ts">
  import { Icon } from "svelte-icons-pack";
  import { BsChevronDown } from "svelte-icons-pack/bs";
  import Logo from "./Logo.svelte";
  import {
    agentsOf,
    marks,
    nameOf,
    pick,
    single,
    versionOf,
    type Run,
    type Stat,
  } from "./lib/data";
  import { bytes, percent, seconds } from "./lib/format";

  let { run }: { run: Run } = $props();

  type Column = {
    label: string;
    /** The column in a sentence, such as "startup time". */
    name: string;
    format: (v: number) => string;
    /** The smallest difference that counts as a win, in the column's unit. */
    floor: number;
    stat: (agent: string) => Stat | undefined;
  };
  const MS = 0.005;
  const MIB = 2 ** 20;
  const POINT = 0.5;

  const { summary, manifest } = $derived(run);
  const agents = $derived(agentsOf(manifest));
  const metric = (
    question: string,
    frontend: string,
    rate: number,
    name: (turns: number) => string,
  ) => {
    const groups = pick(summary, question, frontend, rate);
    return (agent: string) => {
      const group = groups.get(agent);
      return group?.metrics[name(group.turns)];
    };
  };
  const lastIdle = $derived(
    marks(
      summary.groups.filter((g) => g.question === "idle"),
      "idle_cpu_seconds_after_",
    ).at(-1) ?? 0,
  );
  const groups: { label: string; columns: Column[] }[] = $derived([
    {
      label: "Start",
      columns: [
        {
          label: "Startup",
          name: "startup time",
          format: seconds,
          floor: MS,
          stat: metric("startup", "tui", 0, () => "input_ready_seconds"),
        },
        {
          label: "Memory",
          name: "memory at start",
          format: bytes,
          floor: MIB,
          stat: metric("start-memory", "headless", 0, () => "pss_bytes"),
        },
        {
          label: "Install",
          name: "install size",
          format: bytes,
          floor: MIB,
          stat: (a) => {
            const value = manifest.config.images.agents[a]?.install_bytes;
            return value === undefined ? undefined : single(value);
          },
        },
      ],
    },
    {
      label: "Coding task",
      columns: [
        {
          label: "CPU, TUI",
          name: "CPU in the TUI",
          format: seconds,
          floor: MS,
          stat: metric("task", "tui", 120, () => "cpu_seconds"),
        },
        {
          label: "CPU, headless",
          name: "headless CPU",
          format: seconds,
          floor: MS,
          stat: metric("task", "headless", 120, () => "cpu_seconds"),
        },
        {
          label: "Terminal",
          name: "terminal CPU",
          format: seconds,
          floor: MS,
          stat: metric("task", "tui", 120, () => "terminal_cpu_seconds"),
        },
        {
          label: "CPU use",
          name: "CPU use while working",
          format: percent,
          floor: POINT,
          stat: metric("task", "tui", 120, () => "active_cpu_percent"),
        },
      ],
    },
    {
      label: "Long session",
      columns: [
        {
          label: "Memory",
          name: "memory in a long session",
          format: bytes,
          floor: MIB,
          stat: metric(
            "long-session",
            "tui",
            1000,
            (t) => `pss_bytes_after_${t}`,
          ),
        },
        {
          label: "Disk",
          name: "session data on disk",
          format: bytes,
          floor: MIB,
          stat: metric(
            "long-session",
            "tui",
            1000,
            (t) => `session_bytes_after_${t}`,
          ),
        },
      ],
    },
    {
      label: "Idle",
      columns: [
        {
          label: "CPU",
          name: "CPU when idle",
          format: seconds,
          floor: MS,
          stat: metric(
            "idle",
            "tui",
            1000,
            () => `idle_cpu_seconds_after_${lastIdle}`,
          ),
        },
      ],
    },
  ]);
  const columns = $derived(groups.flatMap((g) => g.columns));
  const value = (column: Column, agent: string) => column.stat(agent)?.median;

  type Key = number | "leads";
  // A column index, or "leads": the number of columns an agent clearly leads.
  // Each sort starts with the best first, and a second click reverses it.
  let sortBy = $state<Key>("leads");
  let reversed = $state(false);
  // Narrow screens show one column, which the reader picks.
  let shown = $state(0);
  const sort = (key: Key) => {
    reversed = sortBy === key && !reversed;
    sortBy = key;
    if (key !== "leads") shown = key;
  };
  // Only agents with results appear.
  const measured = $derived(
    agents.filter((a) => columns.some((c) => value(c, a) !== undefined)),
  );
  /** The agent that is clearly lowest in a column, if any. Its worst run must
   * beat the runner-up's best run, by 10% and by the column's floor. Smaller
   * differences can be noise, or too small to notice. */
  const leader = (column: Column): string | undefined => {
    const ranked = measured
      .map((agent) => ({ agent, stat: column.stat(agent) }))
      .filter((r): r is { agent: string; stat: Stat } => r.stat !== undefined)
      .sort((a, b) => a.stat.median - b.stat.median);
    const [first, second] = ranked;
    if (!first) return undefined;
    if (!second) return first.agent;
    const clear =
      first.stat.max < second.stat.min &&
      first.stat.median <= 0.9 * second.stat.median &&
      second.stat.median - first.stat.median >= column.floor;
    return clear ? first.agent : undefined;
  };
  /** The names of the columns that an agent clearly leads. */
  const led = (agent: string) =>
    columns.filter((c) => leader(c) === agent).map((c) => c.name);
  const count = (agent: string) => led(agent).length;
  const sentence = (names: string[]) =>
    names.length < 2
      ? names.join("")
      : `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;
  // Agents stay in alphabetical order within a tie: no other rule decides it.
  const byLeads = $derived([...measured].sort((a, b) => count(b) - count(a)));
  const sorted = $derived.by(() => {
    const sign = reversed ? -1 : 1;
    if (sortBy === "leads")
      return [...measured].sort((a, b) => sign * (count(b) - count(a)));
    const column = columns[sortBy];
    // Agents without a value stay last.
    return [...measured].sort((a, b) => {
      const [va, vb] = [value(column, a), value(column, b)];
      if (va === undefined || vb === undefined)
        return (va === undefined ? 1 : 0) - (vb === undefined ? 1 : 0);
      return sign * (va - vb);
    });
  });
  /** An agent's rank by leads. Agents with as many leads share a rank. */
  const rank = (agent: string) =>
    1 + measured.filter((a) => count(a) > count(agent)).length;
  const highest = (column: Column) =>
    Math.max(...measured.map((a) => value(column, a) ?? 0));
</script>

{#snippet sorter(key: Key, label: string, title?: string)}
  <button
    class={[
      "whitespace-nowrap transition-colors",
      sortBy === key ? "font-medium text-fg" : "text-muted hover:text-fg",
    ]}
    {title}
    onclick={() => sort(key)}
  >
    {label}<span
      class={["ml-0.5 inline-block w-2", sortBy !== key && "invisible"]}
      >{reversed ? "↑" : "↓"}</span
    >
  </button>
{/snippet}

<label class="mb-4 flex items-center gap-3 text-sm md:hidden">
  <span class="text-muted">Show</span>
  <span class="relative min-w-0 flex-1">
    <select
      class="w-full appearance-none border border-line bg-bg py-1.5 pr-8 pl-2.5 text-base"
      value={shown}
      onchange={(e) => {
        reversed = false;
        sortBy = shown = Number(e.currentTarget.value);
      }}
    >
      {#each groups as group (group.label)}
        <optgroup label={group.label}>
          {#each group.columns as column (column.name)}
            {@const i = columns.indexOf(column)}
            <option value={i}
              >{column.name[0].toUpperCase()}{column.name.slice(1)}</option
            >
          {/each}
        </optgroup>
      {/each}
    </select>
    <span
      class="pointer-events-none absolute inset-y-0 right-2.5 flex items-center text-muted"
      aria-hidden="true"
    >
      <Icon src={BsChevronDown} size={12} />
    </span>
  </span>
</label>
<!-- Medium screens scroll the table, with the rank and agent fixed. -->
<div class="overflow-x-auto">
  <table class="w-full text-sm tabular-nums">
    <thead>
      <tr class="text-xs text-faint max-md:hidden">
        <th colspan="2" class="sticky left-0 bg-bg"></th>
        <th></th>
        {#each groups as group (group.label)}
          <th
            colspan={group.columns.length}
            class="px-3 pb-1 text-right font-normal"
          >
            <div class="border-b border-line pb-1">{group.label}</div>
          </th>
        {/each}
      </tr>
      <tr class="border-b border-line text-xs">
        <th
          class="sticky left-0 w-8 min-w-8 bg-bg py-2 text-left font-normal text-faint"
        >
          #
        </th>
        <th
          class="sticky left-8 bg-bg py-2 pr-4 text-left font-normal text-muted"
        >
          Agent
        </th>
        <th class="py-2 pr-3 text-right font-normal">
          {@render sorter(
            "leads",
            "Leads",
            "The columns where the agent is clearly lowest: all its runs beat all runs of the next agent, by at least 10%. Agents with as many leads share a rank.",
          )}
        </th>
        {#each columns as column, i (i)}
          <th
            class={[
              "px-3 py-2 text-right font-normal",
              i !== shown && "max-md:hidden",
            ]}
          >
            {@render sorter(i, column.label)}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each sorted as agent (agent)}
        <tr
          class="border-b border-line bg-bg transition-colors last:border-0 hover:bg-soft"
        >
          <td
            class="sticky left-0 bg-inherit py-3 font-mono text-xs text-faint"
          >
            {rank(agent)}
          </td>
          <td class="sticky left-8 bg-inherit py-3 pr-4 whitespace-nowrap">
            <div class="flex items-center gap-2">
              <Logo {agent} />
              <span class="text-xs text-faint max-sm:hidden"
                >{versionOf(manifest, agent)}</span
              >
            </div>
          </td>
          <td class="py-3 pr-3 text-right">{count(agent)}</td>
          {#each columns as column, i (i)}
            {@const own = value(column, agent)}
            {@const lead = leader(column) === agent}
            <td
              class={[
                "px-3 py-3 text-right whitespace-nowrap",
                i !== shown && "max-md:hidden",
              ]}
            >
              {#if own === undefined}
                <span class="text-faint">-</span>
              {:else}
                <span class={lead ? "font-medium text-accent" : ""}
                  >{column.format(own)}</span
                >
                <div class="mt-1.5 ml-auto h-0.5 w-14 bg-line">
                  <div
                    class={["ml-auto h-full", lead ? "bg-accent" : "bg-faint"]}
                    style:width="{(own / highest(column)) * 100}%"
                  ></div>
                </div>
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<ul class="mt-6 max-w-3xl space-y-2 text-sm leading-relaxed">
  {#each byLeads.filter((a) => count(a) > 0) as agent (agent)}
    <li>
      <span class="mr-1 align-[-3px]"><Logo {agent} name={false} /></span>
      {nameOf(agent)}
      <span class="text-muted"
        >is clearly lowest on {sentence(led(agent))}.</span
      >
    </li>
  {/each}
</ul>
