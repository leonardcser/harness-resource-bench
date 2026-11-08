<script lang="ts">
  import Logo from "../Logo.svelte";
  import { max } from "d3-array";
  import { scaleLinear, scaleLog } from "d3-scale";
  import { area, line } from "d3-shape";
  import { spread, thin } from "../lib/chart";
  import { colorOf, nameOf, type Point, type Series } from "../lib/data";
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
  // The end labels hold a logo of LOGO pixels, a gap, then the text.
  const LOGO = 11;
  const M = { top: 8, right: 136 + LOGO + 4, bottom: 36, left: 60 };
  let width = $state(640);
  let hover = $state<number | null>(null);

  const drawn = $derived(series.filter((s) => s.points.length));
  const xs = $derived(
    [...new Set(drawn.flatMap((s) => s.points.map((p) => p.x)))].sort(
      (a, b) => a - b,
    ),
  );
  const x = $derived(
    (log ? scaleLog().base(2) : scaleLinear())
      .domain([xs[0] ?? 0, xs.at(-1) ?? 1])
      .range([M.left, width - M.right]),
  );
  const y = $derived(
    scaleLinear()
      .domain([
        0,
        (max(drawn, (s) => max(s.points, (p) => p.stat.max)) ?? 1) / unit,
      ])
      .nice(5)
      .range([HEIGHT - M.bottom, M.top]),
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
  const labelY = $derived(
    spread(
      ends.map((p) => at(p, "median")),
      13,
      M.top,
      HEIGHT - M.bottom,
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

  function move(event: PointerEvent) {
    const px = event.offsetX;
    hover = xs.reduce((best, v) =>
      Math.abs(x(v) - px) < Math.abs(x(best) - px) ? v : best,
    );
  }
</script>

<div class="relative" bind:clientWidth={width}>
  <svg
    {width}
    height={HEIGHT}
    role="img"
    class="block overflow-visible"
    onpointermove={move}
    onpointerleave={() => (hover = null)}
  >
    {#each y.ticks(5) as tick (tick)}
      <line
        x1={M.left}
        x2={width - M.right}
        y1={y(tick)}
        y2={y(tick)}
        class="stroke-line"
      />
      <text
        x={M.left - 8}
        y={y(tick)}
        dy="0.35em"
        text-anchor="end"
        class="fill-muted text-[11px] tabular-nums">{yFormat(tick * unit)}</text
      >
    {/each}
    {#each xTicks as v (v)}
      <text
        x={x(v)}
        y={HEIGHT - M.bottom + 16}
        text-anchor="middle"
        class="fill-muted text-[11px] tabular-nums">{xFormat(v)}</text
      >
    {/each}
    <text
      x={(M.left + width - M.right) / 2}
      y={HEIGHT - 2}
      text-anchor="middle"
      class="fill-muted text-[11px]">{xLabel}</text
    >
    {#if hover !== null}
      <line
        x1={x(hover)}
        x2={x(hover)}
        y1={M.top}
        y2={HEIGHT - M.bottom}
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
      <!-- A label pushed off its line's end gets a leader back to it. -->
      {#if Math.abs(labelY[i] - at(ends[i], "median")) > 1}
        <line
          x1={width - M.right + 6}
          y1={at(ends[i], "median")}
          x2={width - M.right + 11}
          y2={labelY[i]}
          stroke={color}
          stroke-opacity="0.6"
        />
      {/if}
      <foreignObject
        x={width - M.right + 13}
        y={labelY[i] - LOGO / 2}
        width={LOGO}
        height={LOGO}
      >
        <div class="flex size-full leading-none">
          <Logo agent={s.agent} name={false} size={LOGO} />
        </div>
      </foreignObject>
      <text
        x={width - M.right + 13 + LOGO + 4}
        y={labelY[i]}
        dy="0.35em"
        class="text-[11px]"
      >
        <tspan fill={color}>{nameOf(s.agent)}</tspan>
        <tspan class="fill-muted tabular-nums"
          >{yFormat(ends[i].stat.median)}</tspan
        >
      </text>
    {/each}
  </svg>
  {#if hover !== null && values.length}
    <Tip x={((x(hover) + 12) / width) * 100} y={10}>
      <div class="mb-1 text-muted">{xLabel} {xFormat(hover)}</div>
      {#each values as r (r.agent)}
        <div class="flex justify-between gap-4">
          <span style:color={colorOf(r.agent)}>{nameOf(r.agent)}</span>
          <span class="tabular-nums">{yFormat(r.point!.stat.median)}</span>
        </div>
      {/each}
    </Tip>
  {/if}
</div>
