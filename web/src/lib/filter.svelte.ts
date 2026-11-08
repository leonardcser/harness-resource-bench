// The agents that the reader hides, on every page. The choice stays across
// pages and visits.
import type { Manifest, Run } from "./data";

const KEY = "hidden-agents";

function saved(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export const filter = $state({ hidden: saved() });

export const shown = (agent: string): boolean => !filter.hidden.includes(agent);

function store(hidden: string[]) {
  filter.hidden = hidden;
  localStorage.setItem(KEY, JSON.stringify(hidden));
}

/** Show or hide an agent. The last shown agent of `all` stays shown. */
export function toggle(agent: string, all: readonly string[]) {
  if (!shown(agent)) store(filter.hidden.filter((a) => a !== agent));
  else if (all.filter(shown).length > 1) store([...filter.hidden, agent]);
}

export const showAll = () => store([]);

/** The run with the hidden agents left out. */
export function visible(run: Run): Run {
  const keep = <T>(record: Record<string, T>) =>
    Object.fromEntries(Object.entries(record).filter(([a]) => shown(a)));
  const config: Manifest["config"] = {
    ...run.manifest.config,
    versions: keep(run.manifest.config.versions),
    images: { agents: keep(run.manifest.config.images.agents) },
  };
  return {
    ...run,
    manifest: { ...run.manifest, config },
    summary: {
      ...run.summary,
      groups: run.summary.groups.filter((g) => shown(g.agent)),
    },
  };
}
