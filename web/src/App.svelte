<script lang="ts">
  import { ModeWatcher } from "mode-watcher";
  import { Icon } from "svelte-icons-pack";
  import { BsGithub } from "svelte-icons-pack/bs";
  import AgentFilter from "./AgentFilter.svelte";
  import Agents from "./Agents.svelte";
  import { load, REPO } from "./lib/data";
  import { visible } from "./lib/filter.svelte";
  import Methodology from "./Methodology.svelte";
  import Results from "./Results.svelte";
  import ThemeToggle from "./ThemeToggle.svelte";

  const PAGES = [
    ["#/", "Results"],
    ["#/agents", "Agents"],
    ["#/methodology", "Methodology"],
  ];

  let hash = $state(location.hash || "#/");
  const data = load();
</script>

<svelte:window onhashchange={() => (hash = location.hash || "#/")} />
<ModeWatcher />

<header class="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur">
  <div class="mx-auto flex h-14 max-w-6xl items-center gap-5 px-6">
    <a
      href="#/"
      class="flex items-center gap-2.5 text-sm font-semibold whitespace-nowrap"
    >
      <span class="grid gap-[2px]" aria-hidden="true">
        <i class="block h-[3px] w-1.5 bg-fg"></i>
        <i class="block h-[3px] w-3.5 bg-fg"></i>
        <i class="block h-[3px] w-2.5 bg-fg"></i>
      </span>
      harness resource bench
    </a>
    <div class="h-4 w-px bg-line"></div>
    <nav class="flex gap-5 text-sm font-medium">
      {#each PAGES as [href, label] (href)}
        <a
          {href}
          class={[
            "transition-colors",
            hash === href ? "text-fg" : "text-muted hover:text-fg",
          ]}>{label}</a
        >
      {/each}
    </nav>
    <div class="ml-auto flex items-center gap-3">
      <AgentFilter />
      <a
        href={REPO}
        class="p-2 text-muted transition-colors hover:text-fg"
        aria-label="GitHub"
      >
        <Icon src={BsGithub} size={16} />
      </a>
      <ThemeToggle />
    </div>
  </div>
</header>

<main class="mx-auto max-w-6xl px-6 pt-12 pb-24">
  {#await data}
    <p class="text-muted">Loading…</p>
  {:then run}
    {#if hash === "#/methodology"}
      <Methodology />
    {:else if hash === "#/agents"}
      <Agents {run} />
    {:else}
      <Results run={visible(run)} />
    {/if}
  {:catch error}
    <p class="text-remove">Could not load the results: {error.message}</p>
  {/await}
</main>
