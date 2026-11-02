import { defineConfig } from "@playwright/test";
import { apiEnv, origin } from "./e2e/worker";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: { baseURL: origin },
  // Never reuse a running server: the api must allow exactly the e2e user.
  webServer: [
    {
      command: "cd ../api && uv run uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/api/health",
      reuseExistingServer: false,
      env: apiEnv,
    },
    {
      command: "pnpm dev",
      url: `${origin}/no-access`,
      reuseExistingServer: false,
      env: { API_INTERNAL_URL: "http://localhost:8000", APP_ORIGIN: origin },
    },
  ],
});
