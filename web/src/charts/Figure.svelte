<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    note = "",
    children,
  }: { title: string; note?: string; children: Snippet } = $props();
</script>

<figure>
  <h3 class="mb-3 text-sm font-medium">{title}</h3>
  {@render children()}
  {#if note}<figcaption class="mt-3 text-xs leading-relaxed text-muted">
      {note}
    </figcaption>{/if}
</figure>
