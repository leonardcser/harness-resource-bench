<script lang="ts">
  // Horizontal bars split into parts, in the supplied row order.
  import { span } from "../lib/chart";
  import { nameOf } from "../lib/data";
  import type { Part, StackRow } from "../lib/splits";
  import AgentRows from "./AgentRows.svelte";

  let {
    rows,
    parts,
    format,
    mark,
  }: {
    rows: StackRow[];
    parts: Part[];
    format: (v: number) => string;
    /** A reference value, drawn as a line across the bars. */
    mark?: { value: number; label: string };
  } = $props();

  const total = (row: StackRow) => row.pieces.reduce((n, p) => n + p.value, 0);
  const drawn = $derived(
    rows.map((row) => ({
      ...row,
      // Pieces in the order of the legend.
      pieces: parts.flatMap((part) =>
        row.pieces.filter((p) => p.part === part.id && p.value > 0),
      ),
    })),
  );
  const top = $derived(Math.max(1e-9, mark?.value ?? 0, ...drawn.map(total)));
  const used = $derived(
    parts.filter((part) =>
      drawn.some((r) => r.pieces.some((p) => p.part === part.id)),
    ),
  );
  const partOf = (id: string) => parts.find((p) => p.id === id)!;
  const percent = (v: number, of: number) => `${Math.round((v / of) * 100)}%`;
</script>

{#snippet cells(row: StackRow)}
  {@const sum = total(row)}
  <div class="relative flex h-8 items-center">
    <div class="flex h-4 shrink-0 gap-[2px]" style:width={span(sum / top)}>
      {#each row.pieces as piece (piece.part)}
        <div
          class="h-full min-w-[2px]"
          style:flex="{piece.value / sum} 1 0"
          style:background={partOf(piece.part).color}
          data-part={piece.part}
        ></div>
      {/each}
    </div>
    <span class="pl-2 text-xs whitespace-nowrap tabular-nums"
      >{format(sum)}</span
    >
    {#if mark}
      <i
        class="pointer-events-none absolute inset-y-0 w-px bg-fg"
        style:left={span(mark.value / top)}
      ></i>
    {/if}
  </div>
{/snippet}

{#snippet tip(row: StackRow, hovered: string | null)}
  {@const sum = total(row)}
  <div class="mb-1 flex justify-between gap-4 font-medium">
    <span>{nameOf(row.agent)}</span>
    <span class="tabular-nums">{format(sum)}</span>
  </div>
  {#each row.pieces as piece (piece.part)}
    {@const part = partOf(piece.part)}
    <div
      class={[
        "flex items-center justify-between gap-4",
        hovered && hovered !== piece.part && "opacity-50",
      ]}
    >
      <span class="inline-flex items-center gap-1.5 text-muted">
        <i class="inline-block size-2" style:background={part.color}></i>
        {part.label}
      </span>
      <span class="tabular-nums"
        >{format(piece.value)} · {percent(piece.value, sum)}</span
      >
    </div>
    {#if hovered === piece.part && piece.items}
      <ul class="mb-1 ml-3.5 space-y-0.5 text-muted">
        {#each piece.items as item (item)}<li>{item}</li>{/each}
      </ul>
    {/if}
  {/each}
{/snippet}

<div class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
  {#each used as part (part.id)}
    <span class="inline-flex items-center gap-1.5">
      <i class="inline-block size-2.5" style:background={part.color}></i>
      {part.label}
    </span>
  {/each}
  {#if mark}
    <span class="inline-flex items-center gap-1.5">
      <i class="inline-block h-3 w-px bg-fg"></i>
      {mark.label}, {format(mark.value)}
    </span>
  {/if}
</div>

<AgentRows
  rows={drawn}
  label={(row) =>
    `${nameOf(row.agent)}: ${format(total(row))}, ${row.pieces
      .map((p) => `${partOf(p.part).label} ${format(p.value)}`)
      .join(", ")}`}
  {cells}
  {tip}
/>
