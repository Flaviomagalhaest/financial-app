// O que o aparelho guarda para funcionar sem internet (ADR 0011): a última resposta de cada
// leitura (a lista de lançamentos, que é a janela do aparelho do ADR 0025, um registro por
// lançamento) e a fila do que não foi enviado. Banco próprio, separado do da sessão; a tela e o
// service worker usam este mesmo módulo.
import type { components } from "../api/schema";
import { config } from "../config";
import { hoje, mesDepois } from "../lancamentos/datas";
import { recarregarParaAVersaoNova } from "./novaVersao";

export type NovoLancamento = components["schemas"]["NovoLancamento"];
export type Lancamento = components["schemas"]["Lancamento"];
export type NovaRecorrencia = components["schemas"]["NovaRecorrencia"];
export type Recorrencia = components["schemas"]["Recorrencia"];
export type AlteracaoDeRecorrencia = components["schemas"]["AlteracaoDeRecorrencia"];
export type NovoParcelamento = components["schemas"]["NovoParcelamento"];
export type Antecipacao = components["schemas"]["Antecipacao"];
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
  /**
   * A regra saiu com rede e a resposta ainda não voltou: quem a mandou (a página ou o service
   * worker). Se quem mandou fechou no caminho, a falha não chega a marcar `talvezNoServidor`, e a
   * marca de outro remetente diz isso (ticket 181).
   */
  enviadaPor?: string;
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
  /**
   * A mudança (criar, edição ou confirmação) que saiu e ainda não teve resposta: a revisão e as
   * ações dela. Ela talvez já esteja gravada; se o item mudou depois, ela sobe de novo antes, e a
   * mudança nova vai sobre a versão que ela gerou, não sobre a de antes (tickets 169 e 173).
   */
  enviadoSemResposta?: { revisao: number; acoes: components["schemas"]["Lote"]["acoes"] };
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
 * A antecipação de parcelas de um parcelamento do servidor. O `id` da fila é o da antecipação, gerado
 * no aparelho e enviado como a chave (ticket 154): o reenvio não antecipa as K parcelas seguintes.
 */
export interface ItemDeAntecipacao extends PedidoNaFila {
  acao: "antecipar_parcelas";
  parcelamento_id: string;
  /** Para a tela dizer qual; o servidor só recebe o id. */
  descricao: string;
  antecipacao: Antecipacao;
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
export type ItemDeRegra = ItemDeRecorrencia | ItemDeParcelamento | ItemDeAntecipacao | ItemDeMudancaDaRecorrencia | ItemDeExclusaoDaRecorrencia;

/** Um pedido não enviado: a mudança de um lançamento ou a de uma regra, pela `acao`. */
export type ItemDaFila = ItemDeLancamento | ItemDeRegra;

const ACOES_DE_LANCAMENTO: ReadonlySet<string> = new Set<ItemDeLancamento["acao"]>(["criar", "editar", "excluir", "confirmar"]);
export const deLancamento = (item: Pick<ItemDaFila, "acao">): item is ItemDeLancamento => ACOES_DE_LANCAMENTO.has(item.acao);

/** O primeiro mês da janela do aparelho (`AAAA-MM-01`), como o servidor a conta (`inicio_da_janela`). */
export const inicioDaJanela = () => mesDepois(hoje(), 1 - config.janelaDoAparelhoMeses);

/**
 * A versão do servidor sobre a qual a mudança da fila foi feita, para o lançamento que não está na
 * lista guardada: o que ficou fora da janela do aparelho (ADR 0025), aberto com internet. O criar
 * não tem: a base dele é o que foi enviado, que talvez nem esteja no servidor.
 */
export function baseDaMudanca(item: ItemDeLancamento): Lancamento | undefined {
  return item.acao === "criar" ? undefined : (item.base as Lancamento | undefined);
}

export interface Guardada<T> {
  dados: T;
  /** Quando o servidor respondeu (ms): "atualizado às 14:32". */
  em: number;
  /** O número da leitura que a trouxe (`lerEGuardar`); a guardada antes dele não o tem. */
  leitura?: number;
}

const BANCO = "financial-app-dados";
const FILA = "fila";
const RESPOSTAS = "respostas";
/** A lista de lançamentos guardada, um registro por lançamento (ticket 164). */
const LANCAMENTOS = "lancamentos";
const CANAL = "financial-app-dados";

/**
 * A lista de lançamentos: a única resposta guardada lançamento por lançamento. Em `respostas`, sob
 * este caminho, fica só a hora e o número da leitura; os lançamentos ficam na loja própria.
 */
export const LISTA = "/api/lancamentos";
/** A chave que `ouvirMudancas` usa para a fila; as respostas usam o caminho delas. */
export const NA_FILA = "fila";
/** Tudo mudou (sair da conta, ou um aviso de uma versão anterior do app). */
const TUDO = "*";

/** A versão 2 guarda a lista lançamento por lançamento e desfaz o bloco da versão 1. */
function abrir(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const abertura = indexedDB.open(BANCO, 2);
    abertura.onupgradeneeded = ({ oldVersion }) => {
      const banco = abertura.result;
      if (oldVersion < 1) {
        banco.createObjectStore(FILA, { keyPath: "id" });
        banco.createObjectStore(RESPOSTAS);
      }
      if (oldVersion < 2) {
        const lancamentos = banco.createObjectStore(LANCAMENTOS, { keyPath: "id" });
        const respostas = abertura.transaction!.objectStore(RESPOSTAS);
        const bloco = respostas.get(LISTA);
        bloco.onsuccess = () => {
          const guardada = bloco.result as Guardada<Lancamento[]> | undefined;
          if (!guardada) return;
          const { dados, ...marca } = guardada;
          for (const lancamento of dados) lancamentos.put(lancamento);
          respostas.put(marca, LISTA);
        };
      }
    };
    abertura.onsuccess = () => resolve(abertura.result);
    abertura.onerror = () => {
      // O banco já está numa versão mais nova: só o código novo o abre (ticket 168).
      if (abertura.error?.name === "VersionError") recarregarParaAVersaoNova();
      reject(abertura.error);
    };
  });
}

export function pedido<T>(p: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    p.onsuccess = () => resolve(p.result);
    p.onerror = () => reject(p.error);
  });
}

const ouvintes = new Map<() => void, ReadonlySet<string>>();
function avisar(mudou: ReadonlySet<string>) {
  for (const [ouvinte, chaves] of ouvintes) if (mudou.has(TUDO) || [...chaves].some((chave) => mudou.has(chave))) ouvinte();
}
// Avisa as outras abas e o service worker (e ouve deles) do que mudou no que está guardado. O aviso
// de uma versão anterior do app não diz o quê: vale como tudo.
const canal = typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(CANAL);
canal?.addEventListener("message", ({ data }) => avisar(new Set(Array.isArray(data) ? (data as string[]) : [TUDO])));

/**
 * Chamado quando muda, aqui ou noutro contexto, o que está guardado sob uma das `chaves`: o caminho
 * de uma resposta, ou `NA_FILA` para a fila. Uma escrita numa resposta não avisa quem lê outra.
 */
export function ouvirMudancas(chaves: readonly string[], ouvinte: () => void): () => void {
  ouvintes.set(ouvinte, new Set(chaves));
  return () => void ouvintes.delete(ouvinte);
}

/** A loja com as escritas anotadas em `mudou`, pela chave que `ouvirMudancas` usa. */
function anotada(loja: IDBObjectStore, mudou: Set<string>): IDBObjectStore {
  const chaveDe = (metodo: string, args: unknown[]) => {
    if (loja.name === FILA) return NA_FILA;
    if (loja.name === LANCAMENTOS) return LISTA;
    if (metodo === "clear") return TUDO;
    return String(metodo === "delete" ? args[0] : args[1]);
  };
  return new Proxy(loja, {
    get(alvo, nome) {
      const valor = Reflect.get(alvo, nome, alvo);
      if (typeof valor !== "function") return valor;
      if (nome === "put" || nome === "add" || nome === "delete" || nome === "clear")
        return (...args: unknown[]) => {
          mudou.add(chaveDe(nome, args));
          return valor.apply(alvo, args);
        };
      return valor.bind(alvo);
    },
  });
}

/**
 * Roda `trabalho` numa transação sobre a fila, as respostas e os lançamentos da lista; só pode
 * esperar pedidos do próprio IndexedDB, senão a transação fecha no meio. Uma escrita confirmada
 * avisa quem ouve o que ela mudou. Na loja `lancamentos`, cada registro é um lançamento da lista,
 * pelo `id`; ela só vale com a marca da leitura em `respostas` (`LISTA`).
 */
export async function emTransacao<T>(
  modo: IDBTransactionMode,
  trabalho: (fila: IDBObjectStore, respostas: IDBObjectStore, lancamentos: IDBObjectStore) => Promise<T>,
): Promise<T> {
  const banco = await abrir();
  try {
    const transacao = banco.transaction([FILA, RESPOSTAS, LANCAMENTOS], modo);
    const fim = new Promise<void>((resolve, reject) => {
      transacao.oncomplete = () => resolve();
      transacao.onerror = transacao.onabort = () => reject(transacao.error);
    });
    const mudou = new Set<string>();
    const [fila, respostas, lancamentos] = [FILA, RESPOSTAS, LANCAMENTOS].map((nome) => anotada(transacao.objectStore(nome), mudou));
    let resultado: T;
    try {
      resultado = await trabalho(fila, respostas, lancamentos);
    } catch (erro) {
      transacao.abort();
      throw erro;
    }
    await fim;
    if (mudou.size > 0) {
      avisar(mudou);
      canal?.postMessage([...mudou]);
    }
    return resultado;
  } finally {
    banco.close();
  }
}

/** Do mais novo ao mais antigo, como o servidor manda a lista. */
function ordenar(lista: Lancamento[]): Lancamento[] {
  return lista.sort((a, b) => b.data.localeCompare(a.data) || b.criado_em.localeCompare(a.criado_em));
}

/** A resposta guardada; a lista vem montada dos lançamentos guardados um a um. */
export const lerResposta = <T>(caminho: string) =>
  emTransacao("readonly", async (_, respostas, lancamentos) => {
    const guardada = (await pedido(respostas.get(caminho))) as Guardada<T> | Omit<Guardada<T>, "dados"> | undefined;
    if (!guardada || caminho !== LISTA) return guardada as Guardada<T> | undefined;
    return { ...guardada, dados: ordenar(await pedido(lancamentos.getAll())) as T } as Guardada<T>;
  });

/** Se há uma resposta guardada, sem ler a lista inteira para saber. */
export const temResposta = (caminho: string) => emTransacao("readonly", async (_, respostas) => (await pedido(respostas.count(caminho))) > 0);

/**
 * Guarda a lista lida: grava só os lançamentos que mudaram desde a guardada e apaga os que o
 * servidor não mandou mais. A lista é a janela do aparelho (ADR 0025): quando o mês vira, o que
 * saiu dela some, menos o que tem mudança na fila (não enviada, recusada ou em conflito), que a
 * tela ainda mostra e que a fila edita sobre a versão guardada.
 */
async function guardarALista(fila: IDBObjectStore, respostas: IDBObjectStore, lancamentos: IDBObjectStore, lida: Guardada<Lancamento[]>) {
  const { dados, ...marca } = lida;
  const guardados = new Map(((await pedido(lancamentos.getAll())) as Lancamento[]).map((l) => [l.id, JSON.stringify(l)]));
  const naFila = new Set(((await pedido(fila.getAll())) as ItemDaFila[]).filter(deLancamento).map((item) => item.id));
  const escritas: Promise<unknown>[] = [];
  for (const lancamento of dados) {
    if (guardados.get(lancamento.id) !== JSON.stringify(lancamento)) escritas.push(pedido(lancamentos.put(lancamento)));
    guardados.delete(lancamento.id);
  }
  for (const id of guardados.keys()) if (!naFila.has(id)) escritas.push(pedido(lancamentos.delete(id)));
  escritas.push(pedido(respostas.put(marca, LISTA)));
  await Promise.all(escritas);
}

export const agora = () => performance.timeOrigin + performance.now();
let ultimaLeitura = 0;
/**
 * O número da leitura é a hora em que ela sai (ms, com fração): a tela, as abas e o service worker
 * do aparelho contam pelo mesmo relógio, sem uma transação a mais no IndexedDB a cada leitura.
 * Neste contexto, cada uma tem número maior que o da anterior.
 */
function numerarLeitura(): number {
  ultimaLeitura = Math.max(agora(), ultimaLeitura + 0.001);
  return ultimaLeitura;
}

/** A guardada é de uma leitura que saiu depois. Uma que saiu "depois de agora" é de antes de o relógio do aparelho voltar: não vale. */
const maisNova = (guardada: Omit<Guardada<unknown>, "dados"> | undefined, numero: number) =>
  !!guardada?.leitura && guardada.leitura > numero && guardada.leitura <= agora();

/** A última leitura de cada caminho ainda sem resposta neste contexto, e quando ela foi pedida (ms). */
const emAndamento = new Map<string, { leitura: Promise<unknown>; pedidaEm: number }>();

/**
 * Busca no servidor (`ler`, `undefined` quando ele não respondeu) e guarda a resposta. As leituras
 * de uma resposta correm juntas, na tela, noutra aba ou no service worker, e a que saiu antes pode
 * chegar depois: numeradas na saída, a mais velha não troca a guardada (tickets 120 e 122).
 *
 * Com `juntarDesde` (ms, no relógio de `agora`), a leitura do caminho pedida neste contexto desde
 * então, ainda sem resposta, serve: a tela que abre com vários leitores do mesmo caminho faz um GET
 * só. A pedida antes não serve: pode ter saído antes de uma mudança no servidor, ou estar presa
 * numa rede que acabou de voltar.
 */
export function lerEGuardar<D>(caminho: string, ler: () => Promise<D | undefined>, { juntarDesde }: { juntarDesde?: number } = {}): Promise<D | undefined> {
  const andamento = emAndamento.get(caminho);
  if (juntarDesde !== undefined && andamento && andamento.pedidaEm >= juntarDesde) return andamento.leitura as Promise<D | undefined>;
  const leitura = comTrava("shared", async () => {
    const numero = numerarLeitura();
    const dados = await ler().catch(() => undefined);
    if (dados === undefined) return undefined;
    await emTransacao("readwrite", async (fila, respostas, lancamentos) => {
      const guardada = (await pedido(respostas.get(caminho))) as Omit<Guardada<D>, "dados"> | undefined;
      if (maisNova(guardada, numero)) return;
      const lida = { dados, em: Date.now(), leitura: numero } satisfies Guardada<D>;
      if (caminho === LISTA) await guardarALista(fila, respostas, lancamentos, lida as Guardada<unknown> as Guardada<Lancamento[]>);
      else await pedido(respostas.put(lida, caminho));
    });
    return dados;
  }).finally(() => {
    if (emAndamento.get(caminho)?.leitura === leitura) emAndamento.delete(caminho);
  });
  emAndamento.set(caminho, { leitura, pedidaEm: agora() });
  return leitura;
}

export async function lerFila(): Promise<ItemDaFila[]> {
  const itens = await emTransacao("readonly", (fila) => pedido(fila.getAll()) as Promise<ItemDaFila[]>);
  return itens.sort((a, b) => a.desde - b.desde);
}

/** Sair da conta apaga tudo o que o aparelho guardou, fila inclusive. */
export const apagarTudo = () =>
  emTransacao("readwrite", async (fila, respostas, lancamentos) => {
    await pedido(fila.clear());
    await pedido(respostas.clear());
    await pedido(lancamentos.clear());
  });

/**
 * Trava entre a tela, outras abas e o service worker: o envio é exclusivo e a leitura do servidor
 * é compartilhada, para uma resposta lida antes do envio não ser guardada por cima do resultado.
 */
export function comTrava<T>(modo: LockMode, trabalho: () => Promise<T>): Promise<T> {
  return navigator.locks ? (navigator.locks.request("financial-app-fila", { mode: modo }, trabalho) as Promise<T>) : trabalho();
}
