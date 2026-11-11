import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { expectConsoleError } from "@/test/consoleGuard";
import { ErrorBoundary } from "@/ui/ErrorBoundary";

function Broken(): never {
  throw new TypeError("Cannot read properties of undefined (reading 'length')");
}

describe("ErrorBoundary (reported 2026-10-14: a blank page)", () => {
  it("shows what failed and a reload instead of an empty page, and clears when the address changes", () => {
    // React reports the error the boundary catches.
    expectConsoleError(/reading 'length'/);
    const { rerender } = render(
      <ErrorBoundary resetKey="/a">
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByText("This page stopped working")).toBeTruthy();
    expect(screen.getByText(/reading 'length'/)).toBeTruthy();
    expect(screen.queryByText(/Error:/)).toBeNull();
    expect(screen.getByRole("button", { name: "Reload the page" })).toBeTruthy();
    rerender(
      <ErrorBoundary resetKey="/b">
        <p>Another page</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("Another page")).toBeTruthy();
  });

  it("never shows an Error: prefix, whatever was thrown", () => {
    expectConsoleError(/Error/);
    function Silent(): never {
      throw new Error("");
    }
    render(
      <ErrorBoundary>
        <Silent />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/failed while showing: Error\./).textContent).not.toMatch(/: Error: /);
  });
});
