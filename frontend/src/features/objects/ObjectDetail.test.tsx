import { fireEvent, render as renderBase, screen, waitFor, within } from "@testing-library/react";
import { ToastProvider } from "@/ui/Toast";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import { objectTypeHue } from "@/model/hues";
import type { EngineModel, ObjectItem, RelationItem } from "@/types";

/** A list's cells edited in place say where a save went in a toast (0.10 A9), as the app's provider shows it. */
const render: typeof renderBase = ((ui: Parameters<typeof renderBase>[0], options?: Parameters<typeof renderBase>[1]) =>
  renderBase(ui, { wrapper: ToastProvider, ...options })) as typeof renderBase;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// The page an application declares none for lists a relationship per direction, containment aside
// (0.13 RL), so the fixture gets one that is not containment.
const linked: EngineModel = {
  ...testModel,
  relationTypes: [
    ...testModel.relationTypes,
    {
      key: "domain-relates-codelist",
      reverseKey: "codelist-related-from-domain",
      name: "Relates to",
      reverseName: "Related from",
      isOriented: true,
      features: {},
    },
  ],
  objectTypeRelations: [
    ...testModel.objectTypeRelations,
    {
      relationTypeKey: "domain-relates-codelist",
      fromObjectTypeKey: "domain",
      toObjectTypeKey: "codelist",
      cardinality: "many-to-many",
    },
  ],
};

describe("ObjectDetail lifecycle controls", () => {
  it.each([domainObject, codelistObject])(
    "resizes $objectTypeKey properties while preserving inline input",
    async (object) => {
      const stored = new Map<string, string>();
      vi.stubGlobal("localStorage", {
        getItem: (key: string) => stored.get(key) ?? null,
        setItem: (key: string, value: string) => stored.set(key, value),
        removeItem: (key: string) => stored.delete(key),
      });
      vi.spyOn(api, "object").mockResolvedValue(object);
      vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
      render(
        <ObjectDetail
          model={testModel}
          application={testModel.applications[0]}
          objectTypeKey={object.objectTypeKey}
          objectId={object.id}
          workspaceKey="default"
          onOpen={vi.fn()}
          onBack={vi.fn()}
          readOnly={false}
        />,
      );
      const divider = await screen.findByRole("separator", { name: "Resize record properties" });
      fireEvent.click(screen.getAllByRole("button", { name: /^Edit Code:/ })[0]);
      const input = screen.getByLabelText("Code");
      fireEvent.change(input, { target: { value: "unsaved" } });
      fireEvent.keyDown(divider, { key: "ArrowLeft" });
      expect(divider).toHaveAttribute("aria-valuenow", "310");
      expect(input).toHaveValue("unsaved");
      const key = `rdm:layout:properties-width:v1:${object.applicationKey}:${object.objectTypeKey}`;
      expect(stored.get(key)).toBe("310");
      fireEvent.doubleClick(divider);
      expect(divider).toHaveAttribute("aria-valuenow", "300");
      expect(stored.has(key)).toBe(false);
      expect(input).toHaveValue("unsaved");
    },
  );
  it("opens a record in the application it stands in, and says so when the model has none", async () => {
    const [here] = testModel.applications;
    const there = { ...here, key: "elsewhere", name: "Elsewhere" };
    const stored = { ...codelistObject, applicationKey: there.key };
    vi.spyOn(api, "object").mockResolvedValue(stored);
    const listed = { ...testModel, applications: [here, { ...there, objectTypeKeys: ["codelist"] }] };
    const onOtherApplication = vi.fn();
    const { unmount } = render(
      <ObjectDetail
        model={listed}
        application={here}
        objectTypeKey="codelist"
        objectId={stored.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        onOtherApplication={onOtherApplication}
      />,
    );
    await waitFor(() => expect(onOtherApplication).toHaveBeenCalledWith(there.key));
    expect(screen.queryByText("Object unavailable")).not.toBeInTheDocument();
    unmount();

    const unlisted = { ...testModel, applications: [here, { ...there, objectTypeKeys: [] }] };
    render(
      <ObjectDetail
        model={unlisted}
        application={here}
        objectTypeKey="codelist"
        objectId={stored.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        onOtherApplication={onOtherApplication}
      />,
    );
    expect(await screen.findByText("Object unavailable")).toBeInTheDocument();
    expect(onOtherApplication).toHaveBeenCalledTimes(1);
  });

  it("follows a record whose type changed to its current type (D42)", async () => {
    const read = vi.spyOn(api, "object").mockRejectedValue(
      new ApiError(409, "OBJECT_TYPE_CHANGED", "The record is a domain in this change set.", {
        objectId: codelistObject.id,
        objectTypeKey: "domain",
        requestedObjectTypeKey: "codelist",
      }),
    );
    const onTypeChanged = vi.fn();
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey="codelist"
        objectId={codelistObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        onTypeChanged={onTypeChanged}
      />,
    );
    await waitFor(() => expect(onTypeChanged).toHaveBeenCalledWith("domain"));
    expect(read).toHaveBeenCalledWith("codelist", codelistObject.id, "default");
    expect(screen.queryByText("Object unavailable")).not.toBeInTheDocument();
  });

  it.each([domainObject, codelistObject])("retries $objectTypeKey in the selected workspace", async (object) => {
    const read = vi
      .spyOn(api, "object")
      .mockRejectedValueOnce(new Error("Record temporarily unavailable"))
      .mockResolvedValueOnce({ ...object, workspaceKey: "west" });
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey={object.objectTypeKey}
        objectId={object.id}
        workspaceKey="west"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        showBackToList={false}
      />,
    );
    expect(await screen.findByText("Record temporarily unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to list" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: object.name })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to list" })).not.toBeInTheDocument();
    expect(read).toHaveBeenNthCalledWith(1, object.objectTypeKey, object.id, "west");
    expect(read).toHaveBeenNthCalledWith(2, object.objectTypeKey, object.id, "west");
  });

  it("renders model-derived child collections and relationships when detail configuration is absent", async () => {
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    const children = vi.spyOn(api, "objects").mockResolvedValue({ items: [codelistObject], nextCursor: null });
    const relations = vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={linked}
        application={{ ...linked.applications[0], details: [] }}
        objectTypeKey={domainObject.objectTypeKey}
        objectId={domainObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Relates to" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: codelistObject.name })).toBeInTheDocument();
    expect(children).toHaveBeenCalledWith("codelist", expect.objectContaining({ parentObjectId: domainObject.id }));
    expect(relations).toHaveBeenCalledWith(domainObject.id, expect.objectContaining({ direction: "outgoing" }));
  });

  it("does not expose object retirement controls or call a retirement API", async () => {
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey="domain"
        objectId={domainObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Connections" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retire object" })).not.toBeInTheDocument();
    expect(screen.queryByText(/retir/i)).not.toBeInTheDocument();
  });
  it.each([domainObject, codelistObject])(
    "exposes live authoring and removes it when read-only for $objectTypeKey",
    async (object) => {
      vi.spyOn(api, "object").mockResolvedValue(object);
      vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
      const props = {
        model: testModel,
        application: testModel.applications[0],
        objectTypeKey: object.objectTypeKey,
        objectId: object.id,
        workspaceKey: "default",
        onOpen: vi.fn(),
        onBack: vi.fn(),
      };
      const { rerender } = render(<ObjectDetail {...props} readOnly={false} />);
      // UA8 (U-D17): no Edit record button; Edit record is the menu's first item.
      fireEvent.click(await screen.findByRole("button", { name: "Record actions" }));
      expect(screen.queryByRole("button", { name: "Edit record" })).not.toBeInTheDocument();
      expect(screen.getAllByRole("menuitem")[0]).toHaveAccessibleName("Edit record");
      fireEvent.click(screen.getByRole("menuitem", { name: "Edit record" }));
      expect(screen.getByLabelText("Name")).toHaveValue(object.name);
      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      rerender(<ObjectDetail {...props} readOnly={false} inspector onExpand={vi.fn()} />);
      fireEvent.click(await screen.findByRole("button", { name: "Record actions" }));
      expect(screen.queryByRole("button", { name: "Edit record" })).not.toBeInTheDocument();
      expect(screen.getAllByRole("menuitem")[0]).toHaveAccessibleName("Edit record");
      fireEvent.keyDown(screen.getAllByRole("menuitem")[0], { key: "Escape" });
      rerender(<ObjectDetail {...props} readOnly />);
      fireEvent.click(screen.getByRole("button", { name: "Record actions" }));
      expect(await screen.findByRole("menuitem", { name: "Copy link" })).toBeInTheDocument();
      expect(screen.queryByRole("menuitem", { name: "Edit record" })).not.toBeInTheDocument();
      expect(screen.queryByRole("menuitem", { name: "Delete record" })).not.toBeInTheDocument();
    },
  );
});

// UA4: the record's header and the inspector's Connected list, on two model configurations (the
// type order reversed changes every slot), so no expectation depends on one model's keys.
const reordered: EngineModel = { ...linked, objectTypes: [...linked.objectTypes].reverse() };
const connectedRelation: RelationItem = {
  direction: "outgoing",
  relation: {
    id: "77777777-7777-4777-8777-777777777777",
    relationTypeKey: "domain-relates-codelist",
    fromObjectId: domainObject.id,
    toObjectId: codelistObject.id,
    attributes: {},
    version: 1,
  },
  object: codelistObject,
};

describe.each([
  ["model order", linked],
  ["reversed type order", reordered],
])("the record in Atlas (UA4), %s", (_, model) => {
  function show(object: ObjectItem, extra: Partial<React.ComponentProps<typeof ObjectDetail>> = {}) {
    vi.spyOn(api, "object").mockResolvedValue(object);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null });
    const onOpen = vi.fn();
    const view = render(
      <ObjectDetail
        model={model}
        application={model.applications[0]}
        objectTypeKey={object.objectTypeKey}
        objectId={object.id}
        workspaceKey="default"
        onOpen={onOpen}
        onBack={vi.fn()}
        {...extra}
      />,
    );
    return { onOpen, ...view };
  }

  it("shows the record's ID, as the API returns it, and copies it", async () => {
    vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    show(codelistObject);
    await screen.findByRole("heading", { level: 1, name: codelistObject.name });
    expect(screen.getByText(codelistObject.id)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy ID" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(codelistObject.id));
    expect(await screen.findByText("ID copied.")).toBeInTheDocument();
  });

  it("tints the header in the record's type and shows its ancestors as chips in theirs", async () => {
    vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
    const { onOpen, container } = show(codelistObject);
    await screen.findByRole("heading", { level: 1, name: codelistObject.name });
    expect(container.querySelector(".record-header")).toHaveAttribute(
      "data-hue",
      String(objectTypeHue(model, "codelist")),
    );
    const ancestor = within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole("button", {
      name: "Connections",
    });
    expect(ancestor).toHaveAttribute("data-hue", String(objectTypeHue(model, "domain")));
    fireEvent.click(ancestor);
    expect(onOpen).toHaveBeenCalledWith("domain", domainObject.id);
  });

  it("lists relations as Connected chips in the inspector and keeps the tables on the full page", async () => {
    const relations = vi
      .spyOn(api, "relations")
      .mockResolvedValue({ items: [connectedRelation], nextCursor: null, totalCount: 1 });
    const onExpand = vi.fn();
    const { onOpen, unmount } = show(domainObject, { inspector: true, onExpand });
    const connected = await screen.findByRole("region", { name: "Connected" });
    // The panel sits its records under their domain (an ancestor column), so a chip names it first.
    const chip = await within(connected).findByRole("button", { name: new RegExp(codelistObject.name) });
    expect(chip).toHaveAttribute("data-hue", String(objectTypeHue(model, "codelist")));
    expect(within(connected).getByText("Relates to")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Search relates to" })).not.toBeInTheDocument();
    expect(relations).toHaveBeenCalledWith(domainObject.id, expect.objectContaining({ direction: "outgoing" }));
    fireEvent.click(chip);
    expect(onOpen).toHaveBeenCalledWith("codelist", codelistObject.id, codelistObject.applicationKey);
    fireEvent.click(within(connected).getByRole("button", { name: "Manage relationships on the full page" }));
    expect(onExpand).toHaveBeenCalled();
    unmount();

    show(domainObject);
    expect(await screen.findByRole("textbox", { name: "Search relates to" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Connected" })).not.toBeInTheDocument();
  });

  it("offers further connected records a page at a time", async () => {
    const more: RelationItem = {
      ...connectedRelation,
      relation: { ...connectedRelation.relation, id: "88888888-8888-4888-8888-888888888888" },
      object: { ...codelistObject, id: "99999999-9999-4999-8999-999999999999", name: "Durations" },
    };
    const relations = vi
      .spyOn(api, "relations")
      .mockResolvedValueOnce({ items: [connectedRelation], nextCursor: "next", totalCount: 2 })
      .mockResolvedValueOnce({ items: [more], nextCursor: null });
    show(domainObject, { inspector: true });
    const connected = await screen.findByRole("region", { name: "Connected" });
    fireEvent.click(await within(connected).findByRole("button", { name: "Show 1 more" }));
    expect(await within(connected).findByRole("button", { name: /Durations/ })).toBeInTheDocument();
    expect(relations).toHaveBeenLastCalledWith(domainObject.id, expect.objectContaining({ cursor: "next" }));
    expect(within(connected).queryByRole("button", { name: /Show/ })).not.toBeInTheDocument();
  });
});
