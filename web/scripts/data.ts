// Copies the run that results/published.json names into public/data: its
// results and the profile of its workload.
// Files change in place, so a running dev server keeps serving them.
import { mkdir, readdir, rm } from "node:fs/promises";

const results = new URL("../../results/", import.meta.url).pathname;
const out = new URL("../public/data/", import.meta.url).pathname;

const pointer = Bun.file(`${results}published.json`);
if (!(await pointer.exists())) {
  throw new Error(`No published.json in ${results}. Run: uv run bench.py run`);
}
const { run } = (await pointer.json()) as { run: string };

const files = new Map<string, string>();
for (const name of ["manifest.json", "summary.json", "profile.json"]) {
  const file = Bun.file(`${results}${run}/${name}`);
  if (!(await file.exists())) {
    throw new Error(`No ${name} in ${results}${run}`);
  }
  files.set(name, await file.text());
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
