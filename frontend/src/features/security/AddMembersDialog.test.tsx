import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import { AddMembersDialog } from "@/features/security/AddMembersDialog";
import type { Group, GroupMember } from "@/types";

vi.mock("@/api/securityClient", () => ({ security: { users: vi.fn(), addMembers: vi.fn() } }));

const group = { id: "g1", name: "Curators" } as Group;
const person = (id: string, name: string, active = true): GroupMember => ({ id, name, username: id, active });
const ana = person("ana", "Ana Varga");
const bo = person("bo", "Bo Lind");
const kept = person("kept", "Kept Member");

describe("adding several people to a group (0.12 SP1b)", () => {
  it("ticks people found, checks a pasted list, and adds them together", async () => {
    vi.mocked(security.users).mockResolvedValue({ items: [ana, kept], nextCursor: null } as never);
    vi.mocked(security.addMembers).mockImplementation(async (_group, body) => {
      if (body.dryRun && body.userIds)
        return {
          items: [
            { input: "ana", outcome: "toAdd", member: ana },
            { input: "kept", outcome: "alreadyMember", member: kept },
          ],
          changed: 0,
        };
      if (body.dryRun)
        return {
          items: [
            { input: "BO", outcome: "toAdd", member: bo },
            { input: "nobody@example.org", outcome: "notFound", member: null },
          ],
          changed: 0,
        };
      return {
        items: body.userIds!.map((id) => ({ input: id, outcome: "added" as const, member: person(id, id) })),
        changed: body.userIds!.length,
      };
    });
    const onAdded = vi.fn();
    render(<AddMembersDialog group={group} onClose={vi.fn()} onAdded={onAdded} />);

    fireEvent.click(await screen.findByRole("checkbox", { name: "Add Ana Varga" }));
    expect(screen.getByRole("checkbox", { name: "Add Kept Member" })).toBeDisabled();
    expect(screen.getByText("Already a member")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Paste a list" }));
    fireEvent.change(screen.getByLabelText("Usernames or e-mail addresses"), {
      target: { value: "BO\nnobody@example.org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Check 2 lines" }));
    expect(await screen.findByText("No person with this username or e-mail")).toBeInTheDocument();
    expect(security.addMembers).toHaveBeenLastCalledWith("g1", {
      identifiers: ["BO", "nobody@example.org"],
      dryRun: true,
    });

    fireEvent.click(await screen.findByRole("button", { name: "Add 2 members" }));
    await waitFor(() => expect(onAdded).toHaveBeenCalled());
    expect(security.addMembers).toHaveBeenLastCalledWith("g1", { userIds: ["ana", "bo"] });
  });
});
