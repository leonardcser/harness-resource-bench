// Adds the frozen page of each run, results/ID/site, to the built site at
// runs/ID/, and names the latest run in runs.json for the pages to read.
import { cp, readdir } from "node:fs/promises";

const results = new URL("../../results/", import.meta.url).pathname;
const dist = new URL("../dist/", import.meta.url).pathname;

// The run of the root, as scripts/data.ts chose it
const { id: run } = (await Bun.file(
  new URL("../src/data/run.json", import.meta.url).pathname,
).json()) as { id: string };

const frozen: string[] = [];
for (const id of await readdir(results)) {
  const site = `${results}${id}/site`;
  if (!(await Bun.file(`${site}/index.html`).exists())) continue;
  await cp(site, `${dist}runs/${id}`, { recursive: true });
  frozen.push(id);
}
await Bun.write(`${dist}runs.json`, JSON.stringify({ latest: run }));
console.log(`runs: ${frozen.join(", ")}`);
