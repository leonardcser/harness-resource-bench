<script lang="ts">
  import { ModeWatcher } from "mode-watcher";
  import { Icon } from "svelte-icons-pack";
  import { BsGithub, BsList, BsX } from "svelte-icons-pack/bs";
  import { slide } from "svelte/transition";
  import AgentFilter from "./AgentFilter.svelte";
  import Agents from "./Agents.svelte";
  import { RUN } from "./lib/data";
  import { visible } from "./lib/filter.svelte";
  import { REPO } from "./lib/site";
  import Methodology from "./Methodology.svelte";
  import Newer from "./Newer.svelte";
  import Results from "./Results.svelte";
  import ThemeToggle from "./ThemeToggle.svelte";

  const PAGES = [
    ["#/", "Results"],
    ["#/agents", "Agents"],
    ["#/methodology", "Methodology"],
  ];

  let hash = $state(location.hash || "#/");
  let menu = $state(false);
</script>

<svelte:window
  onhashchange={() => {
    hash = location.hash || "#/";
    menu = false;
  }}
  onkeydown={(e) => e.key === "Escape" && (menu = false)}
/>
<ModeWatcher />

<header class="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur">
  <div class="mx-auto flex h-14 max-w-6xl items-center gap-5 px-4 sm:px-6">
    <a
      href="#/"
      aria-label="harness resource bench"
      class="flex h-14 min-w-0 flex-wrap content-start gap-x-2 overflow-hidden text-[13px] font-semibold whitespace-nowrap sm:gap-x-2.5 sm:text-sm"
    >
      <!-- Without room, the title wraps to a hidden second line. -->
      <span class="grid h-14 content-center gap-[2px]" aria-hidden="true">
        <i class="block h-[2px] w-1 bg-fg sm:h-[3px] sm:w-1.5"></i>
        <i class="block h-[2px] w-2.5 bg-fg sm:h-[3px] sm:w-3.5"></i>
        <i class="block h-[2px] w-2 bg-fg sm:h-[3px] sm:w-2.5"></i>
      </span>
      <span class="flex h-14 items-center">harness resource bench</span>
    </a>
    <div class="hidden h-4 w-px bg-line md:block"></div>
    <nav class="hidden gap-5 text-sm font-medium md:flex">
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
    <div class="-mr-2 ml-auto flex items-center sm:gap-3">
      <AgentFilter />
      <a
        href={REPO}
        class="p-2 text-muted transition-colors hover:text-fg"
        aria-label="GitHub"
      >
        <Icon src={BsGithub} size={16} />
      </a>
      <ThemeToggle />
      <button
        onclick={() => (menu = !menu)}
        class="p-2 text-muted transition-colors hover:text-fg md:hidden"
        aria-label="Pages"
        aria-expanded={menu}
        aria-controls="pages"
      >
        <Icon src={menu ? BsX : BsList} size={18} />
      </button>
    </div>
  </div>
  {#if menu}
    <nav
      id="pages"
      class="border-t border-line px-4 py-2 sm:px-6 md:hidden"
      transition:slide={{ duration: 150 }}
    >
      {#each PAGES as [href, label] (href)}
        <a
          {href}
          class={[
            "block py-2.5 text-base font-medium transition-colors",
            hash === href ? "text-fg" : "text-muted hover:text-fg",
          ]}>{label}</a
        >
      {/each}
    </nav>
  {/if}
</header>
<Newer />

<main class="mx-auto max-w-6xl px-4 pt-8 pb-16 sm:px-6 sm:pt-12 sm:pb-24">
  {#if hash === "#/methodology"}
    <Methodology />
  {:else if hash === "#/agents"}
    <Agents run={RUN} />
  {:else}
    <Results run={visible(RUN)} />
  {/if}
</main>
