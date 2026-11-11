// The files the benchmark writes, as the data step copies them. The site
// bundles them, so they are there on the first frame.
import manifest from "../data/manifest.json";
import profile from "../data/profile.json";
import run from "../data/run.json";
import summary from "../data/summary.json";

/** The ID of the run, the name of its folder in results/. */
export const RUN_ID: string = run.id;
/** The day the run started, as YYYY-MM-DD. */
export const RUN_DATE: string = run.date;

/** The path from this page to the root of the site. */
export const ROOT = __ROOT__;

/** The page of this run, which never changes once the run is frozen. */
export const PERMALINK = `${ROOT}runs/${RUN_ID}/`;

/** The ID of the run that the root of the site shows, from the build. It is
 * null when that is unknown, as in development. */
export async function latestRunId(): Promise<string | null> {
  try {
    const response = await fetch(`${ROOT}runs.json`, { cache: "no-cache" });
    if (!response.ok) return null;
    const { latest } = (await response.json()) as { latest?: unknown };
    return typeof latest === "string" ? latest : null;
  } catch {
    return null;
  }
}

/** The clock of the benchmark VM's reserved cores, in GHz, which the host
 * hook in bench/proxmox sets. */
export const CLOCK_GHZ = 4.7;

export type Stat = { n: number; median: number; min: number; max: number };

export type Group = {
  agent: string;
  question: string;
  frontend: string;
  rate: number;
  turns: number;
  metrics: Record<string, Stat>;
};

export type Summary = {
  planned: number;
  groups: Group[];
  /** The fixed job before every case, if the run has one. */
  canary?: Stat | null;
};

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
  /** The commit of the code that measured the run, if the run recorded it. */
  commit?: string;
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

export const RUN: Run = {
  manifest: manifest as unknown as Manifest,
  summary: summary as unknown as Summary,
};
export const PROFILE = profile as unknown as Profile;

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

/** The streaming rate of the coding task, in tokens per second: the rate of
 * its headless runs, which also picks the TUI runs that the site shows. */
export const taskRate = (summary: Summary): number =>
  summary.groups.find((g) => g.question === "task" && g.frontend === "headless")
    ?.rate ?? 0;

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

/** The sorted numbers N of the metrics named `prefix` N in any group. */
export function marks(groups: Iterable<Group>, prefix: string): number[] {
  const pattern = new RegExp(`^${prefix}(\\d+)$`);
  const found = new Set<number>();
  for (const group of groups)
    for (const name of Object.keys(group.metrics)) {
      const match = name.match(pattern);
      if (match) found.add(Number(match[1]));
    }
  return [...found].sort((a, b) => a - b);
}

export const single = (value: number): Stat => ({
  n: 1,
  median: value,
  min: value,
  max: value,
});
