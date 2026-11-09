import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { testModel } from "@/test/fixtures";
import { NavigationGroupPage } from "@/features/objects/NavigationGroupPage";

describe("NavigationGroupPage", () => {
  it("lists a group's collections and relation matrices, each opening on its view", () => {
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
    expect(screen.getByText("1 collection and 1 relation matrix")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^Domains by codelist\s*Relation matrix of/ }));
    expect(onOpen).toHaveBeenLastCalledWith("domains-by-codelist");
    fireEvent.change(screen.getByRole("textbox", { name: "Search Places" }), { target: { value: "zzz" } });
    expect(screen.getByText("No collection or relation matrix in this group matches “zzz”.")).toBeTruthy();
  });
});
