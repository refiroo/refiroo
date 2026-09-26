import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import type { RelationsPanelDefinition, WorkspaceDraft } from "@/types";
import { RelationsPanel } from "@/features/objects/panels/RelationsPanel";

vi.mock("@/api/client", () => ({ api: { relations: vi.fn(), deleteRelation: vi.fn() } }));

const panel: RelationsPanelDefinition = {
  key: "relations",
  title: "Relations",
  type: "relations",
  region: "main",
  order: 1,
  visible: true,
  config: { relationTypeKeys: ["domain-contains-codelist"], direction: "outgoing", columns: ["name"] },
};

describe("RelationsPanel", () => {
  beforeEach(() =>
    vi.mocked(api.relations).mockResolvedValue({
      items: [
        {
          direction: "outgoing",
          relation: {
            id: "relation",
            relationTypeKey: "domain-contains-codelist",
            fromObjectId: domainObject.id,
            toObjectId: codelistObject.id,
            attributes: {},
            version: 1,
          },
          object: codelistObject,
        },
      ],
      nextCursor: null,
    }),
  );

  it("shows direction-correct labels and protects managed containment rows", async () => {
    render(<RelationsPanel model={testModel} object={domainObject} panel={panel} onOpen={vi.fn()} />);
    expect(await screen.findByText("Contains")).toBeInTheDocument();
    expect(screen.getByText("Managed through Parent")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add relationship/ })).not.toBeInTheDocument();
  });

  it("can hide a redundant relationship label and show a configured ancestor", async () => {
    render(
      <RelationsPanel
        model={testModel}
        object={domainObject}
        panel={{
          ...panel,
          config: {
            ...panel.config,
            columns: ["ancestor:domain", "name"],
            showRelationshipColumn: false,
          },
        }}
        onOpen={vi.fn()}
      />,
    );

    expect(await screen.findByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Domain" })).toBeInTheDocument();
    expect(screen.getByText("Connections")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Timetable types" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Connections" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Relationship" })).not.toBeInTheDocument();
    expect(screen.queryByText("Contains")).not.toBeInTheDocument();
  });

  it("offers dependent object creation for a required outgoing relation", async () => {
    vi.mocked(api.relations).mockResolvedValue({ items: [], nextCursor: null });
    const translationType = {
      ...testModel.objectTypes[0],
      key: "translation",
      name: "Translation",
      pluralName: "Translations",
      features: { rootCreatable: false },
    };
    const model = {
      ...testModel,
      objectTypes: [...testModel.objectTypes, translationType],
      relationTypes: [
        ...testModel.relationTypes,
        {
          key: "object-has-translation",
          reverseKey: "translation-translates-object",
          name: "Has translation",
          reverseName: "Translates object",
          isOriented: true,
          features: {},
        },
      ],
      objectTypeRelations: [
        ...testModel.objectTypeRelations,
        {
          relationTypeKey: "object-has-translation",
          fromObjectTypeKey: "domain",
          toObjectTypeKey: "translation",
          cardinality: "one-to-many" as const,
          required: true,
        },
      ],
      applications: [
        testModel.applications[0],
        { ...testModel.applications[0], key: "translations", objectTypeKeys: ["translation"] },
      ],
    };
    const translationPanel: RelationsPanelDefinition = {
      ...panel,
      config: {
        relationTypeKeys: ["object-has-translation"],
        direction: "outgoing",
        columns: ["name"],
      },
    };

    render(<RelationsPanel model={model} object={domainObject} panel={translationPanel} onOpen={vi.fn()} />);

    expect(await screen.findByRole("button", { name: "Add Translation" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add relationship" })).not.toBeInTheDocument();
  });

  it("scrolls on to another relation page without replacing the first", async () => {
    vi.mocked(api.relations)
      .mockResolvedValueOnce({
        items: [
          {
            direction: "outgoing",
            relation: {
              id: "relation-1",
              relationTypeKey: "domain-contains-codelist",
              fromObjectId: domainObject.id,
              toObjectId: codelistObject.id,
              attributes: {},
              version: 1,
            },
            object: codelistObject,
          },
        ],
        nextCursor: "next",
      })
      .mockResolvedValueOnce({
        items: [
          {
            direction: "outgoing",
            relation: {
              id: "relation-2",
              relationTypeKey: "domain-contains-codelist",
              fromObjectId: domainObject.id,
              toObjectId: "other",
              attributes: {},
              version: 1,
            },
            object: { ...codelistObject, id: "other", name: "Procedures" },
          },
        ],
        nextCursor: null,
      });
    render(<RelationsPanel model={testModel} object={domainObject} panel={panel} onOpen={vi.fn()} />);
    fireEvent.keyDown(await screen.findByRole("button", { name: "Timetable types" }), { key: "ArrowDown" });
    expect(await screen.findByText("Procedures")).toBeInTheDocument();
    expect(screen.getByText("Timetable types")).toBeInTheDocument();
    await waitFor(() =>
      expect(api.relations).toHaveBeenLastCalledWith(domainObject.id, {
        workspaceKey: "default",
        direction: "outgoing",
        relationTypeKey: "domain-contains-codelist",
        search: "",
        sort: "name",
        cursor: "next",
        pageSize: 50,
      }),
    );
  });

  it("retries the same relation cursor after an edge failure", async () => {
    const first = {
      direction: "outgoing" as const,
      relation: {
        id: "relation-1",
        relationTypeKey: "domain-contains-codelist",
        fromObjectId: domainObject.id,
        toObjectId: codelistObject.id,
        attributes: {},
        version: 1,
      },
      object: codelistObject,
    };
    vi.mocked(api.relations)
      .mockResolvedValueOnce({ items: [first], nextCursor: "next" })
      .mockRejectedValueOnce(new Error("Relation page unavailable"))
      .mockResolvedValueOnce({
        items: [
          {
            ...first,
            relation: { ...first.relation, id: "relation-2" },
            object: { ...codelistObject, id: "other", name: "Procedures" },
          },
        ],
        nextCursor: null,
      });
    render(<RelationsPanel model={testModel} object={domainObject} panel={panel} onOpen={vi.fn()} />);
    fireEvent.keyDown(await screen.findByRole("button", { name: "Timetable types" }), { key: "ArrowDown" });
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Procedures")).toBeInTheDocument();
    expect(api.relations).toHaveBeenLastCalledWith(domainObject.id, {
      workspaceKey: "default",
      direction: "outgoing",
      relationTypeKey: "domain-contains-codelist",
      search: "",
      sort: "name",
      cursor: "next",
      pageSize: 50,
    });
  });

  it("clears a relationship-delete failure when its confirmation is cancelled", async () => {
    const model = {
      ...testModel,
      objectTypes: testModel.objectTypes.map((item) =>
        item.key === "codelist" ? { ...item, behavior: { parentRelationTypeKeys: [] } } : item,
      ),
    };
    vi.mocked(api.deleteRelation).mockRejectedValueOnce(new Error("Relationship delete unavailable"));

    render(<RelationsPanel model={model} object={domainObject} panel={panel} onOpen={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete relationship" }));
    expect(await screen.findByText("Relationship delete unavailable")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("Relationship delete unavailable")).not.toBeInTheDocument();
  });

  describe("sorting (S4R3)", () => {
    const sorted: RelationsPanelDefinition = {
      ...panel,
      config: { ...panel.config, columns: ["name", "code"], sortFields: ["code", "name"], defaultSort: "-code" },
    };
    const lastSort = () => vi.mocked(api.relations).mock.lastCall?.[1]?.sort;
    beforeEach(() => vi.restoreAllMocks());

    it("sorts every data column and the relationship label without configuration", async () => {
      render(
        <RelationsPanel
          model={testModel}
          object={domainObject}
          panel={{ ...panel, config: { ...panel.config, columns: ["name", "code", "active", "path"] } }}
          onOpen={vi.fn()}
        />,
      );
      await screen.findByText("Timetable types");
      expect(lastSort()).toBe("name");
      expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "ascending");
      // Active is not flagged sortable in the model, yet as a data column it sorts.
      fireEvent.click(screen.getByRole("button", { name: "Active" }));
      await waitFor(() => expect(lastSort()).toBe("active"));
      fireEvent.click(screen.getByRole("button", { name: "Relationship" }));
      await waitFor(() => expect(lastSort()).toBe("relationship"));
      // The computed path is the one column the server cannot order.
      expect(within(screen.getByRole("columnheader", { name: "Path" })).queryByRole("button")).toBeNull();
      expect(screen.queryByRole("combobox", { name: "Sort" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Sort: Relationship, ascending" })).toBeInTheDocument();
    });

    it("sorts by the panel's declared default and toggles from the shared headers", async () => {
      render(<RelationsPanel model={testModel} object={domainObject} panel={sorted} onOpen={vi.fn()} />);
      await screen.findByText("Timetable types");
      expect(lastSort()).toBe("-code");
      expect(screen.getByRole("columnheader", { name: /Code/ })).toHaveAttribute("aria-sort", "descending");
      fireEvent.click(screen.getByRole("button", { name: "Code, sorted descending" }));
      await waitFor(() => expect(lastSort()).toBe("code"));
      fireEvent.click(screen.getByRole("button", { name: "Name" }));
      await waitFor(() => expect(lastSort()).toBe("name"));
      expect(screen.getByText("Sorted by Name, ascending")).toHaveAttribute("role", "status");
      // The same menu is present on every list with sort fields.
      expect(screen.getByRole("button", { name: "Sort: Name, ascending" })).toBeInTheDocument();
    });

    it("offers declared fields without a column in the sort menu", async () => {
      render(
        <RelationsPanel
          model={testModel}
          object={domainObject}
          panel={{ ...sorted, config: { ...sorted.config, columns: ["name"] } }}
          onOpen={vi.fn()}
        />,
      );
      await screen.findByText("Timetable types");
      fireEvent.click(screen.getByRole("button", { name: "Sort: Code, descending" }));
      fireEvent.click(await screen.findByRole("menuitemradio", { name: "Ascending" }));
      await waitFor(() => expect(lastSort()).toBe("code"));
    });

    it("drops live-only timestamps from the declared fields in a draft", async () => {
      vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
        api,
        warning: "",
        draft: { id: "d1" } as WorkspaceDraft,
      });
      render(
        <RelationsPanel
          model={testModel}
          object={domainObject}
          panel={{
            ...sorted,
            config: {
              ...sorted.config,
              columns: ["name", "updatedAt"],
              sortFields: ["updatedAt", "name"],
              defaultSort: "-updatedAt",
            },
          }}
          onOpen={vi.fn()}
        />,
      );
      await screen.findByText("Timetable types");
      expect(lastSort()).toBe("name");
      expect(within(screen.getByRole("columnheader", { name: "Updated" })).queryByRole("button")).toBeNull();
      expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "ascending");
    });
  });
});
