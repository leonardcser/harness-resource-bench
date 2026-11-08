<script lang="ts">
  import Logo from "./Logo.svelte";
  import type { ClassValue } from "svelte/elements";
  import {
    RANKED,
    featureScore,
    type Agent,
    type Cell,
    type Group,
  } from "./agents";
  import { shown } from "./lib/filter.svelte";

  let {
    groups,
    versions,
    marks = true,
  }: {
    groups: Group[];
    versions: Record<string, string>;
    /** Show how fully each agent has a feature, not only the text. */
    marks?: boolean;
  } = $props();

  const LEGEND: [Cell["level"], string][] = [
    ["yes", "Yes"],
    ["some", "In part"],
    ["no", "No"],
  ];
  // Text with more to say on hover or focus.
  const more = "cursor-help underline decoration-faint decoration-dotted";
  // Header cells stay under the site header while the table scrolls by.
  const head =
    "z-20 bg-bg pt-3 shadow-[inset_0_-1px_0_var(--color-line)] lg:sticky lg:top-14";
  let tip = $state<{ text: string; x: number; y: number } | null>(null);

  function show(event: Event, text: string) {
    const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
    tip = { text, x: box.left, y: box.bottom + 6 };
  }
  const hide = () => (tip = null);

  const agents = $derived(RANKED.filter(shown));
  const total = $derived(groups.reduce((n, g) => n + g.features.length, 0));
  const score = (agent: Agent) => {
    const n = featureScore(agent, groups);
    return `${Math.floor(n)}${n % 1 ? "½" : ""} of ${total}`;
  };
</script>

<svelte:window onscroll={hide} />

{#snippet mark(level: Cell["level"])}
  <i
    class={[
      "size-1.5 shrink-0",
      level === "yes" && "bg-bar",
      level === "some" && "border border-bar",
      level === "no" && "bg-line",
    ]}
  ></i>
{/snippet}

{#snippet hinted(text: string, detail: string | undefined, style: ClassValue)}
  {#if detail}
    <button
      type="button"
      class={[style, more, "max-w-full text-left"]}
      aria-label="{text}: {detail}"
      onpointerenter={(e) => show(e, detail)}
      onpointerleave={hide}
      onfocus={(e) => show(e, detail)}
      onblur={hide}>{text}</button
    >
  {:else}
    <span class={style}>{text}</span>
  {/if}
{/snippet}

<!-- Where the table fits, it does not scroll, so its header can stick. -->
<div class="overflow-x-auto lg:overflow-visible">
  <table class="w-full min-w-[58rem] table-fixed text-[13px] whitespace-nowrap">
    <colgroup>
      <col class="w-32" />
      {#each agents as agent (agent)}<col />{/each}
    </colgroup>
    <thead>
      <tr>
        <th class={head}></th>
        {#each agents as agent (agent)}
          <th class={[head, "px-3 pb-3 text-left font-normal"]}>
            <Logo {agent} />
            <div
              class="mt-1 truncate text-xs text-faint"
              title={versions[agent]}
            >
              {versions[agent] ?? "Not measured yet"}
            </div>
            {#if marks}
              <div class="mt-0.5 text-xs text-muted tabular-nums">
                {score(agent)}
              </div>
            {/if}
          </th>
        {/each}
      </tr>
    </thead>
    {#each groups as group (group.label)}
      <tbody>
        {#if group.label}
          <tr>
            <th
              colspan={agents.length + 1}
              class="pt-6 pb-2 text-left text-xs font-normal text-faint"
            >
              {group.label}
            </th>
          </tr>
        {/if}
        {#each group.features as feature (feature.label)}
          <tr class="border-t border-line transition-colors hover:bg-soft">
            <th class="py-2 pr-4 text-left font-normal">
              {@render hinted(feature.label, feature.hint, "")}
            </th>
            {#each agents as agent (agent)}
              {@const cell = feature.cells[agent]}
              <td class="px-3 py-2">
                <div class="flex items-center gap-2">
                  {#if marks}{@render mark(cell.level)}{/if}
                  {@render hinted(cell.text, cell.detail, [
                    "truncate",
                    cell.level === "no"
                      ? "text-faint"
                      : marks
                        ? "text-muted"
                        : "text-fg",
                  ])}
                </div>
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    {/each}
  </table>
</div>
<p class="mt-4 flex items-center gap-5 text-xs text-muted">
  {#if marks}
    {#each LEGEND as [level, label] (level)}
      <span class="flex items-center gap-2">{@render mark(level)}{label}</span>
    {/each}
  {/if}
  <span class={["text-faint", marks && "ml-auto"]}
    >{marks ? "A feature in part counts as half. " : ""}Hover dotted text for
    more.</span
  >
</p>
{#if tip}
  <div
    class="pointer-events-none fixed z-40 max-w-64 border border-line bg-bg px-2.5 py-2 text-xs leading-relaxed text-fg"
    style:left="{tip.x}px"
    style:top="{tip.y}px"
    role="tooltip"
  >
    {tip.text}
  </div>
{/if}
