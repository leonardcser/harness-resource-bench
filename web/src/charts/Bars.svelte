<script lang="ts">
  import { max, min } from "d3-array";
  import { scaleLinear, scaleLog } from "d3-scale";
  import { span } from "../lib/chart";
  import { nameOf, type Row, type Stat } from "../lib/data";
  import AgentRows from "./AgentRows.svelte";

  type Zone = { from: number; label: string };

  let {
    rows,
    format,
    zones = [],
    first = [],
    rowsTop = $bindable(0),
  }: {
    rows: Row[];
    format: (v: number) => string;
    /** Bands of a log scale, from their lower bound. */
    zones?: Zone[];
    /** The same measure at the first launch, drawn hatched past the bar
     * where it is clearly larger. */
    first?: Row[];
    /** How far the first row is below the top of the chart, so that a chart
     * beside it can line up its rows. */
    rowsTop?: number;
  } = $props();

  let root = $state<HTMLDivElement>();
  $effect(() => {
    if (!root) return;
    const box = root;
    const observer = new ResizeObserver(() => {
      const row = box.querySelector("[data-agent]");
      rowsTop = row
        ? row.getBoundingClientRect().top - box.getBoundingClientRect().top
        : 0;
    });
    observer.observe(box);
    return () => observer.disconnect();
  });

  const firstOf = $derived(new Map(first.map((r) => [r.agent, r.stat])));
  /** The first launch's extra, where its range lies above the bar's. Within
   * the noise, there is none to draw. */
  const extra = (row: Row): Stat | undefined => {
    const stat = firstOf.get(row.agent);
    return stat && stat.min > row.stat.max ? stat : undefined;
  };
  /** Room for the value label, which is longer with an extra. */
  const room = $derived(rows.some((r) => extra(r)) ? "5.5rem" : "4.5rem");
  const at = (fraction: number) => span(fraction, room);
  const top = $derived(
    max(rows, (r) => Math.max(r.stat.max, extra(r)?.max ?? 0)) ?? 1,
  );
  /** The value, and the extra in its unit and digits, without the unit:
   * `719 ms`, `+127`. */
  const value = (s: Stat, more?: Stat): [string, string] => {
    const base = format(s.median);
    if (!more) return [base, ""];
    const number = base.slice(0, base.lastIndexOf(" "));
    const digits = number.split(".")[1]?.length ?? 0;
    const scale = Number(number) / s.median;
    return [base, `+${((more.median - s.median) * scale).toFixed(digits)}`];
  };
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
  const spreads = (s: Stat) => s.n > 1 && s.max > s.min;
</script>

{#snippet whisker(s: Stat, color: string, clip: string)}
  <span
    class={[
      "pointer-events-none absolute top-1/2 h-3 -translate-y-1/2 border-x-[1.5px]",
      color,
    ]}
    style:left={at(x(s.min))}
    style:width="calc({at(x(s.max))} - {at(x(s.min))})"
    style:clip-path={clip}
    aria-hidden="true"
  >
    <span
      class="absolute inset-x-0 top-1/2 h-0 -translate-y-1/2 border-t-[1.5px] border-inherit"
    ></span>
  </span>
{/snippet}

{#snippet head()}
  <div class="relative h-5 text-[11px] text-muted">
    {#each zones as zone (zone.label)}
      <span
        class="absolute pl-1.5 whitespace-nowrap"
        style:left={at(x(zone.from))}>{zone.label}</span
      >
    {/each}
  </div>
{/snippet}

{#snippet cells(row: Row)}
  {@const s = row.stat}
  {@const more = extra(row)}
  <!-- The whisker at the bar's end: the first launch's, where it is drawn. -->
  {@const shown = more ?? s}
  {@const end = Math.max(shown.max, shown.median)}
  {@const [label, added] = value(s, more)}
  <div class="relative flex h-8 items-center">
    {#each zones as zone, i (zone.label)}
      <div
        class={[
          "absolute inset-y-0 border-l border-line",
          i === 1 && "bg-fg/[0.025]",
          i === 2 && "bg-fg/[0.05]",
        ]}
        style:left={at(x(zone.from))}
        style:right={i < zones.length - 1
          ? `calc(100% - ${at(x(zones[i + 1].from))})`
          : "0"}
      ></div>
    {/each}
    <div
      class="relative h-4 shrink-0 bg-bar"
      style:width={at(x(s.median))}
    ></div>
    {#if more}
      <div
        class="absolute h-4"
        style:left={at(x(s.median))}
        style:width="calc({at(x(more.median))} - {at(x(s.median))})"
        style:background="var(--first-launch)"
        data-part="first"
      ></div>
    {/if}
    {#if spreads(shown)}
      <!-- The whisker in the background color over the bar, and in the
           text color past its end. -->
      {@const split =
        (x(shown.median) - x(shown.min)) / (x(shown.max) - x(shown.min)) || 0}
      {@render whisker(
        shown,
        "border-bg",
        `inset(0 ${(1 - split) * 100}% 0 0)`,
      )}
      {@render whisker(shown, "border-fg", `inset(0 0 0 ${split * 100}%)`)}
    {/if}
    <span
      class="relative pl-2 text-xs whitespace-nowrap tabular-nums"
      style:margin-left="calc({at(x(end))} - {at(x(s.median))})"
      >{label}{#if added}<span class="pl-1 text-muted">{added}</span>{/if}</span
    >
  </div>
{/snippet}

{#snippet tip(row: Row)}
  {@const s = row.stat}
  <div class="mb-1 font-medium">{nameOf(row.agent)}</div>
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
  {@const f = firstOf.get(row.agent)}
  {#if f}
    <div class="mt-1 flex justify-between gap-4">
      <span class="text-muted">first launch</span><span class="tabular-nums"
        >{format(f.median)}</span
      >
    </div>
    {#if f.n > 1}
      <div class="flex justify-between gap-4">
        <span class="text-muted">range of {f.n} runs</span>
        <span class="tabular-nums">{format(f.min)} to {format(f.max)}</span>
      </div>
    {/if}
    {#if !extra(row)}
      <div class="text-muted">The same as every launch, within the noise.</div>
    {/if}
  {/if}
{/snippet}

<div bind:this={root}>
  {#if first.length}
    <div class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      <span class="inline-flex items-center gap-1.5">
        <i class="inline-block size-2.5 bg-bar"></i>
        Every launch
      </span>
      <span class="inline-flex items-center gap-1.5">
        <i class="inline-block size-2.5" style:background="var(--first-launch)"
        ></i>
        Extra at first launch
      </span>
    </div>
  {/if}

  <AgentRows
    {rows}
    label={(row) => {
      const f = firstOf.get(row.agent);
      const at = `${nameOf(row.agent)}: ${format(row.stat.median)}`;
      return f ? `${at}, first launch ${format(f.median)}` : at;
    }}
    {cells}
    {tip}
    head={zones.length ? head : undefined}
  />
</div>
