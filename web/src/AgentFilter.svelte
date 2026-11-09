<script lang="ts">
  import { Icon } from "svelte-icons-pack";
  import { BsFunnel } from "svelte-icons-pack/bs";
  import Logo from "./Logo.svelte";
  import { AGENTS } from "./agents";
  import { filter, shown, showAll, toggle } from "./lib/filter.svelte";

  let open = $state(false);
  let box = $state<HTMLDivElement>();
  const count = $derived(AGENTS.filter(shown).length);

  function outside(event: PointerEvent) {
    if (open && !box?.contains(event.target as Node)) open = false;
  }
</script>

<svelte:window
  onpointerdown={outside}
  onkeydown={(e) => e.key === "Escape" && (open = false)}
/>

<div class="relative" bind:this={box}>
  <button
    onclick={() => (open = !open)}
    class={[
      "flex items-center gap-2 p-2 text-sm transition-colors hover:text-fg",
      filter.hidden.length ? "text-fg" : "text-muted",
    ]}
    aria-expanded={open}
    aria-haspopup="true"
  >
    <Icon src={BsFunnel} size={14} />
    <span class={["tabular-nums", count === AGENTS.length && "max-sm:sr-only"]}>
      {count === AGENTS.length ? "All agents" : `${count} of ${AGENTS.length}`}
    </span>
  </button>
  {#if open}
    <div
      class="absolute top-full right-0 mt-2 w-48 border border-line bg-bg text-xs"
      role="group"
      aria-label="Agents to show"
    >
      {#each AGENTS as agent (agent)}
        <label
          class="flex cursor-pointer items-center gap-2.5 px-2.5 py-1.5 hover:bg-soft"
        >
          <input
            type="checkbox"
            class="size-2.5 shrink-0 cursor-pointer appearance-none border border-bar checked:bg-bar focus-visible:outline focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-default"
            checked={shown(agent)}
            disabled={shown(agent) && count === 1}
            onchange={() => toggle(agent, AGENTS)}
          />
          <Logo {agent} />
        </label>
      {/each}
      <div class="border-t border-line">
        <button
          onclick={showAll}
          disabled={!filter.hidden.length}
          class="w-full px-2.5 py-1.5 text-left text-muted hover:bg-soft hover:text-fg disabled:pointer-events-none disabled:opacity-40"
        >
          Show all
        </button>
      </div>
    </div>
  {/if}
</div>
