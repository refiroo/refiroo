import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject } from "@/test/fixtures";
import { RecordListField, type ChosenRecord } from "@/ui/RecordListField";

vi.mock("@/api/client", () => ({ api: { objects: vi.fn() } }));

function Held({ required }: { required?: boolean }) {
  const [values, setValues] = useState<ChosenRecord[]>([]);
  return (
    <form aria-label="Form">
      <RecordListField
        label="Add domains"
        objectTypeKey="domain"
        values={values}
        required={required}
        onChange={setValues}
      />
    </form>
  );
}

describe("RecordListField (0.9 K3)", () => {
  it("adds a chip per record picked by keyboard, once, and removes it again", async () => {
    vi.mocked(api.objects).mockResolvedValue({
      items: [domainObject, { ...domainObject, id: "other", name: "Finance" }],
      nextCursor: null,
    });
    render(<Held />);
    expect(screen.getByText("None chosen yet")).toBeInTheDocument();
    const search = screen.getByRole("combobox", { name: "Search: Add domains" });
    await screen.findByRole("option", { name: /Finance/ });
    fireEvent.keyDown(search, { key: "ArrowDown" });
    fireEvent.keyDown(search, { key: "ArrowDown" });
    fireEvent.keyDown(search, { key: "Enter" });
    fireEvent.click(screen.getByRole("option", { name: /Finance/ }));
    expect(screen.getAllByRole("row", { name: "Finance" })).toHaveLength(1);
    expect(screen.getByRole("option", { name: /Finance/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("1 chosen")).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("row", { name: "Finance" })).getByRole("button"));
    expect(screen.queryByRole("row", { name: "Finance" })).toBeNull();
    expect(screen.getByText("None chosen yet")).toBeInTheDocument();
  });

  it("is invalid while required and empty", () => {
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null });
    render(<Held required />);
    expect((screen.getByRole("form", { name: "Form" }) as HTMLFormElement).checkValidity()).toBe(false);
  });
});
