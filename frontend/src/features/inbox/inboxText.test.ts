import { describe, expect, it } from "vitest";
import { noticeRoute } from "@/features/inbox/inboxText";
import type { Notification } from "@/types";

const notice = (kind: Notification["kind"]) =>
  ({
    id: "n",
    kind,
    workspaceKey: "herbarium",
    subject: { kind: "change-set", id: "cs-1" },
    details: {},
  }) as Notification;

describe("noticeRoute", () => {
  it("leads a followed publication to the workspace's publications", () => {
    expect(noticeRoute(notice("change-set.published"), "plants")).toEqual({
      kind: "publications",
      applicationKey: "plants",
      workspaceKey: "herbarium",
    });
  });

  it("leads an approval nowhere, as its change set is gone", () => {
    expect(noticeRoute(notice("change-set.approved"), "plants")).toBeUndefined();
  });
});
