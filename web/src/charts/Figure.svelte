<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    note = "",
    children,
    more,
  }: {
    title: string;
    note?: string;
    children: Snippet;
    /** More to read after the note, such as the causes behind the chart. */
    more?: Snippet;
  } = $props();
</script>

<figure>
  <h3 class="mb-3 text-sm font-medium">{title}</h3>
  {@render children()}
  {#if note}<figcaption
      class="mt-3 text-[13px] leading-relaxed text-muted sm:text-xs"
    >
      {note}
    </figcaption>{/if}
  {@render more?.()}
</figure>
