// Copies the run RUN, or else the newest frozen run, into src/data, which the
// site imports at build time: its ID and date, its results and the profile of
// its workload.
// It keeps only the fields that the site reads, as the site bundles them.
// Files change only when their content does, so a dev server reloads once.
import { mkdir, readdir, rm } from "node:fs/promises";

const results = new URL("../../results/", import.meta.url).pathname;
const out = new URL("../src/data/", import.meta.url).pathname;

const frozen = (await readdir(results))
  .filter((id) => Bun.file(`${results}${id}/site/index.html`).size)
  .sort();
const run = process.env.RUN ?? frozen.at(-1);
if (!run) {
  throw new Error(
    `No frozen run in ${results}. Freeze one: RUN=ID bun run freeze`,
  );
}

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
    commit: m.commit,
  }),
  "summary.json": (s) => pick(s, "planned", "groups", "canary"),
  "profile.json": (p) => p,
};

const files = new Map<string, Json>();
for (const [name, trim] of Object.entries(TRIM)) {
  const file = Bun.file(`${results}${run}/${name}`);
  if (!(await file.exists())) {
    throw new Error(`No ${name} in ${results}${run}`);
  }
  files.set(name, trim(await file.json()));
}
const date = files.get("manifest.json")!.started_utc.slice(0, 10);
files.set("run.json", { id: run, date });

await mkdir(out, { recursive: true });
for (const [name, json] of files) {
  const content = JSON.stringify(json);
  const file = Bun.file(out + name);
  if ((await file.exists()) && (await file.text()) === content) continue;
  await Bun.write(file, content);
}
for (const name of await readdir(out)) {
  if (!files.has(name)) await rm(out + name, { recursive: true, force: true });
}
console.log(`data: run ${run}`);
