import { cleanup, configure } from "@solidjs/testing-library";
import { afterEach, vi } from "vitest";

// Screen tests boot the whole app; with every worker busy, the 1 s default
// for findBy and waitFor is too tight and fails at random.
configure({ asyncUtilTimeout: 5000 });

afterEach(() => {
  cleanup();
});

// jsdom has no layout: give matchMedia a fine-pointer, wide-screen answer.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// jsdom has no modal <dialog> and no scrolling.
HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
  this.removeAttribute("open");
};
Element.prototype.scrollIntoView = vi.fn();
