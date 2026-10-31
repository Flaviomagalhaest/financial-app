// O que o aparelho guarda para funcionar sem internet (ADR 0011): a última resposta de cada
// leitura e a fila do que não foi enviado. Banco próprio, separado do da sessão; a tela e o
// service worker usam este mesmo módulo.
import type { components } from "../api/schema";

export type NovoLancamento = components["schemas"]["NovoLancamento"];
export type Lancamento = components["schemas"]["Lancamento"];
export type NovaRecorrencia = components["schemas"]["NovaRecorrencia"];
export type Recorrencia = components["schemas"]["Recorrencia"];
export type AlteracaoDeRecorrencia = components["schemas"]["AlteracaoDeRecorrencia"];
export type NovoParcelamento = components["schemas"]["NovoParcelamento"];
export type Conflito = components["schemas"]["Conflito"];
export type Exclusao = components["schemas"]["Exclusao"];
/** O lançamento numa versão do servidor: a edição sobe só o que mudou desde ela (ADR 0011). */
export type Base = NovoLancamento & { versao: number };

/** O que todo pedido não enviado tem, seja de um lançamento, seja de uma regra. */
interface PedidoNaFila {
  /** O id do lançamento, ou o da recorrência ou do parcelamento. */
  id: string;
  /** Quando a primeira mudança ainda não enviada foi feita (ms), para o aviso de 24 h. */
  desde: number;
  /** A hora da última ação no aparelho (ms): é a hora que o servidor grava, não a da chegada. */
  feitoEm?: number;
  /** Sobe a cada mudança no aparelho: o envio só tira da fila o que não mudou no caminho. */
  revisao: number;
  /** Motivo da recusa do servidor; recusado não sobe até ser corrigido ou descartado. */
  recusa?: string;
  /** O criar (o do lançamento ou o da regra) enviado sem resposta: a revisão que talvez já esteja gravada no servidor. */
  talvezNoServidor?: number;
}

/** Uma mudança de lançamento não enviada: no máximo uma por lançamento, a soma do que se fez nele. */
export interface ItemDeLancamento extends PedidoNaFila {
  acao: "criar" | "editar" | "excluir" | "confirmar";
  /** O lançamento como fica; no confirmar, o previsto já realizado, com os ajustes. */
  lancamento?: NovoLancamento;
  /** Quando o envio que talvez gravou o criar saiu (ms): o planejamento lido depois dele já pode contá-lo. */
  tentadoEm?: number;
  /**
   * A versão do servidor sobre a qual a mudança foi feita: a edição sobe só os campos que
   * mudaram desde ela, e a exclusão leva a versão. No criar talvez gravado, o que foi enviado.
   */
  base?: Base;
  /** O servidor recusou como conflito: a versão dele e os campos que esperam a decisão. */
  conflito?: Conflito;
  /** A exclusão venceu: a mudança não foi salva e espera "Lançar de novo" ou ser dispensada. */
  exclusao?: Exclusao;
}

/** A recorrência criada no aparelho; os previstos o servidor gera ao receber. */
export interface ItemDeRecorrencia extends PedidoNaFila {
  acao: "criar_recorrencia";
  recorrencia: NovaRecorrencia;
}

/** O parcelamento criado no aparelho; as parcelas o servidor gera ao receber. */
export interface ItemDeParcelamento extends PedidoNaFila {
  acao: "criar_parcelamento";
  parcelamento: NovoParcelamento;
}

/**
 * A mudança "daqui para frente" (ou o fim) de uma recorrência que está no servidor. Cada mudança é
 * um pedido, com id próprio; o servidor reajusta os previstos ao receber.
 */
export interface ItemDeMudancaDaRecorrencia extends PedidoNaFila {
  acao: "alterar_recorrencia";
  recorrencia_id: string;
  /** A regra como a tela a mostrava: o envio leva dela os campos que a mudança traz (`antes`). */
  base: Recorrencia;
  alteracao: AlteracaoDeRecorrencia;
}

/** A recorrência excluída no aparelho, com o id dela: toma o lugar do criar que talvez já tenha subido. */
export interface ItemDeExclusaoDaRecorrencia extends PedidoNaFila {
  acao: "excluir_recorrencia";
  /** Para a tela dizer qual; o servidor só recebe o id. */
  recorrencia: NovaRecorrencia;
}

/** A regra vai como um pedido só e não se edita no aparelho, só se descarta. */
export type ItemDeRegra = ItemDeRecorrencia | ItemDeParcelamento | ItemDeMudancaDaRecorrencia | ItemDeExclusaoDaRecorrencia;

/** Um pedido não enviado: a mudança de um lançamento ou a de uma regra, pela `acao`. */
export type ItemDaFila = ItemDeLancamento | ItemDeRegra;

const ACOES_DE_LANCAMENTO: ReadonlySet<string> = new Set<ItemDeLancamento["acao"]>(["criar", "editar", "excluir", "confirmar"]);
export const deLancamento = (item: Pick<ItemDaFila, "acao">): item is ItemDeLancamento => ACOES_DE_LANCAMENTO.has(item.acao);

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
