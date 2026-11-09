<script lang="ts">
  import { max, min } from "d3-array";
  import { scaleLinear, scaleLog } from "d3-scale";
  import Logo from "../Logo.svelte";
  import { pointer, span } from "../lib/chart";
  import { nameOf, type Row, type Stat } from "../lib/data";
  import Tip from "./Tip.svelte";

  type Zone = { from: number; label: string };

  let {
    rows,
    format,
    zones = [],
  }: {
    rows: Row[];
    format: (v: number) => string;
    /** Bands of a log scale, from their lower bound. */
    zones?: Zone[];
  } = $props();

  let box = $state<HTMLDivElement>();
  let hover = $state<{ agent: string; x: number; y: number } | null>(null);

  const sorted = $derived(
    [...rows].sort((a, b) => a.stat.median - b.stat.median),
  );
  const top = $derived(max(rows, (r) => r.stat.max) ?? 1);
  const x = $derived(
    zones.length
      ? scaleLog()
          .domain([
            Math.min(zones[0].from, min(rows, (r) => r.stat.min) ?? 1),
            top,
          ])
          .range([0, 1])
          .clamp(true)
      : scaleLinear().domain([0, top]).range([0, 1]),
  );
  const spreads = (row: Row) => row.stat.n > 1 && row.stat.max > row.stat.min;
</script>

{#snippet whisker(s: Stat, color: string, clip: string)}
  <span
    class={[
      "pointer-events-none absolute top-1/2 h-3 -translate-y-1/2 border-x-[1.5px]",
      color,
    ]}
    style:left={span(x(s.min))}
    style:width="calc({span(x(s.max))} - {span(x(s.min))})"
    style:clip-path={clip}
    aria-hidden="true"
  >
    <span
      class="absolute inset-x-0 top-1/2 h-0 -translate-y-1/2 border-t-[1.5px] border-inherit"
    ></span>
  </span>
{/snippet}

<div
  bind:this={box}
  class="relative grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-2 text-sm sm:grid-cols-[8.5rem_minmax(0,1fr)] sm:gap-x-3"
>
  {#if zones.length}
    <div></div>
    <div class="relative h-5 text-[11px] text-muted">
      {#each zones as zone (zone.label)}
        <span
          class="absolute pl-1.5 whitespace-nowrap"
          style:left={span(x(zone.from))}>{zone.label}</span
        >
      {/each}
    </div>
  {/if}
  {#each sorted as row (row.agent)}
    {@const s = row.stat}
    <div
      class={[
        "col-span-2 grid grid-cols-subgrid transition-opacity",
        hover && hover.agent !== row.agent && "opacity-35",
      ]}
      role="img"
      aria-label="{nameOf(row.agent)}: {format(s.median)}"
      onpointermove={(e) =>
        box && (hover = { agent: row.agent, ...pointer(box, e) })}
      onpointerleave={() => (hover = null)}
    >
      <div class="flex h-8 items-center"><Logo agent={row.agent} /></div>
      <div class="relative flex h-8 items-center">
        {#each zones as zone, i (zone.label)}
          <div
            class={[
              "absolute inset-y-0 border-l border-line",
              i === 1 && "bg-fg/[0.025]",
              i === 2 && "bg-fg/[0.05]",
            ]}
            style:left={span(x(zone.from))}
            style:right={i < zones.length - 1
              ? `calc(100% - ${span(x(zones[i + 1].from))})`
              : "0"}
          ></div>
        {/each}
        <div
          class="relative h-4 shrink-0 bg-bar"
          style:width={span(x(s.median))}
        ></div>
        {#if spreads(row)}
          <!-- The whisker in the background color over the bar, and in the
               text color past its end. -->
          {@const split = (x(s.median) - x(s.min)) / (x(s.max) - x(s.min)) || 0}
          {@render whisker(
            s,
            "border-bg",
            `inset(0 ${(1 - split) * 100}% 0 0)`,
          )}
          {@render whisker(s, "border-fg", `inset(0 0 0 ${split * 100}%)`)}
        {/if}
        <span
          class="relative pl-2 text-xs whitespace-nowrap tabular-nums"
          style:margin-left="calc({span(x(Math.max(s.max, s.median)))} - {span(
            x(s.median),
          )})">{format(s.median)}</span
        >
      </div>
    </div>
  {/each}
  {#if hover}
    {@const s = sorted.find((r) => r.agent === hover!.agent)!.stat}
    <Tip x={hover.x} y={hover.y}>
      <div class="mb-1 font-medium">{nameOf(hover.agent)}</div>
      <div class="flex justify-between gap-4">
        <span class="text-muted">median</span><span class="tabular-nums"
          >{format(s.median)}</span
        >
      </div>
      {#if s.n > 1}
        <div class="flex justify-between gap-4">
          <span class="text-muted">range of {s.n} runs</span>
          <span class="tabular-nums">{format(s.min)} to {format(s.max)}</span>
        </div>
      {/if}
    </Tip>
  {/if}
</div>
