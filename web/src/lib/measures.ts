// The headline measures of a run: the columns of the overview table.
import {
  agentsOf,
  marks,
  pick,
  single,
  taskRate,
  type Run,
  type Stat,
} from "./data";
import { bytes, seconds } from "./format";

export type Measure = {
  label: string;
  /** The measure in a sentence, such as "startup time". */
  name: string;
  format: (v: number) => string;
  /** The smallest difference that counts as a win, in the measure's unit. */
  floor: number;
  stat: (agent: string) => Stat | undefined;
};

export type MeasureGroup = { label: string; measures: Measure[] };

const MS = 0.005;
const MIB = 2 ** 20;

export function measures({ summary, manifest }: Run): MeasureGroup[] {
  const metric = (
    question: string,
    frontend: string,
    rate: number,
    name: (turns: number) => string,
  ) => {
    const groups = pick(summary, question, frontend, rate);
    return (agent: string) => {
      const group = groups.get(agent);
      return group?.metrics[name(group.turns)];
    };
  };
  const rate = taskRate(summary);
  const firstLaunch = metric("startup", "tui", 0, () => "first_launch_bytes");
  const lastIdle =
    marks(
      summary.groups.filter((g) => g.question === "idle"),
      "idle_cpu_seconds_after_",
    ).at(-1) ?? 0;
  return [
    {
      label: "Start",
      measures: [
        {
          label: "Startup",
          name: "startup time",
          format: seconds,
          floor: MS,
          stat: metric("startup", "tui", 0, () => "input_ready_seconds"),
        },
        {
          label: "Memory",
          name: "memory at start",
          format: bytes,
          floor: MIB,
          stat: metric("start-memory", "headless", 0, () => "pss_bytes"),
        },
        {
          label: "Install",
          name: "disk after the first launch",
          format: bytes,
          floor: MIB,
          stat: (a) => {
            const value = manifest.config.images.agents[a]?.install_bytes;
            const first = firstLaunch(a)?.median ?? 0;
            return value === undefined ? undefined : single(value + first);
          },
        },
      ],
    },
    {
      label: "Coding task",
      measures: [
        {
          label: "CPU, TUI",
          name: "CPU in the TUI",
          format: seconds,
          floor: MS,
          stat: metric("task", "tui", rate, () => "cpu_seconds"),
        },
        {
          label: "CPU, headless",
          name: "headless CPU",
          format: seconds,
          floor: MS,
          stat: metric("task", "headless", rate, () => "cpu_seconds"),
        },
        {
          label: "Terminal",
          name: "terminal CPU",
          format: seconds,
          floor: MS,
          stat: metric("task", "tui", rate, () => "terminal_cpu_seconds"),
        },
      ],
    },
    {
      label: "Long session",
      measures: [
        {
          label: "Memory",
          name: "memory in a long session",
          format: bytes,
          floor: MIB,
          stat: metric(
            "long-session",
            "tui",
            1000,
            (t) => `pss_bytes_after_${t}`,
          ),
        },
        {
          label: "Disk",
          name: "session data on disk",
          format: bytes,
          floor: MIB,
          stat: metric(
            "long-session",
            "tui",
            1000,
            (t) => `session_bytes_after_${t}`,
          ),
        },
      ],
    },
    {
      label: "Idle",
      measures: [
        {
          label: "CPU",
          name: "CPU when idle",
          format: seconds,
          floor: MS,
          stat: metric(
            "idle",
            "tui",
            1000,
            () => `idle_cpu_seconds_after_${lastIdle}`,
          ),
        },
      ],
    },
  ];
}

/** The width of a result's range, as a share of its median. */
export const spread = (stat: Stat): number =>
  stat.median === 0 ? 0 : (stat.max - stat.min) / stat.median;

export type Noise = {
  measure: Measure;
  /** The most runs of an agent. */
  runs: number;
  /** The median spread over the agents. */
  typical: number;
  largest: { agent: string; spread: number };
};

/** The spread of each measure with more than one run. */
export function noise(run: Run): Noise[] {
  return measures(run)
    .flatMap((g) => g.measures)
    .flatMap((measure) => {
      const spreads = agentsOf(run.manifest)
        .flatMap((agent) => {
          const stat = measure.stat(agent);
          return stat && stat.n > 1 ? [{ agent, spread: spread(stat) }] : [];
        })
        .sort((a, b) => a.spread - b.spread);
      const largest = spreads.at(-1);
      if (!largest) return [];
      const typical = spreads[Math.floor((spreads.length - 1) / 2)].spread;
      const runs = Math.max(
        ...agentsOf(run.manifest).map((a) => measure.stat(a)?.n ?? 0),
      );
      return [{ measure, runs, typical, largest }];
    });
}

/** The fewest and the most runs behind a result. */
export function repeats({ summary }: Run): { fewest: number; most: number } {
  const counts = summary.groups.flatMap((g) =>
    Object.values(g.metrics).map((s) => s.n),
  );
  return { fewest: Math.min(...counts), most: Math.max(...counts) };
}

/** The most time, in seconds, that the hypervisor took from an agent's CPUs
 * in any case of the run. */
export const steal = ({ summary }: Run): number =>
  Math.max(0, ...summary.groups.map((g) => g.metrics.steal_seconds?.max ?? 0));
