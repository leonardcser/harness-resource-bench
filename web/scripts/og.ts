// Draws public/og.png, the 1200x630 preview that social sites show for a link.
import { Resvg } from "@resvg/resvg-js";
import satori from "satori";
import { AGENTS, PROFILES } from "../src/agents";

const out = new URL("../public/og.png", import.meta.url).pathname;
const fonts = new URL(
  "../node_modules/@fontsource/ibm-plex-sans/files/",
  import.meta.url,
).pathname;

// The light theme in src/app.css.
const C = { bg: "#fbfbfa", fg: "#1f1f1e", muted: "#76756f" };

type Node = { type: string; props: Record<string, unknown> };
const h = (
  type: string,
  style: Record<string, unknown>,
  ...children: (Node | string)[]
): Node => ({ type, props: { style, children } });

const image = (svg: string, size: number): Node => ({
  type: "img",
  props: {
    src: `data:image/svg+xml;base64,${btoa(svg)}`,
    width: size,
    height: size,
  },
});

/** An agent's mark in the light theme. */
const logo = (svg: string) =>
  svg
    .replaceAll('class="fill-fg"', `fill="${C.fg}"`)
    .replaceAll('class="fill-muted"', `fill="${C.muted}"`)
    .replaceAll('class="fill-bg"', `fill="${C.bg}"`)
    .replaceAll("currentColor", C.fg);

const favicon = await Bun.file(
  new URL("../public/favicon.svg", import.meta.url),
).text();
const mark = favicon
  .replace(/<style>.*<\/style>/s, "")
  .replaceAll("<rect ", `<rect fill="${C.fg}" `);

const card = h(
  "div",
  {
    width: 1200,
    height: 630,
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    padding: "72px 96px",
    background: C.bg,
    color: C.fg,
    fontFamily: "IBM Plex Sans",
  },
  h(
    "div",
    { display: "flex", alignItems: "center", gap: 14 },
    image(mark, 32),
    h("div", { fontSize: 24, fontWeight: 600 }, "harness resource bench"),
  ),
  h(
    "div",
    {
      marginTop: 40,
      maxWidth: 820,
      fontSize: 88,
      fontWeight: 600,
      lineHeight: 1.02,
      letterSpacing: "-0.03em",
    },
    "Resource use of coding agents",
  ),
  h(
    "div",
    { marginTop: 24, fontSize: 28, lineHeight: 1.4, color: C.muted },
    "CPU, memory, startup, disk and install size, on the same work.",
  ),
  h(
    "div",
    { marginTop: "auto", display: "flex", alignItems: "center", gap: 44 },
    ...AGENTS.map((agent) => image(logo(PROFILES[agent].logo), 52)),
  ),
);

const font = async (weight: 400 | 600) => ({
  name: "IBM Plex Sans",
  weight,
  style: "normal" as const,
  data: await Bun.file(
    `${fonts}ibm-plex-sans-latin-${weight}-normal.woff`,
  ).arrayBuffer(),
});

const svg = await satori(card as never, {
  width: 1200,
  height: 630,
  fonts: [await font(400), await font(600)],
});
await Bun.write(out, new Resvg(svg).render().asPng());
console.log(`og: ${AGENTS.length} agents`);
