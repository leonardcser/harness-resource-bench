// The files the benchmark writes, as the data step copies them.

export const REPO = "https://github.com/leonardcser/harness-resource-bench";

export type Stat = { n: number; median: number; min: number; max: number };

export type Group = {
  agent: string;
  question: string;
  frontend: string;
  rate: number;
  turns: number;
  metrics: Record<string, Stat>;
};

export type Summary = { planned: number; groups: Group[] };

export type Image = {
  version: string;
  measured_version: string;
  install_bytes: number;
};

export type Manifest = {
  config: {
    versions: Record<string, string>;
    images: { agents: Record<string, Image> };
    seed: number;
  };
  machine: { cpu: string; kernel: string; podman: string };
  /** When the run started. */
  started_utc: string;
};

export type Kind = "shell" | "read" | "search" | "edit" | "write";

/** Size quantiles at `Profile["points"]`. */
export type Quantiles = number[];

export type Profile = {
  source: { turns: number; steps: number };
  points: number[];
  turn: { calls: Quantiles };
  tools: Record<
    Kind,
    { share: number; arguments_bytes: Quantiles; result_bytes: Quantiles }
  >;
};

export const KINDS: Kind[] = ["shell", "read", "search", "edit", "write"];
export const kindColor = (kind: Kind): string => `var(--kind-${kind})`;

export type Run = {
  manifest: Manifest;
  summary: Summary;
};

export type Row = { agent: string; stat: Stat };
export type Point = { x: number; stat: Stat };
export type Series = { agent: string; points: Point[] };

export async function json<T>(path: string): Promise<T> {
  const response = await fetch(`data/${path}`);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

export async function load(): Promise<Run> {
  const [manifest, summary] = await Promise.all([
    json<Manifest>("manifest.json"),
    json<Summary>("summary.json"),
  ]);
  return { manifest, summary };
}

const NAMES: Record<string, string> = {
  "claude-code": "Claude Code",
};

export const nameOf = (agent: string): string => NAMES[agent] ?? agent;

export function agentsOf(manifest: Manifest): string[] {
  return Object.keys(manifest.config.versions).sort();
}

/** The version the agent reports, such as a local build's commit. */
export function versionOf(manifest: Manifest, agent: string): string {
  const image = manifest.config.images.agents[agent];
  const reported = image?.measured_version.match(/\d+\.\d+\.\d+(?:-[\w.]+)*/);
  // A build between releases ends in its commit, shortened as git does.
  const version = reported?.[0].replace(/-([0-9a-f]{7})[0-9a-f]+$/, "-$1");
  return version ?? manifest.config.versions[agent];
}

export const colorOf = (agent: string): string =>
  `var(--agent-${agent}, var(--muted))`;

/** The group of each agent for one question and setting. If there are several
 * session lengths, it takes the longest. */
export function pick(
  summary: Summary,
  question: string,
  frontend: string,
  rate: number,
): Map<string, Group> {
  const picked = new Map<string, Group>();
  for (const group of summary.groups) {
    if (
      group.question !== question ||
      group.frontend !== frontend ||
      group.rate !== rate
    )
      continue;
    const current = picked.get(group.agent);
    if (!current || group.turns > current.turns) picked.set(group.agent, group);
  }
  return picked;
}

export function rows(groups: Map<string, Group>, metric: string): Row[] {
  return [...groups]
    .filter(([, group]) => group.metrics[metric])
    .map(([agent, group]) => ({ agent, stat: group.metrics[metric] }));
}

/** Points from metrics named `prefix` and a number. For an interval
 * (`prefix` A_B), the point is at the end of the interval. */
export function series(groups: Map<string, Group>, prefix: string): Series[] {
  const pattern = new RegExp(`^${prefix}(?:\\d+_)?(\\d+)$`);
  return [...groups].map(([agent, group]) => ({
    agent,
    points: Object.entries(group.metrics)
      .flatMap(([name, stat]) => {
        const match = name.match(pattern);
        return match ? [{ x: Number(match[1]), stat }] : [];
      })
      .sort((a, b) => a.x - b.x),
  }));
}

export const single = (value: number): Stat => ({
  n: 1,
  median: value,
  min: value,
  max: value,
});
