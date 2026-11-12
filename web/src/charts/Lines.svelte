<script lang="ts">
  import Logo from "../Logo.svelte";
  import { max } from "d3-array";
  import { scaleLinear, scaleLog } from "d3-scale";
  import { area, line } from "d3-shape";
  import { spread, textWidth, thin } from "../lib/chart";
  import { colorOf, nameOf, type Point, type Series } from "../lib/data";
  import { scrub } from "../lib/scrub";
  import Tip from "./Tip.svelte";

  let {
    series,
    xLabel,
    xFormat = String,
    yFormat,
    log = false,
    unit = 1,
  }: {
    series: Series[];
    xLabel: string;
    xFormat?: (v: number) => string;
    yFormat: (v: number) => string;
    log?: boolean;
    /** Ticks fall on round multiples of this, such as 2**20 for MiB. */
    unit?: number;
  } = $props();

  const HEIGHT = 240;
  const TOP = 8;
  const BOTTOM = 36;
  // Wide charts label each line at its end: a logo of LOGO pixels, a gap, then
  // the text, in a column of END pixels.
  const LOGO = 11;
  const END = 136 + LOGO + 4;
  let width = $state(640);
  // Narrow charts show a legend below instead, to keep the plot wide.
  const compact = $derived(width < 520);
  let hover = $state<number | null>(null);

  const drawn = $derived(series.filter((s) => s.points.length));
  const xs = $derived(
    [...new Set(drawn.flatMap((s) => s.points.map((p) => p.x)))].sort(
      (a, b) => a - b,
    ),
  );
  const y = $derived(
    scaleLinear()
      .domain([
        0,
        (max(drawn, (s) => max(s.points, (p) => p.stat.max)) ?? 1) / unit,
      ])
      .nice(5)
      .range([HEIGHT - BOTTOM, TOP]),
  );
  const yTicks = $derived(y.ticks(5));
  // The plot leaves room for the widest y label, and on narrow charts for half
  // of the last x label, which is centered on its point.
  const left = $derived(
    Math.ceil(max(yTicks, (t) => textWidth(yFormat(t * unit))) ?? 0) + 8,
  );
  const right = $derived(
    compact ? Math.ceil(textWidth(xFormat(xs.at(-1) ?? 0)) / 2) : END,
  );
  const x = $derived(
    (log ? scaleLog().base(2) : scaleLinear())
      .domain([xs[0] ?? 0, xs.at(-1) ?? 1])
      .range([left, width - right]),
  );
  const at = (p: Point, key: "median" | "min" | "max") => y(p.stat[key] / unit);
  const path = $derived(
    line<Point>()
      .x((p) => x(p.x))
      .y((p) => at(p, "median")),
  );
  const band = $derived(
    area<Point>()
      .x((p) => x(p.x))
      .y0((p) => at(p, "min"))
      .y1((p) => at(p, "max")),
  );
  const ends = $derived(drawn.map((s) => s.points.at(-1)!));
  const legend = $derived(
    [...drawn].sort(
      (a, b) => b.points.at(-1)!.stat.median - a.points.at(-1)!.stat.median,
    ),
  );
  const summary = $derived(
    `At ${xLabel} ${xFormat(xs.at(-1) ?? 0)}: ` +
      legend
        .map(
          (s) => `${nameOf(s.agent)} ${yFormat(s.points.at(-1)!.stat.median)}`,
        )
        .join(", "),
  );
  const labelY = $derived(
    spread(
      ends.map((p) => at(p, "median")),
      13,
      TOP,
      HEIGHT - BOTTOM,
    ),
  );
  const xTicks = $derived(thin(xs, (v) => x(v), 34));
  const values = $derived(
    hover === null
      ? []
      : drawn
          .map((s) => ({
            agent: s.agent,
            point: s.points.find((p) => p.x === hover),
          }))
          .filter((r) => r.point)
          .sort((a, b) => b.point!.stat.median - a.point!.stat.median),
  );

  const nearest = (px: number) =>
    xs.reduce((best, v) =>
      Math.abs(x(v) - px) < Math.abs(x(best) - px) ? v : best,
    );
</script>

{#snippet swatch(agent: string)}
  <i class="h-0.5 w-2.5 shrink-0" style:background={colorOf(agent)}></i>
{/snippet}

<div class="relative" bind:clientWidth={width}>
  <svg
    {width}
    height={HEIGHT}
    role="img"
    aria-label={summary}
    class="block overflow-visible"
    {@attach scrub(
      (p) => (hover = nearest(p.x)),
      () => (hover = null),
    )}
  >
    {#each yTicks as tick (tick)}
      <line
        x1={left}
        x2={width - right}
        y1={y(tick)}
        y2={y(tick)}
        class="stroke-line"
      />
      <text
        x={left - 8}
        y={y(tick)}
        dy="0.35em"
        text-anchor="end"
        class="fill-muted text-[11px] tabular-nums">{yFormat(tick * unit)}</text
      >
    {/each}
    {#each xTicks as v (v)}
      <text
        x={x(v)}
        y={HEIGHT - BOTTOM + 16}
        text-anchor="middle"
        class="fill-muted text-[11px] tabular-nums">{xFormat(v)}</text
      >
    {/each}
    <text
      x={(left + width - right) / 2}
      y={HEIGHT - 2}
      text-anchor="middle"
      class="fill-muted text-[11px]">{xLabel}</text
    >
    {#if hover !== null}
      <line
        x1={x(hover)}
        x2={x(hover)}
        y1={TOP}
        y2={HEIGHT - BOTTOM}
        class="stroke-muted"
      />
    {/if}
    {#each drawn as s, i (s.agent)}
      {@const color = colorOf(s.agent)}
      <path d={band(s.points)} fill={color} fill-opacity="0.08" />
      <path
        d={path(s.points)}
        fill="none"
        stroke={color}
        stroke-width="2"
        stroke-linejoin="round"
      />
      {#each s.points as p (p.x)}
        <circle
          cx={x(p.x)}
          cy={at(p, "median")}
          r="3"
          fill={color}
          class="stroke-bg"
          stroke-width="2"
        />
      {/each}
      {#if !compact}
        <!-- A label pushed off its line's end gets a leader back to it. -->
        {#if Math.abs(labelY[i] - at(ends[i], "median")) > 1}
          <line
            x1={width - right + 6}
            y1={at(ends[i], "median")}
            x2={width - right + 11}
            y2={labelY[i]}
            stroke={color}
            stroke-opacity="0.6"
          />
        {/if}
        <foreignObject
          x={width - right + 13}
          y={labelY[i] - LOGO / 2}
          width={LOGO}
          height={LOGO}
        >
          <div class="flex size-full leading-none">
            <Logo agent={s.agent} name={false} size={LOGO} />
          </div>
        </foreignObject>
        <text
          x={width - right + 13 + LOGO + 4}
          y={labelY[i]}
          dy="0.35em"
          class="text-[11px]"
        >
          <tspan class="fill-fg">{nameOf(s.agent)}</tspan>
          <tspan class="fill-muted tabular-nums"
            >{yFormat(ends[i].stat.median)}</tspan
          >
        </text>
      {/if}
    {/each}
  </svg>
  {#if hover !== null && values.length}
    <Tip x={((x(hover) + 12) / width) * 100} y={10}>
      <div class="mb-1 text-muted">{xLabel} {xFormat(hover)}</div>
      {#each values as r (r.agent)}
        <div class="flex justify-between gap-4">
          <span class="flex items-center gap-1.5"
            >{@render swatch(r.agent)}{nameOf(r.agent)}</span
          >
          <span class="tabular-nums">{yFormat(r.point!.stat.median)}</span>
        </div>
      {/each}
    </Tip>
  {/if}
</div>
{#if compact}
  <ul
    class="mt-3 grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-x-6 gap-y-1.5 text-xs"
  >
    {#each legend as s (s.agent)}
      <li class="flex items-center gap-1.5 whitespace-nowrap">
        {@render swatch(s.agent)}
        <Logo agent={s.agent} name={false} size={12} />
        <span>{nameOf(s.agent)}</span>
        <span class="ml-auto text-muted tabular-nums"
          >{yFormat(s.points.at(-1)!.stat.median)}</span
        >
      </li>
    {/each}
  </ul>
{/if}
