import { describe, expect, it } from "vitest";
import { linkFailedMessage, nextStep } from "@/lib/telegram";

describe("nextStep", () => {
  it.each([
    [200, "home"],
    [404, "link"],
    [403, "no-access"],
    [401, "open-telegram"],
    [500, "error"],
    [422, "error"],
  ] as const)("%i -> %s", (status, step) => {
    expect(nextStep(status)).toBe(step);
  });
});

describe("linkFailedMessage", () => {
  it("explains an invalid link", () => {
    expect(linkFailedMessage("invalid")).toContain("устарела");
  });

  it("explains a login outside the allowlist", () => {
    expect(linkFailedMessage("not_allowed")).toContain("списке доступа");
  });

  it("falls back to a generic text", () => {
    const generic = linkFailedMessage(undefined);
    expect(generic).not.toContain("устарела");
    expect(generic).not.toContain("списке доступа");
    expect(linkFailedMessage("whatever")).toBe(generic);
  });
});
