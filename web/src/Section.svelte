<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    description,
    wide = false,
    children,
  }: {
    title: string;
    description: string;
    /** Content under the title, at full width. */
    wide?: boolean;
    children: Snippet;
  } = $props();
</script>

<section
  class={[
    "grid gap-x-12 gap-y-6 border-t border-line py-10 sm:py-14",
    !wide && "lg:grid-cols-[13rem_1fr]",
  ]}
>
  <div class={[wide ? "max-w-xl" : "lg:sticky lg:top-24 lg:self-start"]}>
    <h2 class="text-lg font-semibold tracking-tight">{title}</h2>
    <p class="mt-2 text-sm leading-relaxed text-muted">{description}</p>
  </div>
  <div class="min-w-0">{@render children()}</div>
</section>
