<script lang="ts">
  // The causes behind a chart, folded under it. Each agent gets its class and
  // one sentence, with the source line where there is one.
  import type { Snippet } from "svelte";
  import type { Topic } from "./findings";
  import { shown } from "./lib/filter.svelte";
  import Logo from "./Logo.svelte";

  let {
    topic,
    rule = "",
    children,
  }: {
    topic: Topic;
    /** Classes for the rule above the panel, such as a width. */
    rule?: string;
    children?: Snippet;
  } = $props();

  const rows = $derived(
    Object.entries(topic.causes)
      .filter(([agent]) => shown(agent))
      .map(([agent, cause]) => ({ agent, cause }))
      .sort(
        (a, b) =>
          topic.tags.indexOf(a.cause.tag) - topic.tags.indexOf(b.cause.tag),
      ),
  );
  // Each class once, in order, with the agents in it.
  const classes = $derived(
    topic.tags.filter((tag) => rows.some((r) => r.cause.tag === tag)),
  );
</script>

{#snippet tag(label: string)}
  <span class="inline-block border border-line px-1.5 text-[11px] text-fg"
    >{label}</span
  >
{/snippet}

<div class={["mt-4 border-t border-line", rule]}></div>
<details class="group pt-3">
  <summary
    class="flex cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted transition-colors select-none hover:text-fg [&::-webkit-details-marker]:hidden"
  >
    <span class="inline-block w-2 transition-transform group-open:rotate-90"
      >›</span
    >
    <span class="font-medium text-fg">Why</span>
    {#each classes as tag (tag)}
      <span class="border border-line px-1.5 py-px text-[11px]">{tag}</span>
    {/each}
  </summary>
  <!-- On phones an agent and its class share a line above the text. -->
  <div
    class="mt-3 grid gap-y-4 text-sm sm:grid-cols-[8.5rem_max-content_minmax(0,1fr)] sm:gap-x-3 sm:gap-y-2.5"
  >
    {#each rows as { agent, cause } (agent)}
      <div class="space-y-1 sm:contents">
        <div class="flex items-center justify-between gap-2 sm:contents">
          <div class="flex items-start"><Logo {agent} /></div>
          <div class="sm:pt-0.5">{@render tag(cause.tag)}</div>
        </div>
        <p class="text-xs leading-relaxed text-muted sm:pt-0.5">
          {cause.text}
          {#if cause.source?.href}
            <a
              href={cause.source.href}
              class="font-mono text-[11px] whitespace-nowrap text-accent hover:underline"
              >{cause.source.label}</a
            >
          {:else if cause.source}
            <span class="font-mono text-[11px] whitespace-nowrap text-faint"
              >{cause.source.label}</span
            >
          {/if}
        </p>
      </div>
    {/each}
  </div>
  {#if topic.note}
    <p class="mt-4 text-xs leading-relaxed text-muted">{topic.note}</p>
  {/if}
  {#if children}<div class="mt-5">{@render children()}</div>{/if}
</details>
