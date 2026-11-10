const UNITS = ["B", "KiB", "MiB", "GiB"];

export function bytes(value: number): string {
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit++;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${value.toFixed(digits)} ${UNITS[unit]}`;
}

export function seconds(value: number): string {
  if (value === 0) return "0 s";
  if (value < 1) return `${(value * 1000).toFixed(value < 0.01 ? 1 : 0)} ms`;
  return `${value.toFixed(value < 10 ? 2 : value < 100 ? 1 : 0)} s`;
}

export function percent(value: number): string {
  return `${value.toFixed(value < 10 ? 1 : 0)}%`;
}

export function minutes(value: number): string {
  return value < 60 ? `${value} s` : `${value / 60} min`;
}

/** Tokens in a JSON size, at about 4 bytes per token. */
export const count = (value: number): string => value.toLocaleString("en");
