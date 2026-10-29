// A camada de dados do aparelho: o único ponto de leitura e escrita das telas (ADR 0011). Lê do
// servidor guardando a última resposta, escreve pela fila e a sobe sozinha quando dá.
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { hoje } from "../lancamentos/datas";
import {
  apagarTudo,
  comTrava,
  guardarResposta,
  lerFila,
  lerResposta,
  ouvirMudancas,
  type Base,
  type Conflito,
  type Exclusao,
  type Guardada,
  type ItemDaFila,
  type Lancamento,
  type NovoLancamento,
} from "./armazem";
import {
  decidirConflito,
  descartar,
  enfileirarExcluir,
  enfileirarSalvar,
  enviarFila,
  ETIQUETA_DO_ENVIO,
  excluirMesmoAssim,
  guardarConflito,
  lancarDeNovo,
  LISTA,
  type Remessa,
} from "./fila";

export type Conta = components["schemas"]["Conta"];
export type Categoria = components["schemas"]["Categoria"];
export type Pessoa = components["schemas"]["Pessoa"];
export type Cartao = components["schemas"]["Cartao"];
export type { Campo } from "./fila";
export type { Conflito, Exclusao, ItemDaFila, Lancamento, NovoLancamento };
export { comoNovo } from "./fila";

/** Lançamento como o aparelho o mostra: o do servidor com as mudanças da fila por cima. */
export type LancamentoNaTela = NovoLancamento & {
  situacao: "previsto" | "realizado";
  /** O do servidor; o não enviado repete o da versão que o servidor tem. */
  atrasado?: boolean;
  /** A versão do servidor que a tela mostra; o não enviado não tem. */
  versao?: number;
  /** Autoria e origem, como o servidor as tem; o criado só no aparelho ainda não tem. */
  criado_por?: string;
  criado_em?: string;
  alterado_por?: string;
  alterado_em?: string;
  fonte?: Lancamento["fonte"];
  /** A recorrência que gerou o previsto. */
  recorrencia_id?: Lancamento["recorrencia_id"];
  /** O lançamento da outra pessoa que este parece repetir. */
  parece_repetido_de?: string | null;
  /** A hora da última ação no aparelho, enquanto a mudança não subiu. */
  feitoEm?: number;
  naoEnviado: boolean;
  recusa?: string;
  /** A mudança do aparelho espera decisão; enquanto isso, a tela mostra a versão do servidor. */
  conflito?: boolean;
  /** A outra pessoa excluiu: a tela mostra a mudança que não foi salva, para "Lançar de novo". */
  exclusao?: Exclusao;
};

const LEITURAS = {
  "/api/lancamentos": () => api.GET("/api/lancamentos"),
  "/api/contas": () => api.GET("/api/contas"),
  "/api/contas?arquivadas=true": () => api.GET("/api/contas", { params: { query: { arquivadas: true } } }),
  "/api/categorias": () => api.GET("/api/categorias"),
  "/api/pessoas": () => api.GET("/api/pessoas"),
  "/api/tags": () => api.GET("/api/tags"),
  "/api/cartoes": () => api.GET("/api/cartoes"),
};
type Caminho = keyof typeof LEITURAS;
type Dados<C extends Caminho> = NonNullable<Awaited<ReturnType<(typeof LEITURAS)[C]>>["data"]>;

/** A resposta do servidor, ou a última guardada; `aoVivo` diz se a última busca deu certo. */
function useResposta<C extends Caminho>(caminho: C) {
  const [guardada, setGuardada] = useState<Guardada<Dados<C>> | null>(null);
  const [aoVivo, setAoVivo] = useState<boolean | null>(null);

  const buscar = useCallback(async () => {
    const dados = await comTrava("shared", async () => {
      const { data } = await LEITURAS[caminho]().catch(() => ({ data: undefined }));
      if (data) await guardarResposta(caminho, data);
      return data;
    });
    setAoVivo(!!dados);
  }, [caminho]);

  useEffect(() => {
    let ativo = true;
    const ler = () =>
      void lerResposta<Dados<C>>(caminho).then((g) => {
        if (ativo && g) setGuardada(g);
      });
    ler();
    void buscar();
    const parar = ouvirMudancas(ler);
    // A rede voltou ou o app voltou à frente: a resposta guardada pode estar velha.
    const buscarDeNovo = () => document.visibilityState === "visible" && void buscar();
    window.addEventListener("online", buscarDeNovo);
    document.addEventListener("visibilitychange", buscarDeNovo);
    return () => {
      ativo = false;
      parar();
      window.removeEventListener("online", buscarDeNovo);
      document.removeEventListener("visibilitychange", buscarDeNovo);
    };
  }, [caminho, buscar]);

  return {
    dados: guardada?.dados ?? null,
    /** Hora da resposta guardada, só quando o servidor não respondeu agora. */
    atualizadoEm: aoVivo === false && guardada ? guardada.em : null,
    semDados: aoVivo === false && !guardada,
    buscar,
  };
}

/** "atualizado às 14:32", para a resposta guardada que a tela mostra sem internet. */
export function atualizadoAs(em: number): string {
  return `atualizado às ${new Date(em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
}

/** A fila do aparelho, atualizada a cada mudança. */
export function useFila(): ItemDaFila[] {
  const [itens, setItens] = useState<ItemDaFila[]>([]);
  useEffect(() => {
    let ativo = true;
    const ler = () => void lerFila().then((lidos) => ativo && setItens(lidos));
    ler();
    const parar = ouvirMudancas(ler);
    return () => {
      ativo = false;
      parar();
    };
  }, []);
  return itens;
}


/** A mesma regra do servidor: sem situação, data futura é prevista; só mudar a data refaz. */
function situacaoNoAparelho(lancamento: NovoLancamento, anterior?: LancamentoNaTela) {
  if (lancamento.situacao) return lancamento.situacao;
  if (anterior && anterior.data === lancamento.data) return anterior.situacao;
  return lancamento.data > hoje() ? "previsto" : "realizado";
}

function naTela(servidor: Lancamento[], fila: ItemDaFila[]): LancamentoNaTela[] {
  const porId = new Map<string, LancamentoNaTela>(servidor.map((l) => [l.id, { ...l, naoEnviado: false }]));
  const novos: LancamentoNaTela[] = [];
  for (const item of fila) {
    const anterior = porId.get(item.id);
    if (item.conflito) {
      const servidor = anterior ?? { ...item.conflito.lancamento, naoEnviado: false };
      porId.set(item.id, { ...servidor, conflito: true });
      continue;
    }
    if (item.acao === "excluir") {
      porId.delete(item.id);
      continue;
    }
    const lancamento = item.lancamento!;
    const situacao = situacaoNoAparelho(lancamento, anterior);
    // O atraso é regra do servidor: vale o dele enquanto a mudança não mexe em data nem situação.
    const atrasado = anterior?.data === lancamento.data && anterior.situacao === situacao ? anterior.atrasado : undefined;
    const mostrado = { ...anterior, ...lancamento, situacao, atrasado, naoEnviado: true, recusa: item.recusa, exclusao: item.exclusao, feitoEm: item.feitoEm };
    if (anterior) porId.set(item.id, mostrado);
    else novos.unshift(mostrado);
  }
  // Os não enviados novos vêm antes dos do servidor na mesma data, como os mais recentes.
  return [...novos, ...porId.values()].sort((a, b) => b.data.localeCompare(a.data));
}

/** Lançamentos do servidor (ou os guardados) com a fila por cima. */
export function useLancamentos() {
  const { dados, atualizadoEm, semDados } = useResposta(LISTA);
  const fila = useFila();
  const lancamentos = useMemo(() => (dados ? naTela(dados, fila) : semDados ? naTela([], fila) : null), [dados, fila, semDados]);
  return { lancamentos, atualizadoEm, semDados };
}

/**
 * Contas, cartões e categorias do casal; `carregado` quando há resposta do servidor, nova ou
 * guardada. Os cartões não arquivados (titulares e adicionais) vêm à parte, e `contasECartoes`
 * dá o nome de qualquer `conta_id`: a compra no cartão guarda nele o cartão (ADR 0015).
 */
export function useCadastro() {
  const contas = useResposta("/api/contas");
  const cartoes = useResposta("/api/cartoes");
  const categorias = useResposta("/api/categorias");
  const recarregar = useCallback(async () => {
    await Promise.all([contas.buscar(), categorias.buscar()]);
  }, [contas.buscar, categorias.buscar]);
  return {
    contas: contas.dados ?? [],
    cartoes: cartoes.dados ?? [],
    contasECartoes: useMemo(() => [...(contas.dados ?? []), ...(cartoes.dados ?? [])], [contas.dados, cartoes.dados]),
    categorias: categorias.dados ?? [],
    carregado: !!contas.dados && !!categorias.dados,
    atualizadoEm: contas.atualizadoEm ?? categorias.atualizadoEm,
    recarregar,
  };
}

/** As duas pessoas do casal; `euId` é a que está usando o aparelho. */
export function usePessoas() {
  const { dados } = useResposta("/api/pessoas");
  const pessoas = dados ?? [];
  const nomeDe = (id: string | null | undefined) => pessoas.find((p) => p.id === id)?.nome ?? "a outra pessoa";
  return { pessoas, euId: pessoas.find((p) => p.eu)?.id, nomeDe };
}

/** A tag é a mesma com outra caixa ("Novo ap" e "novo ap"), como no servidor. */
export const chaveDaTag = (nome: string) => nome.toLocaleLowerCase("pt-BR");

/**
 * Os nomes das tags para escolher no lançamento: as do servidor que não estão arquivadas e as dos
 * lançamentos do aparelho, para a tag criada num lançamento ainda não enviado já aparecer no próximo.
 */
export function useTags(): string[] {
  const { dados } = useResposta("/api/tags");
  const { lancamentos } = useLancamentos();
  return useMemo(() => {
    const arquivadas = new Set((dados ?? []).filter((t) => t.arquivada).map((t) => chaveDaTag(t.nome)));
    const porNome = new Map<string, string>();
    for (const nome of [...(dados ?? []).filter((t) => !t.arquivada).map((t) => t.nome), ...(lancamentos ?? []).flatMap((l) => l.tags ?? [])]) {
      const chave = chaveDaTag(nome);
      if (!arquivadas.has(chave) && !porNome.has(chave)) porNome.set(chave, nome);
    }
    return [...porNome.values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [dados, lancamentos]);
}

/** Todas as contas, arquivadas inclusive, para a tela que as configura. */
export function useContasComArquivadas() {
  const { dados, atualizadoEm, buscar } = useResposta("/api/contas?arquivadas=true");
  return { contas: dados ?? [], atualizadoEm, recarregar: buscar };
}

/** Se o navegador diz que há rede; para desativar o que precisa de internet. */
export function useConexao(): boolean {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const mudou = () => setOnline(navigator.onLine);
    window.addEventListener("online", mudou);
    window.addEventListener("offline", mudou);
    return () => {
      window.removeEventListener("online", mudou);
      window.removeEventListener("offline", mudou);
    };
  }, []);
  return online;
}

const remeter: Remessa = async (acoes) => {
  try {
    const { data, response } = await api.POST("/api/lancamentos/lote", { body: { acoes } });
    return data ? data.resultados : response.status;
  } catch {
    return 0;
  }
};

/** No Android, o navegador chama o service worker quando a rede volta, mesmo com o app fechado. */
function pedirEnvioEmSegundoPlano() {
  void navigator.serviceWorker?.ready
    .then((registro) => (registro as ServiceWorkerRegistration & { sync?: { register(tag: string): Promise<void> } }).sync?.register(ETIQUETA_DO_ENVIO))
    .catch(() => undefined);
}

/** Sobe a fila agora; `false` quando o servidor não respondeu. */
export async function enviarAgora(): Promise<boolean> {
  const enviou = await enviarFila(remeter);
  if (!enviou) pedirEnvioEmSegundoPlano();
  return enviou;
}

/** A versão do servidor que a tela mostrava, quando é a do servidor (não a da fila). */
function baseDe(mostrado?: LancamentoNaTela): Base | undefined {
  return mostrado && !mostrado.naoEnviado && mostrado.versao !== undefined ? { ...mostrado, versao: mostrado.versao } : undefined;
}

/** `mostrado` é o lançamento que a tela abriu para editar: a mudança vale sobre a versão dele. */
export async function salvarLancamento(lancamento: NovoLancamento, novo: boolean, mostrado?: LancamentoNaTela): Promise<void> {
  await enfileirarSalvar(lancamento, novo, baseDe(mostrado));
  void enviarAgora();
}

export async function excluirLancamento(mostrado: LancamentoNaTela): Promise<void> {
  await enfileirarExcluir(mostrado.id, baseDe(mostrado));
  void enviarAgora();
}

export const descartarNaoEnviado = descartar;

/** O casal conferiu o "Parece repetido": exige internet, porque não é uma mudança do lançamento. */
export async function manterOsDois(id: string): Promise<boolean> {
  const { data } = await api.POST("/api/lancamentos/{id}/manter-os-dois", { params: { path: { id } } }).catch(() => ({ data: undefined }));
  if (!data) return false;
  const { data: lista } = await api.GET("/api/lancamentos");
  if (lista) await comTrava("shared", () => guardarResposta(LISTA, lista));
  return true;
}

/** A mudança na fila sobe na hora, se houver internet. */
function eEnvia<A extends unknown[]>(mudar: (...args: A) => Promise<void>) {
  return async (...args: A) => {
    await mudar(...args);
    void enviarAgora();
  };
}

export const decidir = eEnvia(decidirConflito);
export const excluirApesarDoConflito = eEnvia(excluirMesmoAssim);
export const lancarDeNovoOExcluido = eEnvia(lancarDeNovo);
export { guardarConflito };

/** Cadastro precisa de internet (ADR 0011): não entra na fila. `false` se o servidor recusou. */
export async function criarConta(nome: string, tipo: Conta["tipo"]): Promise<boolean> {
  return !!(await api.POST("/api/contas", { body: { nome, tipo } })).data;
}

export async function criarCategoria(nome: string, tipo: Categoria["tipo"]): Promise<boolean> {
  return !!(await api.POST("/api/categorias", { body: { nome, tipo } })).data;
}

export type NovaTransferencia = components["schemas"]["NovaTransferencia"];

/**
 * Transferência precisa de internet (ADR 0011): não entra na fila. Devolve o motivo da recusa, ou
 * `null` quando gravou. Reenviar o mesmo id não duplica.
 */
export async function criarTransferencia(transferencia: NovaTransferencia): Promise<string | null> {
  try {
    const { data, error } = await api.POST("/api/transferencias", { body: transferencia });
    if (data) return null;
    return typeof error?.detail === "string" ? error.detail : "o servidor recusou a transferência";
  } catch {
    return "sem resposta do servidor";
  }
}

export async function contarNaoEnviados(): Promise<number> {
  return (await lerFila()).length;
}

export const apagarDadosDoAparelho = apagarTudo;

/** A fila sobe ao abrir o app, ao voltar para ele e quando a rede volta. */
export function iniciarEnvioAutomatico(): () => void {
  const enviar = () => void enviarAgora();
  const aoVoltar = () => document.visibilityState === "visible" && enviar();
  enviar();
  window.addEventListener("online", enviar);
  document.addEventListener("visibilitychange", aoVoltar);
  return () => {
    window.removeEventListener("online", enviar);
    document.removeEventListener("visibilitychange", aoVoltar);
  };
}
