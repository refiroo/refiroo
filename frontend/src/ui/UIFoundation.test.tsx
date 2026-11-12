import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { ComboBoxField, SelectField } from "@/ui/Selection";
import { Tabs } from "@/ui/Tabs";
import { Notice } from "@/ui/Notice";
import { Card } from "@/ui/Card";
import { PageHeader } from "@/ui/PageHeader";
import { StatusPill } from "@/ui/StatusPill";
import { DescriptionList } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { FormField } from "@/ui/FormField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { TOAST_TIMEOUT_MS, ToastProvider, useToast } from "@/ui/Toast";

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

  it("renders an untitled card as a section its caller names, without padding when flush (UA6)", () => {
    render(
      <Card as="section" flush aria-label="Records" data-hue="3">
        Rows
      </Card>,
    );
    const card = screen.getByRole("region", { name: "Records" });
    expect(card).toHaveClass("card", "card-flush");
    expect(card).toHaveAttribute("data-hue", "3");
  });

  it("lays out a settings page with its eyebrow, title and ruled sections (U3)", () => {
    render(
      <SettingsLayout eyebrow="General" title="About" description="What this deployment runs.">
        <Section title="Engine" description="The running engine." actions={<a href="#x">Open</a>}>
          <DescriptionList
            items={[
              { term: "Version", value: "0.9.0" },
              { term: <abbr title="Application programming interface">API</abbr>, value: "v1", key: "api" },
            ]}
          />
        </Section>
      </SettingsLayout>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "About" })).toBeInTheDocument();
    expect(screen.getByText("General")).toHaveClass("eyebrow");
    const section = screen.getByRole("region", { name: "Engine" });
    expect(within(section).getByRole("heading", { level: 2, name: "Engine" })).toBeInTheDocument();
    expect(within(section).getByRole("link", { name: "Open" })).toBeInTheDocument();
    expect(
      within(section)
        .getAllByRole("term")
        .map((item) => item.textContent),
    ).toEqual(["Version", "API"]);
    expect(
      within(section)
        .getAllByRole("definition")
        .map((item) => item.textContent),
    ).toEqual(["0.9.0", "v1"]);
  });

  it("ties a field's label, help and error to its control, or to a group's legend", () => {
    render(
      <>
        <FormField label="Name" help="Shown in lists." error="A name is required.">
          {(control) => <input {...control} />}
        </FormField>
        <FormField group label="Theme" help="Saved in this browser.">
          {() => (
            <label>
              <input type="radio" name="t" /> Dark
            </label>
          )}
        </FormField>
      </>,
    );
    const input = screen.getByRole("textbox", { name: "Name" });
    expect(input).toHaveAccessibleDescription("Shown in lists. A name is required.");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("group", { name: "Theme" })).toHaveAccessibleDescription("Saved in this browser.");
  });

  it("shows an empty state with its action, and a skeleton announced by its label", () => {
    const create = vi.fn();
    render(
      <>
        <EmptyState action={<button onClick={create}>New draft</button>}>No drafts yet.</EmptyState>
        <Skeleton label="Loading releases" lines={2} />
      </>,
    );
    expect(screen.getByText("No drafts yet.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "New draft" }));
    expect(create).toHaveBeenCalledTimes(1);
    const skeleton = screen.getByRole("status", { name: "Loading releases" });
    expect(skeleton).toHaveAttribute("aria-busy", "true");
    expect(skeleton.querySelectorAll(".skeleton-line")).toHaveLength(2);
  });

  it("keeps a toast until dismissed or eight seconds pass without hover or focus", () => {
    vi.useFakeTimers();
    function Confirm() {
      const toast = useToast();
      return <button onClick={() => toast("Workspace renamed.")}>Rename</button>;
    }
    try {
      render(
        <ToastProvider>
          <Confirm />
        </ToastProvider>,
      );
      const region = screen.getByRole("status");
      fireEvent.click(screen.getByRole("button", { name: "Rename" }));
      expect(region).toHaveTextContent("Workspace renamed.");
      act(() => vi.advanceTimersByTime(TOAST_TIMEOUT_MS - 1));
      expect(region).toHaveTextContent("Workspace renamed.");
      act(() => vi.advanceTimersByTime(1));
      expect(region).not.toHaveTextContent("Workspace renamed.");

      fireEvent.click(screen.getByRole("button", { name: "Rename" }));
      const toast = within(region).getByText("Workspace renamed.").closest<HTMLElement>(".toast")!;
      fireEvent.mouseEnter(toast);
      act(() => vi.advanceTimersByTime(TOAST_TIMEOUT_MS * 2));
      expect(region).toHaveTextContent("Workspace renamed.");
      fireEvent.mouseLeave(toast);
      fireEvent.focus(within(toast).getByRole("button", { name: "Dismiss" }));
      act(() => vi.advanceTimersByTime(TOAST_TIMEOUT_MS * 2));
      expect(region).toHaveTextContent("Workspace renamed.");
      fireEvent.click(within(toast).getByRole("button", { name: "Dismiss" }));
      expect(region).not.toHaveTextContent("Workspace renamed.");
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("ConfirmDialog tone (0.17 UX1)", () => {
  it("draws the confirming button red by default and plain for tone=plain, with no extra line", () => {
    const { unmount } = render(
      <ConfirmDialog title="Remove it?" confirmLabel="Remove" onCancel={vi.fn()} onConfirm={vi.fn()}>
        <p>It goes.</p>
      </ConfirmDialog>,
    );
    expect(screen.getByRole("button", { name: "Remove" })).toHaveClass("danger");
    expect(screen.queryByText(/Please confirm/)).toBeNull();
    unmount();
    render(
      <ConfirmDialog title="Start it?" confirmLabel="Start" tone="plain" onCancel={vi.fn()} onConfirm={vi.fn()}>
        <p>It starts.</p>
      </ConfirmDialog>,
    );
    expect(screen.getByRole("button", { name: "Start" })).toHaveClass("primary");
    expect(screen.queryByText(/Please confirm/)).toBeNull();
  });
});
