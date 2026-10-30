// O envio da fila pelo service worker, sem tela aberta: o `sync` que o Android dispara quando a
// rede volta. O vite.config.ts empacota este arquivo dentro do service-worker.js; ele importa só
// o que roda fora da tela (sem React, sem o cliente da API, sem a biblioteca do SRP).
import { tokenEmSegundoPlano } from "../login/renovacao";
import { fetchComTempoLimite } from "./rede";
import { enviarFila, type Remessa } from "./fila";

export { ETIQUETA_DO_ENVIO } from "./fila";

const remeter: Remessa = async (acoes) => {
  const token = await tokenEmSegundoPlano();
  if (!token) return 401;
  try {
    const resposta = await fetchComTempoLimite("/api/lancamentos/lote", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ acoes }),
    });
    return resposta.ok ? (await resposta.json()).resultados : resposta.status;
  } catch {
    return 0;
  }
};

/** Falha quando a fila não subiu, para o navegador tentar de novo mais tarde. */
export async function enviarEmSegundoPlano(): Promise<void> {
  if (!(await enviarFila(remeter))) throw new Error("a fila não subiu");
}
