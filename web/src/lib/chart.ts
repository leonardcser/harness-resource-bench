// Label layout helpers shared by the charts.

/** End-label positions at least `gap` apart, each near its target. */
export function spread(
  targets: number[],
  gap: number,
  min: number,
  max: number,
): number[] {
  const order = targets.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y);
  const ys = order.map((o) => o.y);
  for (let pass = 0; pass < 50; pass++) {
    let moved = false;
    for (let k = 1; k < ys.length; k++) {
      const overlap = gap - (ys[k] - ys[k - 1]);
      if (overlap > 0.01) {
        ys[k - 1] -= overlap / 2;
        ys[k] += overlap / 2;
        moved = true;
      }
    }
    for (let k = 0; k < ys.length; k++)
      ys[k] = Math.min(max, Math.max(min, ys[k]));
    if (!moved) break;
  }
  const out = new Array<number>(targets.length);
  order.forEach((o, k) => (out[o.i] = ys[k]));
  return out;
}

/** Ticks at least `gap` pixels apart, always keeping the last. */
export function thin(
  ticks: number[],
  pos: (v: number) => number,
  gap: number,
): number[] {
  const kept: number[] = [];
  for (const t of ticks)
    if (!kept.length || pos(t) - pos(kept.at(-1)!) >= gap) kept.push(t);
  const last = ticks.at(-1);
  if (last !== undefined && kept.at(-1) !== last) {
    if (kept.length > 1 && pos(last) - pos(kept.at(-1)!) < gap) kept.pop();
    kept.push(last);
  }
  return kept;
}

/** Length along a bar track for a fraction of the scale. The last 4.5rem stay
 * free for the value label. */
export const span = (fraction: number): string =>
  `calc((100% - 4.5rem) * ${fraction})`;

const measure = document.createElement("canvas").getContext("2d")!;

/** Width in pixels of chart text, which is 11px in the page's font. */
export function textWidth(text: string): number {
  measure.font = `11px ${getComputedStyle(document.body).fontFamily}`;
  return measure.measureText(text).width;
}
