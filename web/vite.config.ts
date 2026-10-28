import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const api = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  // amazon-cognito-identity-js (SRP do login) usa o `global` do Node.
  define: { global: "globalThis" },
  server: { proxy: { "/api": api } },
  preview: { proxy: { "/api": api } },
});
