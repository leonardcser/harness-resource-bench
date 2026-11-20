import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { SITE } from "./src/lib/site.ts";

// The build for the root of the site, or with `--mode freeze`, the page of the
// latest run at runs/ID/, into results/ID/site to commit with the run.
export default defineConfig(({ mode }) => {
  const freeze = mode === "freeze";
  const data = (name: string) =>
    JSON.parse(
      readFileSync(new URL(`src/data/${name}`, import.meta.url), "utf8"),
    );
  const run: { id: string; date: string } = data("run.json");
  // The frozen page links to the code that measured the run, so that commit
  // must stay in the history of the release.
  if (freeze) {
    const commit: string | undefined = data("manifest.json").commit;
    if (!commit) {
      throw new Error(
        `Run ${run.id} names no commit: run again from a commit with no changes`,
      );
    }
    try {
      execFileSync("git", ["merge-base", "--is-ancestor", commit, "HEAD"], {
        stdio: "ignore",
      });
    } catch {
      throw new Error(
        `Run ${run.id} measured ${commit}, which is not in the history of HEAD: do not rewrite the commits of a run`,
      );
    }
  }
  const page = `${SITE}/${freeze ? `runs/${run.id}/` : ""}`;

  return {
    base: "./",
    define: { __ROOT__: JSON.stringify(freeze ? "../../" : "./") },
    build: freeze
      ? { outDir: `../results/${run.id}/site`, emptyOutDir: true }
      : undefined,
    plugins: [
      tailwindcss(),
      svelte(),
      {
        name: "page",
        transformIndexHtml: (html) => ({
          html: html
            .replaceAll("%PAGE_URL%", page)
            .replaceAll("%RUN_DATE%", run.date),
          // Search shows the root, which has the latest run.
          tags: freeze
            ? [{ tag: "meta", attrs: { name: "robots", content: "noindex" } }]
            : [],
        }),
      },
    ],
  };
});
