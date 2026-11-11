<script lang="ts">
  // Two idle seconds per agent: a tick each time a timer from its source
  // fires, as tall as the CPU time of one wake-up.
  import { nameOf } from "../lib/data";
  import { seconds } from "../lib/format";
  import AgentRows from "./AgentRows.svelte";

  type Timer = { ms: number; label: string };

  let {
    rates,
    timers,
  }: {
    /** Wake-ups and CPU seconds per second of idle. */
    rates: Map<string, { wakeups: number; cpu: number }>;
    timers: Record<string, Timer[]>;
  } = $props();

  const WINDOW = 2000;
  const AXIS = [0, 500, 1000, 1500, 2000];
  /** CPU/s below this is noise. Such agents tie and sort by wake-ups. */
  const FLOOR = 1e-5;
  const TALL = 26;
  const SHORT = 4;

  type BeatRow = {
    agent: string;
    perSecond: number;
    timers: Timer[];
    load: number;
    each: number;
  };
  const rows: BeatRow[] = $derived(
    [...rates]
      .map(([agent, { wakeups, cpu }]) => ({
        agent,
        perSecond: wakeups,
        timers: timers[agent] ?? [],
        load: cpu,
        // A count of zero or less means no usable count: the ticks keep the
        // timers from the source, at the lowest height.
        each: wakeups > 0 ? cpu / wakeups : 0,
      }))
      .sort(
        (a, b) =>
          Math.max(a.load, FLOOR) - Math.max(b.load, FLOOR) ||
          a.perSecond - b.perSecond,
      ),
  );
  const costliest = $derived(
    Math.max(1e-12, ...rows.filter((r) => r.timers.length).map((r) => r.each)),
  );
  const height = (each: number) =>
    SHORT + (TALL - SHORT) * Math.min(1, each / costliest);
  /** Each timer starts at its own offset, so ticks do not overlap. */
  const ticks = (timers: { ms: number }[]): number[] => {
    const shortest = Math.min(...timers.map((t) => t.ms));
    return timers.flatMap((timer, i) => {
      const out: number[] = [];
      for (
        let t = ((i + 0.5) / timers.length) * shortest;
        t < WINDOW;
        t += timer.ms
      )
        out.push(t);
      return out;
    });
  };
  const rate = (v: number) =>
    v <= 0 ? "-" : v < 10 ? v.toFixed(1) : String(Math.round(v));
  const every = (ms: number) => (ms < 1000 ? `${ms} ms` : `${ms / 1000} s`);
  const load = (v: number) => (v < FLOOR ? "< 0.01 ms" : seconds(v));
  const micro = (v: number) => `${Math.round(v * 1e6)} µs`;
</script>

{#snippet head()}
  <div></div>
  <div class="text-right text-[11px] whitespace-nowrap text-muted">
    wake-ups/s
  </div>
  <div class="text-right text-[11px] text-muted">CPU/s</div>
{/snippet}

{#snippet cells(row: BeatRow)}
  <div class="relative h-8">
    <div class="absolute inset-x-0 top-1/2 h-px bg-line"></div>
    {#each ticks(row.timers) as t, i (i)}
      <div
        class="absolute top-1/2 w-px -translate-y-1/2 bg-bar"
        style:left="{(t / WINDOW) * 100}%"
        style:height="{height(row.each)}px"
      ></div>
    {/each}
  </div>
  <div class="flex h-8 items-center justify-end text-xs tabular-nums">
    {rate(row.perSecond)}
  </div>
  <div class="flex h-8 items-center justify-end text-xs tabular-nums">
    {load(row.load)}
  </div>
{/snippet}

{#snippet foot()}
  <div class="relative h-5 text-[11px] text-muted tabular-nums">
    {#each AXIS as t (t)}
      <span
        class={[
          "absolute top-1 whitespace-nowrap",
          t === WINDOW ? "-translate-x-full" : t && "-translate-x-1/2",
          t % 1000 && "hidden sm:inline",
        ]}
        style:left="{(t / WINDOW) * 100}%">{t ? every(t) : "0"}</span
      >
    {/each}
  </div>
{/snippet}

{#snippet tip(row: BeatRow)}
  <div class="mb-1 font-medium">{nameOf(row.agent)}</div>
  {#each row.timers as timer (timer.label)}
    <div class="flex justify-between gap-4">
      <span class="text-muted">{timer.label}</span>
      <span class="tabular-nums">every {every(timer.ms)}</span>
    </div>
  {:else}
    <div class="text-muted">No timers. It waits for input.</div>
  {/each}
  <div class="mt-1 flex justify-between gap-4 border-t border-line pt-1">
    <span class="text-muted">measured</span>
    <span class="tabular-nums">{rate(row.perSecond)} wake-ups/s</span>
  </div>
  <div class="flex justify-between gap-4">
    <span class="text-muted">CPU time</span>
    <span class="tabular-nums">{load(row.load)}/s</span>
  </div>
  {#if row.load >= FLOOR && row.each > 0}
    <div class="flex justify-between gap-4">
      <span class="text-muted">per wake-up</span>
      <span class="tabular-nums">{micro(row.each)}</span>
    </div>
  {/if}
{/snippet}

<AgentRows
  {rows}
  columns="minmax(0,1fr) 3rem 4rem"
  label={(row) =>
    `${nameOf(row.agent)}: ${rate(row.perSecond)} wake-ups and ${load(row.load)} of CPU time a second`}
  {cells}
  {tip}
  {head}
  {foot}
/>
