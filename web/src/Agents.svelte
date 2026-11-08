<script lang="ts">
  import Logo from "./Logo.svelte";
  import Matrix from "./Matrix.svelte";
  import Section from "./Section.svelte";
  import { AGENTS, GLANCE, GROUPS, PROFILES, RANKED } from "./agents";
  import { versionOf, type Run } from "./lib/data";
  import { shown } from "./lib/filter.svelte";

  let { run }: { run: Run } = $props();

  const versions = $derived(
    Object.fromEntries(AGENTS.map((a) => [a, versionOf(run.manifest, a)])),
  );
</script>

<svelte:head>
  <title>The agents - Harness resource bench</title>
  <meta
    name="description"
    content="What Claude Code, Codex, fx, omp, opencode, pi and smelt support."
  />
</svelte:head>

<div class="max-w-3xl">
  <h1 class="text-3xl font-semibold tracking-tight">The agents</h1>
  <p class="mt-4 leading-relaxed text-muted">What each agent supports.</p>
</div>

<div class="mt-14">
  <Section
    title="At a glance"
    description="What each agent is built with and what it runs on."
    wide
  >
    <Matrix
      groups={[{ label: "", features: GLANCE }]}
      {versions}
      marks={false}
    />
  </Section>

  <Section
    title="Features"
    description="What a user meets day to day, grouped by area."
    wide
  >
    <Matrix groups={GROUPS} {versions} />
  </Section>

  <Section title="How they differ" description="Each agent in a few words.">
    <div class="grid gap-x-10 gap-y-8 sm:grid-cols-2 xl:grid-cols-3">
      {#each RANKED.filter(shown) as agent (agent)}
        {@const profile = PROFILES[agent]}
        <article>
          <Logo {agent} />
          <h3 class="mt-3 text-sm font-medium">{profile.tagline}</h3>
          <p class="mt-2 text-sm leading-relaxed text-muted">{profile.text}</p>
        </article>
      {/each}
    </div>
  </Section>
</div>

<p class="border-t border-line pt-6 text-xs leading-relaxed text-muted">
  Checked in November 2026 against the versions in the benchmark. Agents change
  fast, so a row can be out of date. Corrections are welcome on GitHub. I build
  smelt, so keep that in mind when you read its rows.
</p>
