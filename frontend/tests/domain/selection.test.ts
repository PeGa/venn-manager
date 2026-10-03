import { describe, expect, it } from "vitest";

import { EMPTY, click, prune, toggle } from "@/domain/selection";

const ROWS = ["a", "b", "c", "d", "e"];
const plain = { shift: false, toggle: false };

describe("click (fine pointer)", () => {
  it("selects one row and anchors it", () => {
    expect(click(EMPTY, ROWS, "c", plain)).toEqual({ ids: ["c"], anchor: "c" });
  });

  it("replaces the selection on a plain click", () => {
    const one = click(EMPTY, ROWS, "a", plain);
    expect(click(one, ROWS, "d", plain)).toEqual({ ids: ["d"], anchor: "d" });
  });

  it("toggles rows with Ctrl or ⌘ and moves the anchor", () => {
    let selection = click(EMPTY, ROWS, "a", plain);
    selection = click(selection, ROWS, "c", { shift: false, toggle: true });
    expect(selection).toEqual({ ids: ["a", "c"], anchor: "c" });
    selection = click(selection, ROWS, "a", { shift: false, toggle: true });
    expect(selection).toEqual({ ids: ["c"], anchor: "a" });
  });

  it("selects a contiguous range with Shift, in either direction", () => {
    const anchored = click(EMPTY, ROWS, "b", plain);
    expect(click(anchored, ROWS, "d", { shift: true, toggle: false }).ids).toEqual(["b", "c", "d"]);
    const reversed = click(EMPTY, ROWS, "d", plain);
    expect(click(reversed, ROWS, "b", { shift: true, toggle: false }).ids).toEqual(["b", "c", "d"]);
  });

  it("keeps the anchor across shift clicks", () => {
    const anchored = click(EMPTY, ROWS, "b", plain);
    const wide = click(anchored, ROWS, "e", { shift: true, toggle: false });
    expect(click(wide, ROWS, "c", { shift: true, toggle: false })).toEqual({
      ids: ["b", "c"],
      anchor: "b",
    });
  });

  it("treats Shift without an anchor as a plain click", () => {
    expect(click(EMPTY, ROWS, "c", { shift: true, toggle: false })).toEqual({
      ids: ["c"],
      anchor: "c",
    });
  });
});

describe("toggle (coarse pointer select mode)", () => {
  it("adds and removes rows", () => {
    const one = toggle(EMPTY, "a");
    expect(one.ids).toEqual(["a"]);
    expect(toggle(one, "a").ids).toEqual([]);
  });
});

describe("prune", () => {
  it("drops rows that disappeared", () => {
    expect(prune({ ids: ["a", "x"], anchor: "x" }, ROWS)).toEqual({ ids: ["a"], anchor: null });
  });
});
