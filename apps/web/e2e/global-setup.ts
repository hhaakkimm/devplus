import { execSync } from "node:child_process";

export default function globalSetup() {
  const token = execSync("uv run python scripts/seed_e2e.py", {
    cwd: "../api",
    encoding: "utf8",
  }).trim();
  if (!token) throw new Error("seed_e2e.py printed no session token");
  process.env.E2E_SESSION_TOKEN = token;
}
