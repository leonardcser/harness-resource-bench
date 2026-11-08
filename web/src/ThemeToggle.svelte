<script lang="ts">
  import { mode, toggleMode } from "mode-watcher";
  import { Icon } from "svelte-icons-pack";
  import { IoMoon, IoSunny } from "svelte-icons-pack/io";
  import { slide } from "svelte/transition";
</script>

<button
  onclick={toggleMode}
  class="relative flex w-fit min-w-8 items-center p-2 text-muted transition-colors hover:text-fg"
  aria-label="Toggle theme"
>
  {#if mode.current === "dark"}
    <div transition:slide={{ duration: 200 }} class="absolute left-2">
      <Icon src={IoMoon} size={16} />
    </div>
  {:else}
    <div transition:slide={{ duration: 200 }} class="absolute left-2">
      <Icon src={IoSunny} size={16} />
    </div>
  {/if}
</button>
