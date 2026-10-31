// O envio da fila pelo service worker, sem tela aberta: o `sync` que o Android dispara quando a
// rede volta. O vite.config.ts empacota este arquivo dentro do service-worker.js; ele importa só
// o que roda fora da tela (sem React, sem o cliente da API, sem a biblioteca do SRP).
import { tokenEmSegundoPlano } from "../login/renovacao";
import { lerEGuardar, lerFila, lerResposta } from "./armazem";
import { fetchComTempoLimite } from "./rede";
import { enviarFila, LISTA, regraAceita, RELIDAS_DEPOIS_DE_REGRA, type Remessa } from "./fila";

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

/** Lê do servidor e guarda, como a tela: a leitura numerada não troca uma guardada mais nova. */
async function lerDoServidor(caminho: string) {
  const token = await tokenEmSegundoPlano();
  if (!token) return undefined;
  return lerEGuardar(caminho, async () => {
    const resposta = await fetchComTempoLimite(caminho, { headers: { Authorization: `Bearer ${token}` } });
    return resposta.ok ? ((await resposta.json()) as unknown) : undefined;
  });
}

/** Falha quando a fila não subiu, para o navegador tentar de novo mais tarde. */
export async function enviarEmSegundoPlano(): Promise<void> {
  // O envio tira o item da fila e só acerta a lista que já está guardada: sem ela, o lançamento
  // enviado sumiria do aparelho até a próxima leitura com internet. Como na tela (ticket 120),
  // sem a lista a fila não sobe (ticket 122).
  const pendentes = (await lerFila()).length;
  if (pendentes > 0 && !(await lerResposta(LISTA)) && !(await lerDoServidor(LISTA))) throw new Error("a lista não chegou");
  const enviou = await enviarFila(remeter);
  if (geradosNoServidor) {
    geradosNoServidor = false;
    // Lê de novo o que a regra aceita mudou, para a tela já abrir com os previstos e as parcelas.
    await Promise.all(RELIDAS_DEPOIS_DE_REGRA.map(lerDoServidor));
  }
  if (!enviou) throw new Error("a fila não subiu");
}
