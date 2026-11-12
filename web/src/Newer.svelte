<script lang="ts">
  import { ROOT, RUN_DATE, RUN_ID, latestRunId } from "./lib/data";

  let latest = $state<string | null>(null);
  $effect(() => {
    latestRunId().then((id) => (latest = id));
  });
</script>

{#if latest && latest !== RUN_ID}
  <div class="border-b border-line bg-soft">
    <p
      class="mx-auto max-w-6xl px-4 py-2.5 text-sm leading-relaxed text-muted sm:px-6"
    >
      This is the run of {RUN_DATE}. A newer run is available.
      <a href={ROOT} class="link">See the latest run</a>.
    </p>
  </div>
{/if}
