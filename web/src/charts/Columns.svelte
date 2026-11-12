<script lang="ts">
  // One bar column per part, each from its own baseline. Parts with the same
  // `scale` share it. A header click sorts by that column.
  import { nameOf } from "../lib/data";
  import {
    TOTAL,
    stackValue as value,
    type Part,
    type StackRow,
  } from "../lib/splits";
  import AgentRows from "./AgentRows.svelte";

  let {
    rows,
    parts,
    format,
    by,
    onsort,
  }: {
    rows: StackRow[];
    by: string;
    onsort: (part: string) => void;
    parts: Part[];
    format: (v: number) => string;
  } = $props();

  const scaleOf = (part: Part) => part.scale ?? part.id;
  const top = (part: Part) =>
    Math.max(
      1e-9,
      ...parts
        .filter((p) => scaleOf(p) === scaleOf(part))
        .flatMap((p) => rows.map((r) => value(r, p.id))),
    );
  /** A part on its own scale, while others share one. */
  const alone = (part: Part) =>
    parts.some((p) => p.scale) &&
    parts.every((p) => p === part || scaleOf(p) !== scaleOf(part));
  /** Bar columns on wider screens, before the total. */
  const bars = $derived(`repeat(${parts.length}, minmax(0, 1fr))`);
</script>

{#snippet sort(id: string, label: string, color?: string, note = false)}
  <button
    class={[
      "flex items-baseline gap-1 text-left text-xs transition-colors hover:text-fg",
      by === id ? "font-medium text-fg" : "text-muted",
      id === TOTAL && "ml-auto justify-end sm:ml-0",
    ]}
    aria-pressed={by === id}
    onclick={() => onsort(id)}
  >
    {#if color}<i
        class="inline-block size-2.5 shrink-0 self-center sm:hidden"
        style:background={color}
      ></i>{/if}
    {label}{#if by === id}<span aria-hidden="true">↓</span>{/if}
    {#if note}<span class="font-normal text-faint">(own scale)</span>{/if}
  </button>
{/snippet}

<!--
  On phones the total ends the logo line and the bars stack below it at full
  width, so the head becomes a legend.
-->
{#snippet head()}
  <div
    class="mb-2 flex flex-wrap gap-x-4 gap-y-1 sm:mb-1 sm:grid sm:grid-cols-[var(--bars)_3.5rem] sm:gap-x-3"
    style:--bars={bars}
  >
    {#each parts as part (part.id)}
      {@render sort(part.id, part.label, part.color, alone(part))}
    {/each}
    {@render sort(TOTAL, "Total")}
  </div>
{/snippet}

{#snippet total(row: StackRow)}
  <span class="text-xs font-medium tabular-nums"
    >{format(value(row, TOTAL))}</span
  >
{/snippet}

{#snippet cells(row: StackRow)}
  <div
    class="mb-3 grid gap-y-1 sm:mb-0 sm:h-8 sm:grid-cols-[var(--bars)_3.5rem] sm:gap-x-3"
    style:--bars={bars}
  >
    {#each parts as part (part.id)}
      {@const v = value(row, part.id)}
      <div
        class="flex h-4 min-w-0 items-center sm:h-auto"
        style:--share={v / top(part)}
      >
        <div
          class="h-3 w-[calc((100%-3.25rem)*var(--share))] min-w-[2px] shrink-0 sm:h-4"
          style:background={part.color}
        ></div>
        <span
          class="pl-1.5 text-[11px] whitespace-nowrap tabular-nums sm:text-xs"
          >{format(v)}</span
        >
      </div>
    {/each}
    <div class="hidden items-center justify-end sm:flex">
      {@render total(row)}
    </div>
  </div>
{/snippet}

{#snippet tip(row: StackRow)}
  <div class="mb-1 flex justify-between gap-4 font-medium">
    <span>{nameOf(row.agent)}</span>
    <span class="tabular-nums">{format(value(row, TOTAL))}</span>
  </div>
  {#each parts as part (part.id)}
    <div class="flex items-center justify-between gap-4">
      <span class="inline-flex items-center gap-1.5 text-muted">
        <i class="inline-block size-2" style:background={part.color}></i>
        {part.label}
      </span>
      <span class="tabular-nums">{format(value(row, part.id))}</span>
    </div>
  {/each}
{/snippet}

<AgentRows
  {rows}
  label={(row) =>
    `${nameOf(row.agent)}: ${parts
      .map((p) => `${p.label} ${format(value(row, p.id))}`)
      .join(", ")}`}
  {cells}
  {tip}
  {head}
  end={total}
/>
