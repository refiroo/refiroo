import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import type { Grant } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { GrantsSection } from "./GrantsSection";

vi.mock("@/api/client", () => ({ api: { workspaces: vi.fn().mockResolvedValue({ items: [], nextCursor: null }) } }));
vi.mock("@/api/securityClient", () => ({ security: { deleteGrant: vi.fn() } }));
const dialog = vi.fn();
vi.mock("./GrantDialog", () => ({
  GrantDialog: (props: { who?: { name: string } }) => {
    dialog(props.who);
    return <div role="dialog">Grant for {props.who?.name ?? "nobody"}</div>;
  },
}));

const person = (id: string, name: string) => ({ kind: "user" as const, id, name });
const grant = (id: string, principal: Grant["principal"], key: string, extra: Partial<Grant["scope"]> = {}) =>
  ({
    id,
    principal,
    role: { key, name: key === "steward" ? "Data steward" : key === "reader" ? "Reader" : key },
    scope: {
      instance: false,
      workspaceKey: "w",
      applications: [],
      recordTypes: [],
      applicationNames: [],
      recordTypeNames: [],
      ...extra,
    },
  }) as unknown as Grant;

const ana = person("1", "Ana Varga");
const boris = person("2", "Boris Novak");
const grants = [
  grant("g1", ana, "reader"),
  grant("g2", ana, "workspace-admin", { instance: true }),
  grant("g3", boris, "steward", { applicationNames: ["A", "B", "C"] }),
];

function renderSection() {
  return render(
    <ToastProvider>
      <GrantsSection
        subject={{ workspace: { key: "w", label: "W" } }}
        title="Access"
        load={() => Promise.resolve({ items: grants, nextCursor: null })}
        deps={["w"]}
        onNavigate={() => {}}
        headingLevel={3}
      />
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(security.deleteGrant).mockResolvedValue(undefined as never);
});

describe("workspace Access list", () => {
  it("shows one row per principal with a chip per grant", async () => {
    renderSection();
    const list = await screen.findByRole("list", { name: "Access" });
    const rows = within(list)
      .getAllByRole("listitem", { name: "" })
      .filter((item) => item.className === "access-row");
    expect(rows).toHaveLength(2);
    const chips = within(screen.getByRole("list", { name: "Roles of Ana Varga" })).getAllByText(
      /Reader|workspace-admin/,
    );
    expect(chips).toHaveLength(2);
    expect(screen.getByText("· writes: A, B +1")).toBeInTheDocument();
  });

  it("offers no remove on a whole-instance chip", async () => {
    renderSection();
    await screen.findByText("· whole instance");
    expect(screen.getByRole("button", { name: "Remove Reader from Ana Varga" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove workspace-admin from Ana Varga" })).toBeNull();
  });

  it("removes a grant after confirming", async () => {
    renderSection();
    fireEvent.click(await screen.findByRole("button", { name: "Remove Reader from Ana Varga" }));
    expect(security.deleteGrant).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(security.deleteGrant).toHaveBeenCalledWith("g1"));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Remove Reader from Ana Varga" })).toBeNull());
  });

  it("opens the grant dialog for the row's principal", async () => {
    renderSection();
    fireEvent.click(await screen.findByRole("button", { name: "Add a role for Boris Novak" }));
    expect(await screen.findByText("Grant for Boris Novak")).toBeInTheDocument();
  });

  it("narrows the rows by search and by role", async () => {
    renderSection();
    await screen.findByText("Ana Varga");
    fireEvent.change(screen.getByLabelText("Search people, groups, clients"), { target: { value: "bor" } });
    expect(screen.queryByText("Ana Varga")).toBeNull();
    expect(screen.getByText("Boris Novak")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search people, groups, clients"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "role:steward" } });
    expect(screen.queryByText("Ana Varga")).toBeNull();
    fireEvent.change(screen.getByLabelText("Search people, groups, clients"), { target: { value: "zzz" } });
    expect(screen.getByText("No one matches.")).toBeInTheDocument();
  });
});
