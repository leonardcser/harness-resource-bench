<script lang="ts">
  // Each kind's share of calls and the typical size of what it returns or
  // changes.
  import { kindColor, KINDS, type Profile } from "../lib/data";
  import { bytes } from "../lib/format";

  let { profile }: { profile: Profile } = $props();

  const median = $derived(profile.points.indexOf(0.5));
  const rows = $derived(
    KINDS.map((kind) => ({ kind, ...profile.tools[kind] })).sort(
      (a, b) => b.share - a.share,
    ),
  );
  const top = $derived(Math.max(...rows.map((r) => r.share)));
</script>

<table class="w-full text-sm tabular-nums">
  <thead>
    <tr class="border-b border-line text-xs text-muted">
      <th class="py-2 pr-4 text-left font-normal">Kind</th>
      <th class="py-2 pr-4 text-left font-normal">Share of calls</th>
      <th class="py-2 pl-4 text-right font-normal">Typical size</th>
    </tr>
  </thead>
  <tbody>
    {#each rows as row (row.kind)}
      {@const sizes =
        row.kind === "edit" || row.kind === "write"
          ? row.arguments_bytes
          : row.result_bytes}
      <tr class="border-b border-line last:border-0">
        <td class="w-28 py-2 pr-4">
          <span class="inline-flex items-center gap-2">
            <i
              class="inline-block size-2.5"
              style:background={kindColor(row.kind)}
            ></i>{row.kind}
          </span>
        </td>
        <td class="py-2 pr-4">
          <div class="flex items-center gap-2">
            <div
              class="h-2"
              style:width="{(row.share / top) * 80}%"
              style:background={kindColor(row.kind)}
            ></div>
            <span class="text-xs">{Math.round(row.share * 100)}%</span>
          </div>
        </td>
        <td class="w-28 py-2 pl-4 text-right">{bytes(sizes[median])}</td>
      </tr>
    {/each}
  </tbody>
</table>
