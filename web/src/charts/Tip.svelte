<script lang="ts">
  import type { Snippet } from "svelte";

  // x and y are percentages of the chart box. A tooltip `above` clears the
  // finger that points at it.
  let {
    x,
    y,
    above = false,
    children,
  }: { x: number; y: number; above?: boolean; children: Snippet } = $props();

  let tip = $state<HTMLElement>();
  let width = $state(0);
  // The tooltip keeps its width. It sits right of the point, or left of it when
  // that does not fit, and never leaves the chart.
  const left = $derived.by(() => {
    const box = tip?.offsetParent;
    if (!box) return 0;
    const point = (x / 100) * box.clientWidth;
    const side =
      point + 10 + width > box.clientWidth ? point - 10 - width : point + 10;
    return Math.max(0, Math.min(side, box.clientWidth - width));
  });
</script>

<div
  bind:this={tip}
  bind:offsetWidth={width}
  class="pointer-events-none absolute z-10 w-max min-w-40 border border-line bg-bg px-2.5 py-2 text-xs"
  style:left="{left}px"
  style:top="{y}%"
  style:transform="translateY({above
    ? 'calc(-100% - 32px)'
    : y > 60
      ? 'calc(-100% - 6px)'
      : '6px'})"
  role="status"
>
  {@render children()}
</div>
