import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { rolldown } from "rolldown";
import { defineConfig, type Plugin } from "vite";

const api = "http://127.0.0.1:8765";

/** O envio da fila em segundo plano, num bloco só para o service worker, com o env do build. */
async function empacotarSegundoPlano(env: Record<string, string>): Promise<string> {
  const pacote = await rolldown({
    input: "src/dados/segundoPlano.ts",
    transform: { define: { "import.meta.env": JSON.stringify(env) } },
  });
  const { output } = await pacote.generate({ format: "iife", name: "segundoPlano" });
  await pacote.close();
  return `(() => {\n${output[0].code}\nreturn segundoPlano;\n})()`;
}

/**
 * Escreve o service-worker.js no build, com a lista dos arquivos da casca, uma versão e o envio
 * da fila em segundo plano.
 */
function serviceWorker(): Plugin {
  let env: Record<string, string> = {};
  return {
    name: "service-worker-da-casca",
    apply: "build",
    configResolved(config) {
      env = config.env;
    },
    async generateBundle(_opcoes, bundle) {
      const segundoPlano = await empacotarSegundoPlano(env);
      const publicos = readdirSync("public");
      const arquivos = [
        ...new Set(["index.html", ...Object.keys(bundle), ...publicos].map((nome) => `/${nome}`)),
      ].sort();
      const versao = createHash("sha256")
        .update(
          Object.values(bundle)
            .map((item) => item.fileName + (item.type === "chunk" ? item.code : ""))
            .join(),
        )
        .update(publicos.map((nome) => readFileSync(`public/${nome}`)).join())
        .update(segundoPlano)
        .digest("hex")
        .slice(0, 12);
      this.emitFile({
        type: "asset",
        fileName: "service-worker.js",
        source: readFileSync("service-worker.js", "utf8")
          .replace("__VERSAO__", versao)
          .replace("__CASCA__", JSON.stringify(arquivos))
          .replace("__SEGUNDO_PLANO__", () => segundoPlano),
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
