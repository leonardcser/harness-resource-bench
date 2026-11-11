<script lang="ts">
  import Logo from "./Logo.svelte";
  import { nameOf } from "./lib/data";
  import type { ClassValue } from "svelte/elements";
  import {
    RANKED,
    PROFILES,
    featureScore,
    releaseUrl,
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

  const LEVELS: Cell["level"][] = ["yes", "some", "no"];
  const LABELS: Record<Cell["level"], string> = {
    yes: "Yes",
    some: "In part",
    no: "No",
  };
  // Text with more to say on hover or focus.
  const more = "cursor-help underline decoration-faint decoration-dotted";
  const head = "bg-bg pt-3 shadow-[inset_0_-1px_0_var(--color-line)]";
  const table =
    "w-full min-w-[58rem] table-fixed text-[13px] whitespace-nowrap";
  let headBox = $state<HTMLDivElement>();
  let tip = $state<{ text: string; x: number; y: number } | null>(null);

  // A tap focuses the text, and the mouse hovers it. The tip stays on screen.
  function show(event: Event, text: string) {
    const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const x = Math.max(8, Math.min(box.left, innerWidth - 256 - 8));
    tip = { text, x, y: box.bottom + 6 };
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

{#snippet mark(level: Cell["level"], size = "size-1.5")}
  <i
    class={[
      size,
      "shrink-0",
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
      onpointerenter={(e) => e.pointerType === "mouse" && show(e, detail)}
      onpointerleave={(e) => e.pointerType === "mouse" && hide()}
      onfocus={(e) => show(e, detail)}
      onblur={hide}>{text}</button
    >
  {:else}
    <span class={style}>{text}</span>
  {/if}
{/snippet}

{#snippet columns()}
  <colgroup>
    <col class="w-32" />
    {#each agents as agent (agent)}<col />{/each}
  </colgroup>
{/snippet}

<!-- The header is a table of its own, so it stays under the site header while
     the body scrolls by. Where the body scrolls sideways, the header follows
     and the row names stay put. With marks, narrow screens get the compact
     list below instead. -->
<div class={[marks && "max-lg:hidden"]}>
  <div bind:this={headBox} class="sticky top-14 z-20 overflow-hidden">
    <table class={table}>
      {@render columns()}
      <thead>
        <tr>
          <th
            class={[
              head,
              "left-0 z-10 max-lg:sticky max-lg:shadow-[inset_0_-1px_0_var(--color-line),inset_-1px_0_var(--color-line)]",
            ]}
          ></th>
          {#each agents as agent (agent)}
            <th class={[head, "px-3 pb-3 text-left font-normal"]}>
              <Logo {agent} href={PROFILES[agent].repo} />
              <div
                class="mt-1 truncate text-xs text-faint"
                title={versions[agent]}
              >
                {#if versions[agent]}
                  <a
                    href={releaseUrl(agent, versions[agent])}
                    class="hover:text-muted hover:underline"
                    >{versions[agent]}</a
                  >
                {:else}
                  Not measured yet
                {/if}
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
    </table>
  </div>
  <div
    class="overflow-x-auto"
    onscroll={(e) => {
      if (headBox) headBox.scrollLeft = e.currentTarget.scrollLeft;
      hide();
    }}
  >
    <table class={table}>
      {@render columns()}
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
            <tr
              class="border-t border-line bg-bg transition-colors hover:bg-soft"
            >
              <th
                class="left-0 z-10 bg-inherit py-2 pr-4 text-left font-normal max-lg:sticky max-lg:shadow-[inset_-1px_0_var(--color-line)]"
              >
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
</div>
{#if marks}
  <!-- One mark per agent. A row opens to each agent's text. -->
  <div class="text-[13px] lg:hidden">
    <div
      class="sticky top-14 z-20 grid grid-cols-[minmax(0,1fr)_repeat(var(--n),2rem)] items-end bg-bg pt-3 pb-2 shadow-[inset_0_-1px_0_var(--color-line)]"
      style:--n={agents.length}
    >
      <span class="text-xs text-muted">Features of {total}</span>
      {#each agents as agent (agent)}
        <span class="grid justify-items-center gap-1" title={nameOf(agent)}>
          <Logo {agent} name={false} />
          <span class="text-[11px] text-muted tabular-nums"
            >{score(agent).split(" ")[0]}</span
          >
        </span>
      {/each}
    </div>
    {#each groups as group (group.label)}
      <div class="pt-6 pb-2 text-xs text-faint">{group.label}</div>
      {#each group.features as feature (feature.label)}
        <details class="group border-t border-line">
          <summary
            class="grid cursor-pointer list-none grid-cols-[minmax(0,1fr)_repeat(var(--n),2rem)] items-center py-2.5 group-open:bg-soft [&::-webkit-details-marker]:hidden"
            style:--n={agents.length}
          >
            <span class="truncate pr-2">{feature.label}</span>
            {#each agents as agent (agent)}
              {@const level = feature.cells[agent].level}
              <span class="flex justify-center"
                >{@render mark(level, "size-2")}<span class="sr-only"
                  >{nameOf(agent)}: {LABELS[level]}.</span
                ></span
              >
            {/each}
          </summary>
          <div class="space-y-2.5 pt-3 pb-4 pl-3 text-[13px]">
            {#if feature.hint}<p class="text-muted">{feature.hint}</p>{/if}
            {#each agents as agent (agent)}
              {@const cell = feature.cells[agent]}
              <div
                class="grid grid-cols-[7.5rem_minmax(0,1fr)] items-start gap-x-2"
              >
                <Logo {agent} size={12} />
                <div>
                  <div class="flex items-center gap-2">
                    {@render mark(cell.level)}
                    <span class={cell.level === "no" ? "text-faint" : ""}
                      >{cell.text}</span
                    >
                  </div>
                  {#if cell.detail}
                    <p class="mt-0.5 ml-3.5 leading-relaxed text-muted">
                      {cell.detail}
                    </p>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        </details>
      {/each}
    {/each}
  </div>
{/if}
<p class="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
  {#if marks}
    {#each LEVELS as level (level)}
      <span class="flex items-center gap-2"
        >{@render mark(level)}{LABELS[level]}</span
      >
    {/each}
  {/if}
  <span class={["text-faint", marks && "ml-auto"]}
    >{marks ? "A feature in part counts as half. " : ""}<span
      class={[marks && "max-lg:hidden"]}
      >Hover or tap dotted text for more.</span
    >{#if marks}<span class="lg:hidden">Tap a row for more.</span>{/if}</span
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
