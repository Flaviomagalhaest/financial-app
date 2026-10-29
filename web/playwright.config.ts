import { defineConfig } from "@playwright/test";
import { clienteId, emissor, endpoint, userPoolId } from "./e2e/cognito-falso";

const urlDoBanco = process.env.DATABASE_URL;

export default defineConfig({
  testDir: "e2e",
  // Um teste por vez: os testes dividem os usuários do Cognito falso e um deles derruba as
  // sessões de um usuário.
  workers: 1,
  use: { baseURL: "http://127.0.0.1:4173" },
  webServer: [
    {
      command: "node e2e/cognito-falso.ts",
      url: `${emissor}/.well-known/jwks.json`,
      reuseExistingServer: !process.env.CI,
    },
    {
      command:
        "uv run python -m app.migrations && uv run uvicorn app.main:create_app --factory --port 8765",
      cwd: "../backend",
      url: "http://127.0.0.1:8765/api/saude",
      env: {
        DATABASE_URL: urlDoBanco ?? "",
        JWT_EMISSOR: emissor,
        JWT_AUDIENCIA: clienteId,
        PESSOAS: JSON.stringify({ "sub-flavio": "Flávio", "sub-esposa": "Fulana" }),
      },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run build && npm run preview",
      url: "http://127.0.0.1:4173",
      env: {
        VITE_COGNITO_USER_POOL_ID: userPoolId,
        VITE_COGNITO_CLIENTE_ID: clienteId,
        VITE_COGNITO_ENDPOINT: endpoint,
      },
      reuseExistingServer: !process.env.CI,
    },
  ],
});
