// Bars split into parts: the parts, and the rows of each chart from a run.

import type { Group, Manifest } from "./data";
import { marks } from "./data";
import { bytes } from "./format";

export type Part = {
  id: string;
  label: string;
  color: string;
  /** Parts with the same scale share it in a chart of columns. */
  scale?: string;
};

export type StackRow = {
  agent: string;
  pieces: { part: string; value: number; items?: string[] }[];
};

/** The sort key for the sum of all parts. */
export const TOTAL = "total";

export const stackValue = (row: StackRow, part = TOTAL): number =>
  part === TOTAL
    ? row.pieces.reduce((n, p) => n + p.value, 0)
    : (row.pieces.find((p) => p.part === part)?.value ?? 0);

/** Keep chart rows and their explanations in the same value order. */
export function sortStack(rows: StackRow[], part = TOTAL): StackRow[] {
  return [...rows].sort((a, b) => stackValue(a, part) - stackValue(b, part));
}

/** A curated piece. Without a value, it takes the rest of the total. */
export type Piece = { part: string; value?: number; items?: string[] };

export const INSTALL_PARTS: Part[] = [
  { id: "code", label: "Agent code", color: "var(--part-1)" },
  { id: "runtime", label: "Runtime", color: "var(--part-2)" },
  { id: "bytecode", label: "Bytecode copy", color: "var(--part-3)" },
  { id: "extra", label: "Extra binaries and data", color: "var(--part-4)" },
  { id: "other", label: "Other", color: "var(--faint)" },
  {
    id: "first",
    label: "Written at first launch",
    color: "var(--first-launch)",
  },
];

/** Session files by format, as the bench names them. */
export const SESSION_PARTS: Part[] = [
  { id: "jsonl", label: "JSONL", color: "var(--part-1)" },
  { id: "sqlite", label: "SQLite", color: "var(--part-2)" },
  { id: "wal", label: "SQLite WAL", color: "var(--part-3)" },
  { id: "json", label: "JSON", color: "var(--part-4)" },
  { id: "other", label: "Other", color: "var(--faint)" },
];

export const MEMORY_PARTS: Part[] = [
  { id: "code", label: "Code and mapped files", color: "var(--part-1)" },
  { id: "heap", label: "Heap and data", color: "var(--part-2)" },
];

export const TASK_PARTS: Part[] = [
  { id: "work", label: "Headless", color: "var(--part-1)", scale: "agent" },
  { id: "tui", label: "+ TUI", color: "var(--part-2)", scale: "agent" },
  { id: "terminal", label: "+ Terminal", color: "var(--part-3)" },
];

/** The names of the HOME folders that an agent writes at its first launch,
 * and of the rest of its files. */
export type FirstLaunchFiles = {
  folders: Record<string, string>;
  rest?: string;
};

/** Less than this at the first launch is a few small files, not drawn. */
const FIRST_LAUNCH_MIN_BYTES = 0.1 * 2 ** 20;

const median = (group: Group | undefined, metric: string) =>
  group?.metrics[metric]?.median;

/** The named files of the first launch, largest first, with their measured
 * sizes. The rest is what the named folders leave of `total`. */
function firstLaunchItems(
  group: Group | undefined,
  total: number,
  names: FirstLaunchFiles | undefined,
): string[] | undefined {
  if (!names) return undefined;
  const sized: [string, number][] = Object.entries(names.folders).map(
    ([folder, name]) => [
      name,
      median(group, `first_launch_bytes_in_${folder}`) ?? 0,
    ],
  );
  const rest = total - sized.reduce((n, [, size]) => n + size, 0);
  sized.push([names.rest ?? "other files", rest]);
  return sized
    .filter(([, size]) => size >= FIRST_LAUNCH_MIN_BYTES)
    .sort((a, b) => b[1] - a[1])
    .map(([name, size]) => `${name}, ${bytes(size)}`);
}

/** The install, split by `pieces`, and what the agent writes into its home
 * folder at the first launch of `startup`, with the `files` that it holds. */
export function installRows(
  manifest: Manifest,
  pieces: Record<string, Piece[]>,
  startup: Map<string, Group>,
  files: Record<string, FirstLaunchFiles>,
): StackRow[] {
  return Object.entries(manifest.config.images.agents).map(([agent, image]) => {
    const own = pieces[agent] ?? [{ part: "other" }];
    const known = own.reduce((n, p) => n + (p.value ?? 0), 0);
    const group = startup.get(agent);
    const first = median(group, "first_launch_bytes");
    return {
      agent,
      pieces: [
        ...own.map((p) => ({
          ...p,
          value: p.value ?? Math.max(0, image.install_bytes - known),
        })),
        ...(first && first >= FIRST_LAUNCH_MIN_BYTES
          ? [
              {
                part: "first",
                value: first,
                items: firstLaunchItems(group, first, files[agent]),
              },
            ]
          : []),
      ],
    };
  });
}

export function taskRows(
  tui: Map<string, Group>,
  headless: Map<string, Group>,
): StackRow[] {
  return [...tui].flatMap(([agent, group]) => {
    const own = median(group, "cpu_seconds");
    const work = median(headless.get(agent), "cpu_seconds");
    if (own === undefined || work === undefined) return [];
    return [
      {
        agent,
        pieces: [
          { part: "work", value: Math.min(work, own) },
          { part: "tui", value: Math.max(0, own - work) },
          {
            part: "terminal",
            value: median(group, "terminal_cpu_seconds") ?? 0,
          },
        ],
      },
    ];
  });
}

/** Idle memory split into heap and data, which is the anonymous memory, and
 * code and mapped files, which is the rest. A program that runs from the HOME
 * folder maps its code as shared memory, as the HOME is in tmpfs. */
export function memoryRows(idle: Map<string, Group>, mark: number): StackRow[] {
  return [...idle].flatMap(([agent, group]) => {
    const total = median(group, `idle_pss_bytes_after_${mark}`);
    const heap = median(group, `idle_pss_anon_bytes_after_${mark}`);
    if (total === undefined || heap === undefined) return [];
    return [
      {
        agent,
        pieces: [
          { part: "code", value: total - heap },
          { part: "heap", value: heap },
        ],
      },
    ];
  });
}

export function sessionRows(
  growth: Map<string, Group>,
  turns: number,
): StackRow[] {
  return [...growth].flatMap(([agent, group]) => {
    const pieces = SESSION_PARTS.flatMap(({ id }) => {
      const value = median(group, `session_${id}_bytes_after_${turns}`);
      return value === undefined ? [] : [{ part: id, value }];
    });
    return pieces.length ? [{ agent, pieces }] : [];
  });
}

/** CPU/s below this is noise. Such agents tie and sort by wake-ups. */
export const IDLE_CPU_FLOOR = 1e-5;
export type IdleRow = { agent: string; wakeups: number; cpu: number };

/** Wake-ups and CPU seconds per second of idle, ordered by CPU use.
 * CPU skips the first mark, while the agent settles. */
export function idleRows(idle: Map<string, Group>): IdleRow[] {
  const at = marks(idle.values(), "idle_cpu_seconds_after_");
  const [from, to] = [at.find((m) => m > 0), at.at(-1)];
  const rows: IdleRow[] = [];
  if (from === undefined || to === undefined || to <= from) return rows;
  for (const [agent, group] of idle) {
    const wakeups = median(group, "idle_wakeups_per_second");
    const a = median(group, `idle_cpu_seconds_after_${from}`);
    const b = median(group, `idle_cpu_seconds_after_${to}`);
    if (wakeups === undefined || a === undefined || b === undefined) continue;
    rows.push({ agent, wakeups, cpu: Math.max(0, b - a) / (to - from) });
  }
  return rows.sort(
    (a, b) =>
      Math.max(a.cpu, IDLE_CPU_FLOOR) - Math.max(b.cpu, IDLE_CPU_FLOOR) ||
      a.wakeups - b.wakeups,
  );
}
