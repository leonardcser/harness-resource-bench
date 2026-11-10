// Copies the run that results/published.json names into src/data, which the
// site imports at build time: its results and the profile of its workload.
// It keeps only the fields that the site reads, as the site bundles them.
// Files change only when their content does, so a dev server reloads once.
import { mkdir, readdir, rm } from "node:fs/promises";

const results = new URL("../../results/", import.meta.url).pathname;
const out = new URL("../src/data/", import.meta.url).pathname;

const pointer = Bun.file(`${results}published.json`);
if (!(await pointer.exists())) {
  throw new Error(`No published.json in ${results}. Run: uv run bench.py run`);
}
const { run } = (await pointer.json()) as { run: string };

type Json = Record<string, any>;
const pick = (o: Json, ...keys: string[]) =>
  Object.fromEntries(keys.map((k) => [k, o[k]]));
const map = (o: Json, f: (v: Json) => Json) =>
  Object.fromEntries(Object.entries(o).map(([k, v]) => [k, f(v)]));

// The fields of each file that src/lib/data.ts declares.
const TRIM: Record<string, (o: Json) => Json> = {
  "manifest.json": (m) => ({
    config: {
      versions: m.config.versions,
      images: {
        agents: map(m.config.images.agents, (a) =>
          pick(a, "version", "measured_version", "install_bytes"),
        ),
      },
      seed: m.config.seed,
    },
    machine: pick(m.machine, "cpu", "kernel", "podman"),
    started_utc: m.started_utc,
  }),
  "summary.json": (s) => pick(s, "planned", "groups", "canary"),
  "profile.json": (p) => p,
};

const files = new Map<string, string>();
for (const [name, trim] of Object.entries(TRIM)) {
  const file = Bun.file(`${results}${run}/${name}`);
  if (!(await file.exists())) {
    throw new Error(`No ${name} in ${results}${run}`);
  }
  files.set(name, JSON.stringify(trim(await file.json())));
}

await mkdir(out, { recursive: true });
for (const [name, content] of files) {
  const file = Bun.file(out + name);
  if ((await file.exists()) && (await file.text()) === content) continue;
  await Bun.write(file, content);
}
for (const name of await readdir(out)) {
  if (!files.has(name)) await rm(out + name, { recursive: true, force: true });
}
console.log(`data: run ${run}`);
