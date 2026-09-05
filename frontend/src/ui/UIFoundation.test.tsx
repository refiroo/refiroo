import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { ComboBoxField, SelectField } from "@/ui/Selection";
import { Tabs } from "@/ui/Tabs";

describe("RDM UI foundation", () => {
  it("keeps decorative icons hidden and gives meaningful icons an accessible name", () => {
    const { container } = render(
      <>
        <Icon name="search" />
        <Icon name="check" label="Ready" />
      </>,
    );
    expect(container.querySelector("[aria-hidden='true']")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Ready" })).toBeInTheDocument();
  });

  it("provides keyboard-aware selection and menu behavior behind RDM APIs", async () => {
    const onSelect = vi.fn();
    const edit = vi.fn();
    render(
      <>
        <SelectField
          label="Sort"
          value="name"
          options={[
            { id: "name", label: "Name" },
            { id: "-name", label: "Name descending" },
          ]}
          onChange={onSelect}
        />
        <ActionMenu items={[{ id: "edit", label: "Edit", onAction: edit }]} />
      </>,
    );

    fireEvent.click(screen.getByRole("button", { name: /name sort/i }));
    fireEvent.click(await screen.findByRole("option", { name: "Name descending" }));
    expect(onSelect).toHaveBeenCalledWith("-name");

    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Edit" }));
    expect(edit).toHaveBeenCalledTimes(1);
  });

  it("supports a custom workspace key without claiming catalogue authority", () => {
    const onChange = vi.fn();
    render(
      <ComboBoxField
        label="Workspace"
        value="default"
        options={[{ id: "default", label: "default" }]}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByRole("combobox", { name: "Workspace" }), { target: { value: "west" } });
    expect(onChange).toHaveBeenCalledWith("west");
  });

  it("exposes tabs with standard tab and panel semantics", () => {
    render(
      <Tabs
        label="Object sections"
        selected="details"
        tabs={[
          { id: "details", label: "Details", content: "Detail content" },
          { id: "history", label: "History", content: "History content" },
        ]}
      />,
    );
    expect(screen.getByRole("tablist", { name: "Object sections" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Detail content");
  });
});
