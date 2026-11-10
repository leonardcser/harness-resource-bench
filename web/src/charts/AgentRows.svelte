<script lang="ts" generics="R extends { agent: string }">
  // One row per agent: its logo, then the chart's cells. Hover dims the other
  // rows and shows a tooltip. Head and foot rows align with the cells.
  import type { Snippet } from "svelte";
  import Logo from "../Logo.svelte";
  import { pointer } from "../lib/chart";
  import Tip from "./Tip.svelte";

  let {
    rows,
    columns = "minmax(0,1fr)",
    label,
    cells,
    tip,
    head,
    foot,
    end,
  }: {
    rows: R[];
    /** Grid columns after the logo. */
    columns?: string;
    label: (row: R) => string;
    cells: Snippet<[R]>;
    /** The hovered row, and the `data-part` of the hovered element. */
    tip: Snippet<[R, string | null]>;
    head?: Snippet;
    foot?: Snippet;
    /**
     * On phones, the logo takes its own line, which ends with this, and the
     * cells get the full width below it.
     */
    end?: Snippet<[R]>;
  } = $props();

  let box = $state<HTMLDivElement>();
  let hover = $state<{
    row: R;
    part: string | null;
    x: number;
    y: number;
  } | null>(null);
</script>

{#snippet line(content: Snippet)}
  <div class="col-span-full grid grid-cols-subgrid">
    <div></div>
    {@render content()}
  </div>
{/snippet}

<div
  bind:this={box}
  class={[
    "relative grid gap-x-2 text-sm sm:grid-cols-[8.5rem_var(--columns)] sm:gap-x-3",
    end ? "grid-cols-[var(--columns)]" : "grid-cols-[6.5rem_var(--columns)]",
  ]}
  style:--columns={columns}
>
  {#if head}{@render line(head)}{/if}
  {#each rows as row (row.agent)}
    <div
      class={[
        "col-span-full grid grid-cols-subgrid transition-opacity",
        hover && hover.row.agent !== row.agent && "opacity-35",
      ]}
      role="img"
      aria-label={label(row)}
      onpointermove={(e) =>
        box &&
        (hover = {
          row,
          part:
            (e.target as HTMLElement).closest<HTMLElement>("[data-part]")
              ?.dataset.part ?? null,
          ...pointer(box, e),
        })}
      onpointerleave={() => (hover = null)}
    >
      <div
        class={[
          "flex items-center justify-between sm:h-8",
          end ? "h-7" : "h-8",
        ]}
      >
        <Logo agent={row.agent} />
        {#if end}<div class="sm:hidden">{@render end(row)}</div>{/if}
      </div>
      {@render cells(row)}
    </div>
  {/each}
  {#if foot}{@render line(foot)}{/if}
  {#if hover}
    <Tip x={hover.x} y={hover.y}>{@render tip(hover.row, hover.part)}</Tip>
  {/if}
</div>
