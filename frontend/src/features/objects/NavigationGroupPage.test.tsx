import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { testModel } from "@/test/fixtures";
import { NavigationGroupPage } from "@/features/objects/NavigationGroupPage";

describe("NavigationGroupPage", () => {
  it("lists a group's collections and views, each opening on its view", () => {
    const application = structuredClone(testModel.applications[0]);
    const domains = application.views[0];
    if (domains.type !== "table") throw new Error("Expected table fixture");
    application.views.push({
      key: "domains-by-codelist",
      name: "Domains by codelist",
      type: "relationMatrix",
      config: {
        relationTypeKey: "domain-contains-codelist",
        direction: "outgoing",
        rowObjectTypeKey: "domain",
        columnObjectTypeKey: "codelist",
        cellObjectTypeKey: "codelist",
        rowColumns: ["name"],
        columnLabelField: "name",
        cellFields: ["name"],
        searchFields: ["name"],
        pageSize: 20,
      },
    });
    application.navigation = {
      groups: [{ key: "places", label: "Places", collections: [{ view: "domains-by-codelist" }, "domain"] }],
    };
    const onOpen = vi.fn();
    render(
      <NavigationGroupPage model={testModel} application={application} groupKey="places" onOpenCollection={onOpen} />,
    );
    expect(screen.getByText("1 collection and 1 view")).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Domains by codelist\s*Relation matrix of/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^Domains by codelist\s*Relation matrix of/ }));
    expect(onOpen).toHaveBeenLastCalledWith("domains-by-codelist");
    fireEvent.change(screen.getByRole("textbox", { name: "Search Places" }), { target: { value: "zzz" } });
    expect(screen.getByText("No collection or view in this group matches “zzz”.")).toBeTruthy();
  });

  it("lists a table view and a tree view as entries of their own, named by kind", () => {
    const application = structuredClone(testModel.applications[0]);
    const domains = application.views[0];
    if (domains.type !== "table") throw new Error("Expected table fixture");
    application.views.push({ ...domains, key: "domains-again", name: "Domains again" });
    application.views.push({
      key: "domain-tree",
      name: "Domain tree",
      type: "tree",
      config: { rootObjectTypeKeys: ["domain"], nodeObjectTypeKeys: ["domain"], displayFields: { domain: ["name"] } },
    } as never);
    application.navigation = {
      groups: [{ key: "places", label: "Places", collections: [{ view: "domains-again" }, { view: "domain-tree" }] }],
    };
    const onOpen = vi.fn();
    render(
      <NavigationGroupPage model={testModel} application={application} groupKey="places" onOpenCollection={onOpen} />,
    );
    expect(screen.getByText("0 collections and 2 views")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^Domains again\s*Table of/ }));
    expect(onOpen).toHaveBeenLastCalledWith("domains-again");
    fireEvent.click(screen.getByRole("button", { name: /^Domain tree\s*Tree of/ }));
    expect(onOpen).toHaveBeenLastCalledWith("domain-tree");
  });
});
