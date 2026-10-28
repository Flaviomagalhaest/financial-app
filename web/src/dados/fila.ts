// A fila dos lançamentos não enviados: o que se faz no aparelho entra aqui e sobe em lote, na
// ordem (ADR 0011). Sem React nem cliente da API, porque o service worker também envia.
import type { components } from "../api/schema";
import { comTrava, emTransacao, lerFila, pedido, type Guardada, type ItemDaFila, type Lancamento, type NovoLancamento } from "./armazem";

export type Acao = components["schemas"]["Lote"]["acoes"][number];
export type Resultado = components["schemas"]["Resultado"];
/** Uma ida ao servidor: os resultados, na ordem das ações, ou o status HTTP da falha (0 sem rede). */
export type Remessa = (acoes: Acao[]) => Promise<Resultado[] | number>;

/** O `sync` que a tela pede e o service worker atende (service-worker.js). */
export const ETIQUETA_DO_ENVIO = "enviar-fila";
/** A lista de lançamentos guardada, que o resultado do envio já acerta. */
export const LISTA = "/api/lancamentos";
/** O mesmo limite do servidor (`LIMITE_DO_LOTE`). */
const LIMITE_DO_LOTE = 100;

async function mudar(id: string, proximo: (atual: ItemDaFila | undefined) => Omit<ItemDaFila, "id" | "desde" | "revisao"> | null) {
  await emTransacao("readwrite", async (fila) => {
    const atual: ItemDaFila | undefined = await pedido(fila.get(id));
    const item = proximo(atual);
    if (!item) await pedido(fila.delete(id));
    else await pedido(fila.put({ ...item, id, desde: atual?.desde ?? Date.now(), revisao: (atual?.revisao ?? 0) + 1 }));
  });
}

/** Criar (`novo`) ou editar; editar o que ainda não subiu muda o pedido de criar. Tira a recusa. */
export function enfileirarSalvar(lancamento: NovoLancamento, novo: boolean): Promise<void> {
  return mudar(lancamento.id, (atual) =>
    atual?.acao === "criar" || novo
      ? { acao: "criar", lancamento, talvezNoServidor: atual?.talvezNoServidor }
      : { acao: "editar", lancamento },
  );
}

/** Excluir o que com certeza não chegou ao servidor só o tira da fila. */
export function enfileirarExcluir(id: string): Promise<void> {
  return mudar(id, (atual) => (atual?.acao === "criar" && atual.talvezNoServidor === undefined ? null : { acao: "excluir" }));
}

/** Desiste da mudança não enviada: o aparelho volta a mostrar o que o servidor tem. */
export function descartar(id: string): Promise<void> {
  return mudar(id, () => null);
}

/**
 * As ações de um item. O criar que talvez já esteja no servidor com uma versão anterior vai com
 * a edição atrás: no servidor, reenviar o criar devolve o que já está gravado.
 */
function acoesDo(item: ItemDaFila): Acao[] {
  if (item.acao === "excluir") return [{ acao: "excluir", id: item.id }];
  const lancamento = item.lancamento!;
  const comEdicao = item.acao === "criar" && item.talvezNoServidor !== undefined && item.talvezNoServidor !== item.revisao;
  return comEdicao ? [{ acao: "criar", lancamento }, { acao: "editar", lancamento }] : [{ acao: item.acao, lancamento }];
}

export function ordenar(lista: Lancamento[]): Lancamento[] {
  return lista.sort((a, b) => b.data.localeCompare(a.data) || b.criado_em.localeCompare(a.criado_em));
}

async function aplicar(enviados: ItemDaFila[], resultados: Resultado[]) {
  await emTransacao("readwrite", async (fila, respostas) => {
    const guardada: Guardada<Lancamento[]> | undefined = await pedido(respostas.get(LISTA));
    let lista = guardada?.dados ?? [];
    for (const [i, enviado] of enviados.entries()) {
      const { resultado, motivo, lancamento } = resultados[i];
      const atual: ItemDaFila | undefined = await pedido(fila.get(enviado.id));
      const intacto = atual?.revisao === enviado.revisao;
      if (resultado === "recusada" || resultado === "conflito") {
        if (intacto) await pedido(fila.put({ ...atual, recusa: motivo ?? "conflito" }));
        continue;
      }
      // Excluído no aparelho enquanto subia: agora que existe no servidor, sai de lá também.
      const excluidoNoCaminho = resultado === "aceita" && !atual && enviado.acao === "criar";
      lista = lista.filter((l) => l.id !== enviado.id);
      if (lancamento && !excluidoNoCaminho) lista.push(lancamento);
      if (excluidoNoCaminho) await pedido(fila.put({ id: enviado.id, acao: "excluir", desde: enviado.desde, revisao: 1 }));
      else if (resultado === "descartada" || intacto) await pedido(fila.delete(enviado.id));
      // Mudou no caminho: o que era criar já existe lá, e a mudança nova sobe como edição.
      else if (atual?.acao === "criar") await pedido(fila.put({ ...atual, acao: "editar", talvezNoServidor: undefined }));
    }
    if (guardada) await pedido(respostas.put({ dados: ordenar(lista), em: guardada.em }, LISTA));
  });
}

/**
 * Sem resposta, o servidor pode ter gravado o criar. Guarda a primeira revisão que talvez tenha
 * chegado: uma tentativa depois, sem rede, não prova que a anterior não chegou.
 */
async function marcarSemResposta(enviados: ItemDaFila[]) {
  await emTransacao("readwrite", async (fila) => {
    for (const enviado of enviados) {
      const atual: ItemDaFila | undefined = await pedido(fila.get(enviado.id));
      if (enviado.acao === "criar" && atual?.acao === "criar" && atual.talvezNoServidor === undefined)
        await pedido(fila.put({ ...atual, talvezNoServidor: enviado.revisao }));
    }
  });
}

/** Um resultado por item: a recusa do criar, se houver, senão o da última ação dele. */
function porItem(itens: ItemDaFila[], resultados: Resultado[]): Resultado[] {
  let i = 0;
  return itens.map((item) => {
    const deste = resultados.slice(i, (i += acoesDo(item).length));
    return deste.find((r) => r.resultado === "recusada" || r.resultado === "conflito") ?? deste[deste.length - 1];
  });
}

/** Resultados de um lote; se o servidor recusa o formato do lote inteiro, manda um a um. */
async function remeterLote(remeter: Remessa, itens: ItemDaFila[]): Promise<Resultado[] | null> {
  const acoes = itens.flatMap(acoesDo);
  const resposta = await remeter(acoes);
  if (typeof resposta !== "number") return resposta.length === acoes.length ? porItem(itens, resposta) : null;
  if (resposta !== 422) return null;
  if (itens.length === 1) return [{ resultado: "recusada", motivo: "o servidor não aceitou este lançamento" }];
  const resultados: Resultado[] = [];
  for (const item of itens) {
    const um = await remeterLote(remeter, [item]);
    if (!um) return null;
    resultados.push(...um);
  }
  return resultados;
}

/** Os primeiros itens cujas ações cabem num lote. */
function ateOLimite(itens: ItemDaFila[]): ItemDaFila[] {
  let acoes = 0;
  return itens.filter((item) => (acoes += acoesDo(item).length) <= LIMITE_DO_LOTE);
}

/**
 * Sobe a fila em lotes, na ordem. Devolve `true` quando não sobrou nada para subir (recusados
 * esperam a pessoa) e `false` quando o servidor não respondeu: a fila fica para a próxima.
 */
export function enviarFila(remeter: Remessa): Promise<boolean> {
  return comTrava("exclusive", async () => {
    for (;;) {
      const lote = ateOLimite((await lerFila()).filter((item) => !item.recusa));
      if (lote.length === 0) return true;
      const resultados = await remeterLote(remeter, lote).catch(() => null);
      if (!resultados) {
        await marcarSemResposta(lote);
        return false;
      }
      await aplicar(lote, resultados);
    }
  });
}
