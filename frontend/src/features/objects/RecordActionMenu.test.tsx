import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { domainObject } from "@/test/fixtures";

const descriptor = Object.getOwnPropertyDescriptor(navigator, "clipboard");
afterEach(() => {
  if (descriptor) Object.defineProperty(navigator, "clipboard", descriptor);
  else Reflect.deleteProperty(navigator, "clipboard");
});

describe("record actions", () => {
  it("keeps a read-only record link available and reports clipboard refusal with a recovery action", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockRejectedValue(new Error("Permission denied")),
      },
    });
    render(<RecordActionMenu object={domainObject} readOnly onEdit={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: `Actions for ${domainObject.name}` }));
    expect(screen.queryByRole("menuitem", { name: "Edit record" })).not.toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Delete record" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("menuitem", { name: "Copy link" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Open the record and copy its address from the browser."),
    );
  });
});
