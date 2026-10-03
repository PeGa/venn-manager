import { cleanup } from "@solidjs/testing-library";
import { afterEach, vi } from "vitest";

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
