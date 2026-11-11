<script lang="ts">
  // Each agent's mark, from its agent file, and its name. With `href`, the
  // whole is a link that shows as one only on hover.
  import { PROFILES, type Agent } from "./agents";
  import { nameOf } from "./lib/data";

  let {
    agent,
    name = true,
    size = 16,
    href,
  }: { agent: string; name?: boolean; size?: number; href?: string } = $props();
  // Ids inside a mark, such as of a gradient, are unique to each copy.
  const uid = $props.id();
  const svg = $derived(
    PROFILES[agent as Agent]?.logo.replace(/(id="|url\(#)/g, `$1${uid}-`),
  );
</script>

<svelte:element
  this={href ? "a" : "span"}
  {href}
  class="group/logo inline-flex items-center gap-2 whitespace-nowrap"
>
  <span
    class="inline-block shrink-0 text-fg [&>svg]:size-full"
    style:width="{size}px"
    style:height="{size}px"
    aria-hidden="true"
  >
    {@html svg}
  </span>
  {#if name}<span
      class={href &&
        "decoration-faint underline-offset-2 group-hover/logo:underline"}
      >{nameOf(agent)}</span
    >{/if}
</svelte:element>
