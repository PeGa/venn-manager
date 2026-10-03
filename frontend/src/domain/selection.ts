/**
 * Row selection on Transactions (FRONTEND.md § 6).
 *
 * Pure state transitions; the UI decides which one a gesture triggers.
 */

export interface Selection {
  readonly ids: readonly string[];
  readonly anchor: string | null;
}

export interface Modifiers {
  /** Shift: select the range from the anchor. */
  shift: boolean;
  /** Ctrl or ⌘: toggle one row. */
  toggle: boolean;
}

export const EMPTY: Selection = { ids: [], anchor: null };

/** A click with a fine pointer. *order* is the rows as displayed. */
export function click(
  selection: Selection,
  order: readonly string[],
  id: string,
  { shift, toggle: flip }: Modifiers,
): Selection {
  if (shift && selection.anchor !== null && order.includes(selection.anchor)) {
    const from = order.indexOf(selection.anchor);
    const to = order.indexOf(id);
    const [low, high] = from < to ? [from, to] : [to, from];
    return { ids: order.slice(low, high + 1), anchor: selection.anchor };
  }
  if (flip) {
    return { ...toggle(selection, id), anchor: id };
  }
  return { ids: [id], anchor: id };
}

/** Add or remove one row (coarse-pointer select mode, Ctrl/⌘ clicks). */
export function toggle(selection: Selection, id: string): Selection {
  const ids = selection.ids.includes(id)
    ? selection.ids.filter((selected) => selected !== id)
    : [...selection.ids, id];
  return { ids, anchor: selection.anchor };
}

/** Forget rows that are no longer listed. */
export function prune(selection: Selection, order: readonly string[]): Selection {
  const anchor = selection.anchor !== null && order.includes(selection.anchor) ? selection.anchor : null;
  return { ids: selection.ids.filter((id) => order.includes(id)), anchor };
}
