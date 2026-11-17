import { describe, expect, it } from "vitest";
import { signInUrl } from "@/lib/miniapp";

describe("signInUrl", () => {
  it("goes to GitHub login without the cookie", () => {
    expect(signInUrl("")).toBe("/api/auth/github/login");
  });

  it("goes to /tg when miniapp=1 is set", () => {
    expect(signInUrl("session=abc; miniapp=1")).toBe("/tg");
    expect(signInUrl("miniapp=1")).toBe("/tg");
  });

  it("ignores miniapp=0", () => {
    expect(signInUrl("miniapp=0")).toBe("/api/auth/github/login");
  });

  it("ignores a cookie that only ends with miniapp", () => {
    expect(signInUrl("xminiapp=1")).toBe("/api/auth/github/login");
  });
});
