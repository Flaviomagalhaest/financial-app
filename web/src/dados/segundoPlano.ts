// O envio da fila pelo service worker, sem tela aberta: o `sync` que o Android dispara quando a
// rede volta. O vite.config.ts empacota este arquivo dentro do service-worker.js; ele importa só
// o que roda fora da tela (sem React, sem o cliente da API, sem a biblioteca do SRP).
import { tokenEmSegundoPlano } from "../login/renovacao";
import { comTrava, guardarResposta } from "./armazem";
import { fetchComTempoLimite } from "./rede";
import { enviarFila, regraAceita, RELIDAS_DEPOIS_DE_REGRA, type Remessa } from "./fila";

export { ETIQUETA_DO_ENVIO } from "./fila";

/** Uma regra subiu neste envio: os previstos e as parcelas que o servidor fez só vêm nas leituras. */
let geradosNoServidor = false;

const remeter: Remessa = async (acoes) => {
  const token = await tokenEmSegundoPlano();
  if (!token) return 401;
  try {
    const resposta = await fetchComTempoLimite("/api/lancamentos/lote", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ acoes }),
    });
    if (!resposta.ok) return resposta.status;
    const { resultados } = await resposta.json();
    if (regraAceita(acoes, resultados)) geradosNoServidor = true;
    return resultados;
  } catch {
    return 0;
  }
};

/** Lê de novo e guarda o que a regra aceita mudou, para a tela já abrir com os previstos e as parcelas. */
async function relerDepoisDaRegra() {
  const token = await tokenEmSegundoPlano();
  if (!token) return;
  await Promise.all(
    RELIDAS_DEPOIS_DE_REGRA.map((caminho) =>
      comTrava("shared", async () => {
        const resposta = await fetchComTempoLimite(caminho, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null);
        if (resposta?.ok) await guardarResposta(caminho, await resposta.json());
      }),
    ),
  );
}

/** Falha quando a fila não subiu, para o navegador tentar de novo mais tarde. */
export async function enviarEmSegundoPlano(): Promise<void> {
  const enviou = await enviarFila(remeter);
  if (geradosNoServidor) {
    geradosNoServidor = false;
    await relerDepoisDaRegra();
  }
  if (!enviou) throw new Error("a fila não subiu");
}
