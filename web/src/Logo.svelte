<script lang="ts">
  // Each agent's mark, from its agent file, and its name.
  import { PROFILES, type Agent } from "./agents";
  import { nameOf } from "./lib/data";

  let {
    agent,
    name = true,
    size = 16,
  }: { agent: string; name?: boolean; size?: number } = $props();
  // Ids inside a mark, such as of a gradient, are unique to each copy.
  const uid = $props.id();
  const svg = $derived(
    PROFILES[agent as Agent]?.logo.replace(/(id="|url\(#)/g, `$1${uid}-`),
  );
</script>

<span class="inline-flex items-center gap-2 whitespace-nowrap">
  <span
    class="inline-block shrink-0 text-fg [&>svg]:size-full"
    style:width="{size}px"
    style:height="{size}px"
    aria-hidden="true"
  >
    {@html svg}
  </span>
  {#if name}<span>{nameOf(agent)}</span>{/if}
</span>
