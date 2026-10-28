// O que o aparelho guarda para funcionar sem internet (ADR 0011): a última resposta de cada
// leitura e a fila dos lançamentos não enviados. Banco próprio, separado do da sessão; a tela e o
// service worker usam este mesmo módulo.
import type { components } from "../api/schema";

export type NovoLancamento = components["schemas"]["NovoLancamento"];
export type Lancamento = components["schemas"]["Lancamento"];

/** Uma mudança não enviada: no máximo uma por lançamento, a soma do que se fez nele. */
export interface ItemDaFila {
  /** O id do lançamento. */
  id: string;
  acao: "criar" | "editar" | "excluir";
  lancamento?: NovoLancamento;
  /** Quando a primeira mudança ainda não enviada foi feita (ms), para o aviso de 24 h. */
  desde: number;
  /** Sobe a cada mudança no aparelho: o envio só tira da fila o que não mudou no caminho. */
  revisao: number;
  /** Motivo da recusa do servidor; recusado não sobe até ser corrigido ou descartado. */
  recusa?: string;
  /** No criar enviado sem resposta: a revisão que talvez já esteja gravada no servidor. */
  talvezNoServidor?: number;
}

export interface Guardada<T> {
  dados: T;
  /** Quando o servidor respondeu (ms): "atualizado às 14:32". */
  em: number;
}

const BANCO = "financial-app-dados";
const FILA = "fila";
const RESPOSTAS = "respostas";
const CANAL = "financial-app-dados";

function abrir(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const abertura = indexedDB.open(BANCO, 1);
    abertura.onupgradeneeded = () => {
      abertura.result.createObjectStore(FILA, { keyPath: "id" });
      abertura.result.createObjectStore(RESPOSTAS);
    };
    abertura.onsuccess = () => resolve(abertura.result);
    abertura.onerror = () => reject(abertura.error);
  });
}

export function pedido<T>(p: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    p.onsuccess = () => resolve(p.result);
    p.onerror = () => reject(p.error);
  });
}

const ouvintes = new Set<() => void>();
// Avisa as outras abas e o service worker (e ouve deles) quando algo guardado muda.
const canal = typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(CANAL);
canal?.addEventListener("message", () => ouvintes.forEach((ouvinte) => ouvinte()));

/** Chamado sempre que a fila ou uma resposta guardada muda, aqui ou noutro contexto. */
export function ouvirMudancas(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte);
  return () => void ouvintes.delete(ouvinte);
}

/**
 * Roda `trabalho` numa transação sobre a fila e as respostas; só pode esperar pedidos do próprio
 * IndexedDB, senão a transação fecha no meio. Uma escrita confirmada avisa os ouvintes.
 */
export async function emTransacao<T>(
  modo: IDBTransactionMode,
  trabalho: (fila: IDBObjectStore, respostas: IDBObjectStore) => Promise<T>,
): Promise<T> {
  const banco = await abrir();
  try {
    const transacao = banco.transaction([FILA, RESPOSTAS], modo);
    const fim = new Promise<void>((resolve, reject) => {
      transacao.oncomplete = () => resolve();
      transacao.onerror = transacao.onabort = () => reject(transacao.error);
    });
    let resultado: T;
    try {
      resultado = await trabalho(transacao.objectStore(FILA), transacao.objectStore(RESPOSTAS));
    } catch (erro) {
      transacao.abort();
      throw erro;
    }
    await fim;
    if (modo === "readwrite") {
      ouvintes.forEach((ouvinte) => ouvinte());
      canal?.postMessage("mudou");
    }
    return resultado;
  } finally {
    banco.close();
  }
}

export const lerResposta = <T>(caminho: string) =>
  emTransacao("readonly", (_, respostas) => pedido(respostas.get(caminho)) as Promise<Guardada<T> | undefined>);

export const guardarResposta = <T>(caminho: string, dados: T) =>
  emTransacao("readwrite", async (_, respostas) => void (await pedido(respostas.put({ dados, em: Date.now() }, caminho))));

export async function lerFila(): Promise<ItemDaFila[]> {
  const itens = await emTransacao("readonly", (fila) => pedido(fila.getAll()) as Promise<ItemDaFila[]>);
  return itens.sort((a, b) => a.desde - b.desde);
}

/** Sair da conta apaga tudo o que o aparelho guardou, fila inclusive. */
export const apagarTudo = () =>
  emTransacao("readwrite", async (fila, respostas) => {
    await pedido(fila.clear());
    await pedido(respostas.clear());
  });

/**
 * Trava entre a tela, outras abas e o service worker: o envio é exclusivo e a leitura do servidor
 * é compartilhada, para uma resposta lida antes do envio não ser guardada por cima do resultado.
 */
export function comTrava<T>(modo: LockMode, trabalho: () => Promise<T>): Promise<T> {
  return navigator.locks ? (navigator.locks.request("financial-app-fila", { mode: modo }, trabalho) as Promise<T>) : trabalho();
}
