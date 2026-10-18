import { defineConfig } from "@playwright/test";

const origin = "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  use: { baseURL: origin },
  // Never reuse a running server: the api must allow exactly the e2e user.
  webServer: [
    {
      command: "cd ../api && uv run uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/api/health",
      reuseExistingServer: false,
      // DATABASE_URL comes from the environment (make exports .env).
      env: {
        ALLOWED_GITHUB_LOGINS: "e2e-user",
        APP_ORIGIN: origin,
        COOKIE_SECURE: "false",
        GITHUB_CLIENT_ID: "e2e",
        GITHUB_CLIENT_SECRET: "e2e",
      },
    },
    {
      command: "pnpm dev",
      url: `${origin}/no-access`,
      reuseExistingServer: false,
      env: { API_INTERNAL_URL: "http://localhost:8000" },
    },
  ],
});
