/**
 * Vitest setup.
 *
 * Two things jsdom does not give us: automatic DOM cleanup between tests, and
 * `matchMedia`, which the system-theme listener needs.
 */
import { cleanup } from "@testing-library/preact";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
});

type MediaListener = (event: { matches: boolean; media: string }) => void;

const mediaState = new Map<string, boolean>();

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: mediaState.get(query) ?? false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

/** Test helper: make a media query report a given match state. */
export function setMediaMatch(query: string, matches: boolean): void {
  mediaState.set(query, matches);
}

export type { MediaListener };
