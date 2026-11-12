import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import type { Grant } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { GrantsSection } from "./GrantsSection";

vi.mock("@/api/client", () => ({ api: { workspaces: vi.fn().mockResolvedValue({ items: [], nextCursor: null }) } }));
vi.mock("@/api/securityClient", () => ({ security: { deleteGrant: vi.fn(), createGrant: vi.fn() } }));
const dialog = vi.fn();
const change: { current: { added: unknown[]; removed: unknown[] } } = { current: { added: [], removed: [] } };
vi.mock("./GrantDialog", () => ({
  GrantDialog: (props: {
    who?: { name: string };
    onChanged: (change: { added: unknown[]; removed: unknown[] }) => void;
  }) => {
    dialog(props.who);
    return (
      <div role="dialog">
        Grant for {props.who?.name ?? "nobody"}
        <button type="button" onClick={() => props.onChanged(change.current)}>
          save change
        </button>
      </div>
    );
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
  vi.mocked(security.createGrant).mockResolvedValue(undefined as never);
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
    fireEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Remove grant" }));
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

describe("a person's roles (0.17 ST1)", () => {
  it("groups the grants by place: every workspace first, each grant a coloured chip, one held through a group says so, only the person's own can be removed", async () => {
    const team = { kind: "group" as const, id: "9", name: "Stewards North" };
    const rows = [
      grant("p1", ana, "steward", { applicationNames: ["A"] }),
      grant("p3", ana, "owner"),
      grant("p2", team, "reader", { instance: true }),
    ];
    render(
      <ToastProvider>
        <GrantsSection
          subject={{ principal: ana }}
          load={() => Promise.resolve({ items: rows, nextCursor: null })}
          deps={["u"]}
          onNavigate={() => {}}
        />
      </ToastProvider>,
    );
    const panel = await screen.findByRole("group", { name: "Roles" });
    const places = within(panel)
      .getAllByRole("list")
      .map((list) => list.getAttribute("aria-label"));
    expect(places[0]).toBe("Roles in Every workspace");
    expect(places).toHaveLength(2);
    const workspace = within(panel).getByRole("list", { name: places[1]! });
    expect(within(workspace).getByText("Data steward").closest("[data-hue]")).toHaveAttribute("data-hue", "1");
    expect(within(workspace).getByText(/writes: A/)).toBeInTheDocument();
    expect(within(workspace).getByText("owner")).toBeInTheDocument();
    const everywhere = within(panel).getByRole("list", { name: "Roles in Every workspace" });
    expect(within(everywhere).getByText(/through/)).toBeInTheDocument();
    expect(within(everywhere).getByRole("link", { name: "Stewards North" })).toBeInTheDocument();
    expect(within(panel).getAllByRole("button", { name: /^Remove/ })).toHaveLength(2);
    expect(within(panel).getAllByRole("button", { name: /^Grant .* more/ })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Grant" })).toBeInTheDocument();
  });
});

describe("removing and changing from a person's page, with Undo (0.17)", () => {
  const rows = [grant("p1", ana, "steward", { applicationNames: ["A"], applications: ["a"] })];
  const renderPerson = () =>
    render(
      <ToastProvider>
        <GrantsSection
          subject={{ principal: ana }}
          load={() => Promise.resolve({ items: rows, nextCursor: null })}
          deps={["u"]}
          onNavigate={() => {}}
        />
      </ToastProvider>,
    );

  it("removes by the chip's trash without asking, says so, and Undo makes the grant again with its narrowing", async () => {
    renderPerson();
    fireEvent.click(await screen.findByRole("button", { name: /^Remove Data steward/ }));
    await waitFor(() => expect(security.deleteGrant).toHaveBeenCalledWith("p1"));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(await screen.findByText(/Ana Varga no longer holds Data steward/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() =>
      expect(security.createGrant).toHaveBeenCalledWith({
        principal: { kind: "user", id: "1" },
        role: "steward",
        scope: { workspaceKey: "w", applications: ["a"] },
      }),
    );
  });

  it("after a saved dialog says what changed, and Undo deletes what was added and makes the removed again", async () => {
    const made = grant("n1", ana, "reader");
    change.current = { added: [made], removed: [rows[0]!] };
    renderPerson();
    fireEvent.click(await screen.findByRole("button", { name: /^Grant Ana Varga more/ }));
    fireEvent.click(await screen.findByRole("button", { name: "save change" }));
    expect(await screen.findByText("Ana Varga’s access changed: 1 added, 1 removed.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(security.deleteGrant).toHaveBeenCalledWith("n1"));
    await waitFor(() => expect(security.createGrant).toHaveBeenCalledTimes(1));
  });
});
