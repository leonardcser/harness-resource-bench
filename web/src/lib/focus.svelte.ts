// The label that a chart's legend points at. The chart dims the others, so
// that one agent or part stands out.

/** The opacity of what a focus dims. */
export const DIM = 0.15;

export class Focus {
  label = $state<string | null>(null);

  /** Whether `label` gives way to another one in focus. */
  dims(label: string) {
    return this.label !== null && this.label !== label;
  }

  /** Handlers that put `label` in focus while the pointer is over an
   * element. */
  on(label: string) {
    return {
      onpointerenter: () => (this.label = label),
      onpointerleave: () => (this.label = null),
    };
  }
}
