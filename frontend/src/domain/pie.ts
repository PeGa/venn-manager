/**
 * Pie geometry for the History breakdown (FRONTEND.md § 5.4). Segments are
 * percentages of the ring, drawn with `stroke-dasharray` on an SVG circle.
 */

/** The design's pie palette, in slice order. */
export const PIE_COLORS = ["#23392f", "#4f9a76", "#9fd6b8", "#d9694a", "#d9c7a8", "#a9c7b6", "#c9bfe0"] as const;

export interface Segment {
  /** Where the segment starts, 0–100, clockwise from 12 o'clock. */
  start: number;
  /** How much of the ring it covers, 0–100. */
  length: number;
  color: string;
}

/** Lay *amounts* end to end, each as its exact share of their total. */
export function pieSegments(amounts: readonly number[]): Segment[] {
  const total = amounts.reduce((sum, amount) => sum + amount, 0);
  if (total <= 0) return [];
  let start = 0;
  return amounts.map((amount, index) => {
    const length = (amount / total) * 100;
    const segment = { start, length, color: PIE_COLORS[index % PIE_COLORS.length] ?? PIE_COLORS[0] };
    start += length;
    return segment;
  });
}
