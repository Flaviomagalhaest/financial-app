// A rede como a camada de dados a conhece: toda chamada tem tempo limite, e a última que falhou ou
// demorou conta como "sem internet", mesmo com o navegador dizendo que há rede (Wi-Fi sem saída).
// Só o que roda fora da tela entra aqui: o service worker empacota este arquivo, com o estado dele
// à parte: a falha vista lá não chega às telas.
import valoresIniciais from "../../../config/valores-iniciais.json";

const TEMPO_LIMITE_MS = valoresIniciais.tempoLimiteDaRedeSegundos * 1000;

let semResposta = false;
const ouvintes = new Set<() => void>();

function marcarSemResposta(valor: boolean) {
  if (semResposta === valor) return;
  semResposta = valor;
  ouvintes.forEach((avisar) => avisar());
}

/** A última chamada falhou ou passou do tempo, e nenhuma deu certo depois. */
export const ultimaChamadaFalhou = () => semResposta;

export function ouvirFalhaDeRede(avisar: () => void): () => void {
  ouvintes.add(avisar);
  return () => void ouvintes.delete(avisar);
}

/** O navegador avisou que a rede voltou: a próxima chamada decide, até lá vale o aviso dele. */
export const redeVoltou = () => marcarSemResposta(false);

/** `fetch` com tempo limite, que registra se o servidor respondeu. Falha como o `fetch` falha. */
export async function fetchComTempoLimite(entrada: RequestInfo | URL, opcoes?: RequestInit): Promise<Response> {
  const limite = AbortSignal.timeout(TEMPO_LIMITE_MS);
  const sinal = opcoes?.signal ?? (entrada instanceof Request ? entrada.signal : undefined);
  try {
    const resposta = await fetch(entrada, { ...opcoes, signal: sinal ? AbortSignal.any([sinal, limite]) : limite });
    marcarSemResposta(false);
    return resposta;
  } catch (erro) {
    // Cancelada por quem chamou não diz nada sobre a rede.
    if (!sinal?.aborted) marcarSemResposta(true);
    throw erro;
  }
}
