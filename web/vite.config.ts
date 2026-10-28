import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const api = "http://127.0.0.1:8765";

/** Escreve o service-worker.js no build, com a lista dos arquivos da casca e uma versão. */
function serviceWorker(): Plugin {
  return {
    name: "service-worker-da-casca",
    apply: "build",
    generateBundle(_opcoes, bundle) {
      const arquivos = [
        "/index.html",
        ...Object.keys(bundle).map((nome) => `/${nome}`),
        ...readdirSync("public").map((nome) => `/${nome}`),
      ].sort();
      const versao = createHash("sha256")
        .update(
          Object.values(bundle)
            .map((item) => item.fileName + (item.type === "chunk" ? item.code : ""))
            .join(),
        )
        .update(readdirSync("public").map((nome) => readFileSync(`public/${nome}`)).join())
        .digest("hex")
        .slice(0, 12);
      this.emitFile({
        type: "asset",
        fileName: "service-worker.js",
        source: readFileSync("service-worker.js", "utf8")
          .replace("__VERSAO__", versao)
          .replace("__CASCA__", JSON.stringify(arquivos)),
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serviceWorker()],
  // amazon-cognito-identity-js (SRP do login) usa o `global` do Node.
  define: { global: "globalThis" },
  server: { proxy: { "/api": api } },
  preview: { proxy: { "/api": api } },
});
