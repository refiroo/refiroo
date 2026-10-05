import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { ComboBoxField, SelectField } from "@/ui/Selection";
import { Tabs } from "@/ui/Tabs";
import { Notice } from "@/ui/Notice";
import { Card } from "@/ui/Card";
import { PageHeader } from "@/ui/PageHeader";
import { StatusPill } from "@/ui/StatusPill";

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

    const select = screen.getByRole("button", { name: /name sort/i });
    fireEvent.keyDown(select, { key: "ArrowDown", code: "ArrowDown" });
    fireEvent.keyDown(await screen.findByRole("option", { name: "Name descending" }), {
      key: "Enter",
      code: "Enter",
    });
    expect(onSelect).toHaveBeenCalledWith("-name");

    const menu = screen.getByRole("button", { name: "More actions" });
    fireEvent.keyDown(menu, { key: "ArrowDown", code: "ArrowDown" });
    fireEvent.keyDown(await screen.findByRole("menuitem", { name: "Edit" }), { key: "Enter", code: "Enter" });
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
    const onChange = vi.fn();
    render(
      <Tabs
        label="Object sections"
        selected="details"
        onChange={onChange}
        tabs={[
          { id: "details", label: "Details", content: "Detail content" },
          { id: "history", label: "History", content: "History content" },
        ]}
      />,
    );
    expect(screen.getByRole("tablist", { name: "Object sections" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Detail content");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Details" }), { key: "ArrowRight", code: "ArrowRight" });
    expect(onChange).toHaveBeenCalledWith("history");
  });

  it("moves focus to a newly mounted task-level error notice", () => {
    render(
      <Notice tone="error" title="Save failed" focusOnMount>
        Your input was preserved.
      </Notice>,
    );
    expect(screen.getByRole("alert")).toHaveFocus();
  });

  it("gives a page one focusable title with its description, decorative icon and actions", () => {
    const { container } = render(
      <PageHeader
        focusTitle
        icon={<Icon name="tree" />}
        eyebrow="Domain"
        title="Domains"
        description="Top-level grouping of reference data"
        actions={<button className="primary">Add domain</button>}
      />,
    );
    const title = screen.getByRole("heading", { level: 1, name: "Domains" });
    expect(title).toHaveAttribute("tabindex", "-1");
    expect(screen.getByText("Domain")).toHaveClass("eyebrow");
    expect(screen.getByText("Top-level grouping of reference data")).toBeInTheDocument();
    expect(container.querySelector(".page-icon")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("button", { name: "Add domain" }).closest(".page-actions")).not.toBeNull();
    render(<PageHeader title="Publications" />);
    expect(screen.getByRole("heading", { level: 1, name: "Publications" })).not.toHaveAttribute("tabindex");
  });

  it("names a status in text, with its marker hidden from assistive technology", () => {
    const { container } = render(<StatusPill tone="changeSet">Change set · Q4</StatusPill>);
    const pill = container.querySelector(".status-pill");
    expect(pill).toHaveClass("tone-change-set");
    expect(pill).toHaveTextContent("Change set · Q4");
    expect(container.querySelector(".status-pill-marker")).toHaveAttribute("aria-hidden", "true");
  });

  it("makes a titled card a region named by its heading, and an untitled one a plain block", () => {
    render(
      <Card title="Details" actions={<button>Edit</button>}>
        <p>Body</p>
      </Card>,
    );
    expect(screen.getByRole("region", { name: "Details" })).toHaveTextContent("Body");
    expect(screen.getByRole("heading", { level: 2, name: "Details" })).toBeInTheDocument();
    const { container } = render(<Card>Plain</Card>);
    expect(container.querySelector("section")).toBeNull();
    expect(container.querySelector(".card")).toHaveTextContent("Plain");
  });
});
