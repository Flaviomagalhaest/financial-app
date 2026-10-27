import { defineConfig } from "@playwright/test";

const urlDoBanco = process.env.DATABASE_URL;

export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://127.0.0.1:4173" },
  webServer: [
    {
      command:
        "uv run python -m app.migrations && uv run uvicorn app.main:create_app --factory --port 8765",
      cwd: "../backend",
      url: "http://127.0.0.1:8765/api/saude",
      env: { DATABASE_URL: urlDoBanco ?? "" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run build && npm run preview",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
