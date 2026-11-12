// Inspecting a chart with a pointer. A mouse inspects on hover. A finger
// presses and holds, then drags; a quick swipe still scrolls the page.
import type { Attachment } from "svelte/attachments";

export type Probe = {
  /** Position in pixels from the element's top left corner. */
  x: number;
  y: number;
  /** The element under the pointer. */
  target: Element | null;
  touch: boolean;
};

/** How long a finger holds still before it inspects, in milliseconds. */
const HOLD = 250;
/** How far a finger may drift during the hold, in pixels. */
const SLOP = 8;

export function scrub(
  move: (probe: Probe) => void,
  end: () => void,
): Attachment<HTMLElement | SVGElement> {
  return (node) => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let start: { x: number; y: number } | null = null;
    let active = false;

    const probe = (clientX: number, clientY: number, touch: boolean) => {
      const r = node.getBoundingClientRect();
      move({
        x: clientX - r.left,
        y: clientY - r.top,
        target: document.elementFromPoint(clientX, clientY),
        touch,
      });
    };
    const stop = () => {
      clearTimeout(timer);
      start = null;
      if (active) end();
      active = false;
    };

    const onPointerMove = (e: PointerEvent) =>
      e.pointerType !== "touch" && probe(e.clientX, e.clientY, false);
    const onPointerLeave = (e: PointerEvent) =>
      e.pointerType !== "touch" && end();
    const onTouchStart = (e: TouchEvent) => {
      stop();
      if (e.touches.length !== 1) return;
      const t = e.touches[0];
      start = { x: t.clientX, y: t.clientY };
      timer = setTimeout(() => {
        active = true;
        probe(start!.x, start!.y, true);
      }, HOLD);
    };
    const onTouchMove = (e: TouchEvent) => {
      const t = e.touches[0];
      if (active) {
        e.preventDefault();
        probe(t.clientX, t.clientY, true);
      } else if (
        start &&
        Math.hypot(t.clientX - start.x, t.clientY - start.y) > SLOP
      )
        stop();
    };
    // A long press would otherwise open the context menu or select text.
    const onContextMenu = (e: Event) => (start || active) && e.preventDefault();

    const style = node.style as CSSStyleDeclaration & {
      webkitTouchCallout: string;
    };
    style.userSelect = style.webkitUserSelect = "none";
    style.webkitTouchCallout = "none";
    const listeners: [string, EventListener, AddEventListenerOptions?][] = [
      ["pointermove", onPointerMove as EventListener],
      ["pointerleave", onPointerLeave as EventListener],
      ["touchstart", onTouchStart as EventListener, { passive: true }],
      ["touchmove", onTouchMove as EventListener, { passive: false }],
      ["touchend", stop],
      ["touchcancel", stop],
      ["contextmenu", onContextMenu],
    ];
    for (const [type, fn, opts] of listeners)
      node.addEventListener(type, fn, opts);
    return () => {
      stop();
      for (const [type, fn] of listeners) node.removeEventListener(type, fn);
    };
  };
}
