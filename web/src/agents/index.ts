// What each agent offers at the version in the benchmark. The cells come from
// the source and documentation of each agent. Claude Code is closed source, so
// its cells come from its documentation and its binary.
//
// To add an agent, add a file next to this one and list it here.
import claudeCode from "./claude-code";
import codex from "./codex";
import { FEATURES, type Cell, type FeatureId, type Profile } from "./features";
import fx from "./fx";
import omp from "./omp";
import opencode from "./opencode";
import pi from "./pi";
import smelt from "./smelt";

export type { Cell, Level } from "./features";

const profiles = {
  "claude-code": claudeCode,
  codex,
  fx,
  omp,
  opencode,
  pi,
  smelt,
};
export type Agent = keyof typeof profiles;
export const PROFILES: Record<Agent, Profile> = profiles;
export const AGENTS = Object.keys(PROFILES) as Agent[];

/** The git tag of an agent's release. */
export const tagOf = (agent: Agent, version: string): string =>
  `${PROFILES[agent].tagPrefix ?? "v"}${version}`;

/** The GitHub page of a version: its commit for a build between releases,
 * as `versionOf` shortens it, or else its release. */
export const releaseUrl = (agent: Agent, version: string): string => {
  const { repo } = PROFILES[agent];
  const commit = version.match(/-([0-9a-f]{7})$/)?.[1];
  return commit
    ? `${repo}/commit/${commit}`
    : `${repo}/releases/tag/${tagOf(agent, version)}`;
};

export type Feature = {
  label: string;
  /** What the row means, shown on hover. */
  hint?: string;
  cells: Record<Agent, Cell>;
};
export type Group = { label: string; features: Feature[] };

const GLANCE_GROUP = "At a glance";

const groups: Group[] = [];
for (const [id, info] of Object.entries(FEATURES) as [
  FeatureId,
  (typeof FEATURES)[FeatureId],
][]) {
  const feature: Feature = {
    label: info.label,
    hint: "hint" in info ? info.hint : undefined,
    cells: Object.fromEntries(
      AGENTS.map((agent) => [agent, PROFILES[agent].cells[id]]),
    ) as Record<Agent, Cell>,
  };
  const group = groups.find((g) => g.label === info.group);
  if (group) group.features.push(feature);
  else groups.push({ label: info.group, features: [feature] });
}

/** What each agent is built with and what it runs on. */
export const GLANCE: Feature[] = groups.find(
  (g) => g.label === GLANCE_GROUP,
)!.features;
/** What a user meets day to day, grouped by area. */
export const GROUPS: Group[] = groups.filter((g) => g.label !== GLANCE_GROUP);

/** Features an agent has in `groups`, with a partial one counted as half. */
export const featureScore = (agent: Agent, groups: Group[]): number =>
  groups
    .flatMap((g) => g.features)
    .reduce(
      (n, f) => n + { yes: 1, some: 0.5, no: 0 }[f.cells[agent].level],
      0,
    );

/** The agents by how many features they have, most first. Ties keep name order. */
export const RANKED: Agent[] = [...AGENTS].sort(
  (a, b) => featureScore(b, GROUPS) - featureScore(a, GROUPS),
);
