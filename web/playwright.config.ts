import { defineConfig } from "@playwright/test";

const urlDoBanco = process.env.DATABASE_URL;

export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://127.0.0.1:4173" },
  webServer: [
    {
      command:
        "uv run python -c \"from app.migrations import aplicar_migrations as a; import os; a(os.environ['DATABASE_URL'])\" && uv run uvicorn app.main:create_app --factory --port 8765",
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
