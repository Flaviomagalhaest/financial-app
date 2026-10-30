// A camada de dados do aparelho: o único ponto de leitura e escrita das telas (ADR 0011). Lê do
// servidor guardando a última resposta, escreve pela fila e a sobe sozinha quando dá.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  type NovaRecorrencia,
  type NovoLancamento,
} from "./armazem";
import {
  decidirConflito,
  descartar,
  enfileirarExcluir,
  enfileirarRecorrencia,
  enfileirarSalvar,
  enviarFila,
  ETIQUETA_DO_ENVIO,
  excluirMesmoAssim,
  guardarConflito,
  lancarDeNovo,
  LISTA,
  type Remessa,
} from "./fila";
import { fetchComTempoLimite, ouvirFalhaDeRede, redeVoltou, ultimaChamadaFalhou } from "./rede";
import { fonteDoHistorico, sugestaoDe, type FonteDeSugestao } from "./sugestao";

export type Conta = components["schemas"]["Conta"];
export type Categoria = components["schemas"]["Categoria"];
export type Pessoa = components["schemas"]["Pessoa"];
export type Cartao = components["schemas"]["Cartao"];
export type Fatura = components["schemas"]["Fatura"];
export type LeituraDoMes = components["schemas"]["LeituraDoMes"];
export type ItemDoModelo = components["schemas"]["ItemDoModelo"];
export type LeituraDaHoje = components["schemas"]["Hoje"];
export type LimiteDoCartao = components["schemas"]["LimiteDoCartao"];
export type { Campo } from "./fila";
export type { ContextoDaSugestao, FonteDeSugestao, Sugestao } from "./sugestao";
export type { Conflito, Exclusao, ItemDaFila, Lancamento, NovaRecorrencia, NovoLancamento };
export { comoNovo } from "./fila";

/** Lançamento como o aparelho o mostra: o do servidor com as mudanças da fila por cima. */
export type LancamentoNaTela = NovoLancamento & {
  situacao: "previsto" | "realizado";
  /** O do servidor; o não enviado repete o da versão que o servidor tem. */
  atrasado?: boolean;
  /** O mês em que o lançamento conta (o da fatura, no cartão); o criado só no aparelho ainda não tem. */
  mes?: string;
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
  "/api/sugestoes": () => api.GET("/api/sugestoes"),
};
type Caminho = keyof typeof LEITURAS;
type Dados<C extends Caminho> = NonNullable<Awaited<ReturnType<(typeof LEITURAS)[C]>>["data"]>;

/** Busca no servidor e guarda a resposta; `undefined` quando ele não respondeu. */
function buscarEGuardar<D>(caminho: string, ler: () => Promise<{ data?: D }>) {
  return comTrava("shared", async () => {
    const { data } = await ler().catch(() => ({ data: undefined }));
    if (data) await guardarResposta(caminho, data);
    return data;
  });
}

/** A resposta do servidor, ou a última guardada; `aoVivo` diz se a última busca deu certo. */
function useResposta<C extends Caminho>(caminho: C) {
  return useRespostaDe<Dados<C>>(caminho, LEITURAS[caminho] as () => Promise<{ data?: Dados<C> }>);
}

/** As faturas de um cartão, da mais antiga à mais nova; as do adicional são as do titular. */
export function useFaturas(cartaoId: string) {
  const ler = () => api.GET("/api/cartoes/{id}/faturas", { params: { path: { id: cartaoId } } });
  return useRespostaDe<Fatura[]>(`/api/cartoes/${cartaoId}/faturas`, ler);
}

/** A aba Mês de um mês (`AAAA-MM`), numa leitura só, guardada para mostrar sem internet. */
export function useMes(mes: string) {
  const ler = () => api.GET("/api/meses/{mes}", { params: { path: { mes } } });
  return useRespostaDe<LeituraDoMes>(`/api/meses/${mes}`, ler);
}

/** O modelo padrão do planejamento, que "Aplicar modelo padrão" copia para um mês vazio. */
export function useModeloPadrao() {
  return useRespostaDe<{ itens: ItemDoModelo[] }>("/api/planejamento/modelo", () => api.GET("/api/planejamento/modelo"));
}

/** A leitura da tela Hoje, em uma chamada; sem internet, a última guardada. */
export function useHoje() {
  return useRespostaDe<LeituraDaHoje>("/api/hoje", () => api.GET("/api/hoje"));
}

/** O limite comprometido e disponível do cartão titular (o adicional divide o dele). */
export function useLimite(cartaoId: string) {
  const ler = () => api.GET("/api/cartoes/{id}/limite", { params: { path: { id: cartaoId } } });
  return useRespostaDe<LimiteDoCartao>(`/api/cartoes/${cartaoId}/limite`, ler);
}

function useRespostaDe<D>(caminho: string, ler: () => Promise<{ data?: D }>) {
  const [guardada, setGuardada] = useState<Guardada<D> | null>(null);
  const [aoVivo, setAoVivo] = useState<boolean | null>(null);
  const leitor = useRef(ler);
  leitor.current = ler;

  const buscar = useCallback(async () => {
    setAoVivo(!!(await buscarEGuardar(caminho, leitor.current)));
  }, [caminho]);

  useEffect(() => {
    let ativo = true;
    const lerGuardada = () =>
      void lerResposta<D>(caminho).then((g) => {
        if (ativo && g) setGuardada(g);
      });
    lerGuardada();
    void buscar();
    const parar = ouvirMudancas(lerGuardada);
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
    // Os previstos da recorrência são do servidor: até ela subir, o aparelho só mostra a regra.
    if (item.acao === "criar_recorrencia") continue;
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

/** A recorrência na fila, com o motivo da recusa quando o servidor não a aceitou. */
export type RecorrenciaNaoEnviada = NovaRecorrencia & { recusa?: string };

/** As recorrências criadas no aparelho que ainda não subiram, da mais antiga à mais nova. */
export function useRecorrenciasNaoEnviadas(): RecorrenciaNaoEnviada[] {
  const fila = useFila();
  return useMemo(() => fila.flatMap((item) => (item.recorrencia ? [{ ...item.recorrencia, recusa: item.recusa }] : [])), [fila]);
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

/**
 * A sugestão pela descrição, sem internet: o índice do servidor com os lançamentos do aparelho que
 * ele ainda não tem por cima (os não enviados e os que mudaram no servidor depois de ele ser
 * montado), para o que se acabou de lançar ou corrigir já ser a sugestão mais recente. Sem índice
 * guardado, a lista inteira. Do enviado, o aparelho só sabe quando mudou, não o quê: mudar só o
 * valor dele também o põe primeiro, até o índice ser buscado de novo.
 */
export function useSugestao(): FonteDeSugestao {
  const { dados: indice } = useResposta("/api/sugestoes");
  const { lancamentos } = useLancamentos();
  return useMemo(() => {
    const desde = indice ? Date.parse(indice.gerado_em) : 0;
    const depois = (lancamentos ?? []).flatMap((l) => {
      if (l.conflito || l.exclusao) return [];
      const em = l.naoEnviado ? l.feitoEm : l.alterado_em ? Date.parse(l.alterado_em) : undefined;
      const sugestao = em && (l.naoEnviado || em > desde) ? sugestaoDe(l, em) : null;
      return sugestao ? [sugestao] : [];
    });
    return fonteDoHistorico([...depois, ...(indice?.sugestoes ?? [])]);
  }, [indice, lancamentos]);
}

/** Todas as contas, arquivadas inclusive, para a tela que as configura. */
export function useContasComArquivadas() {
  const { dados, atualizadoEm, buscar } = useResposta("/api/contas?arquivadas=true");
  return { contas: dados ?? [], atualizadoEm, recarregar: buscar };
}

/** Todas as tags, arquivadas inclusive, com o id, para a tela que as configura. */
export function useTagsComArquivadas() {
  const { dados, atualizadoEm, buscar } = useResposta("/api/tags");
  return { tags: dados ?? [], atualizadoEm, recarregar: buscar };
}

/** Se há rede: o navegador diz que sim e a última chamada ao servidor não falhou nem demorou. */
export function useConexao(): boolean {
  const [online, setOnline] = useState(navigator.onLine);
  const [semResposta, setSemResposta] = useState(ultimaChamadaFalhou);
  useEffect(() => {
    const mudou = () => setOnline(navigator.onLine);
    const voltou = () => {
      mudou();
      redeVoltou();
    };
    window.addEventListener("online", voltou);
    window.addEventListener("offline", mudou);
    const parar = ouvirFalhaDeRede(() => setSemResposta(ultimaChamadaFalhou()));
    return () => {
      window.removeEventListener("online", voltou);
      window.removeEventListener("offline", mudou);
      parar();
    };
  }, []);
  // O navegador não avisa que um Wi-Fi sem saída voltou: enquanto a última chamada falhou, tenta de novo.
  useEffect(() => {
    if (!semResposta) return;
    const tentar = setInterval(() => void fetchComTempoLimite("/api/saude").catch(() => undefined), 10_000);
    return () => clearInterval(tentar);
  }, [semResposta]);
  return online && !semResposta;
}

/** Uma recorrência subiu: os previstos que o servidor gerou só vêm na leitura dos lançamentos. */
let previstosNovos = false;

const remeter: Remessa = async (acoes) => {
  try {
    const { data, response } = await api.POST("/api/lancamentos/lote", { body: { acoes } });
    if (data?.resultados.some((r) => r.recorrencia)) previstosNovos = true;
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
  if (previstosNovos) {
    previstosNovos = false;
    await buscarEGuardar(LISTA, LEITURAS[LISTA]);
  }
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

/**
 * Em qual item do planejamento o lançamento "a escolher" conta. É uma mudança do lançamento, então
 * vai pela fila e vale sem internet; devolve `false` quando ela não subiu agora.
 */
export async function escolherItem(mostrado: LancamentoNaTela, categoriaId: string): Promise<boolean> {
  const { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags, pessoa, fatura_mes } = mostrado;
  const lancamento = { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags, pessoa, fatura_mes, item_categoria_id: categoriaId };
  await enfileirarSalvar(lancamento, false, baseDe(mostrado));
  return enviarAgora();
}

/** A recorrência nova vai pela fila e vale sem internet, como um pedido só (ADR 0011). */
export async function salvarRecorrencia(recorrencia: NovaRecorrencia): Promise<void> {
  await enfileirarRecorrencia(recorrencia);
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
export function criarTransferencia(transferencia: NovaTransferencia): Promise<string | null> {
  return recusaDe(() => api.POST("/api/transferencias", { body: transferencia }), "o servidor recusou a transferência");
}

/** O motivo da recusa do servidor, ou `null` quando ele aceitou. */
async function recusaDe(pedir: () => Promise<{ data?: unknown; error?: unknown }>, padrao: string): Promise<string | null> {
  try {
    const { data, error } = await pedir();
    if (data) return null;
    const detalhe = (error as { detail?: unknown } | undefined)?.detail;
    return typeof detalhe === "string" ? detalhe : padrao;
  } catch {
    return "sem resposta do servidor";
  }
}

/** O planejamento precisa de internet (ADR 0011). Copia os itens de `de` para `mes`, que precisa estar vazio. */
export function copiarPlanejamento(mes: string, de: string): Promise<string | null> {
  return recusaDe(() => api.POST("/api/planejamento/{mes}/copiar", { params: { path: { mes } }, body: { de } }), "o servidor recusou a cópia");
}

export function aplicarModeloPadrao(mes: string): Promise<string | null> {
  return recusaDe(() => api.POST("/api/planejamento/{mes}/aplicar-modelo", { params: { path: { mes } } }), "o servidor recusou o modelo padrão");
}

/** Troca o modelo padrão inteiro pelos itens enviados. */
export function definirModeloPadrao(itens: ItemDoModelo[]): Promise<string | null> {
  return recusaDe(() => api.PUT("/api/planejamento/modelo", { body: { itens } }), "o servidor recusou o modelo padrão");
}

export async function contarNaoEnviados(): Promise<number> {
  return (await lerFila()).length;
}

export const apagarDadosDoAparelho = apagarTudo;

/**
 * A fila sobe ao abrir o app, ao voltar para ele e quando a rede volta; o índice de sugestão vem
 * logo depois, para o aparelho tê-lo sem internet mesmo sem ter aberto o novo lançamento.
 */
export function iniciarEnvioAutomatico(): () => void {
  const enviar = () => void enviarAgora().then(() => buscarEGuardar("/api/sugestoes", LEITURAS["/api/sugestoes"]));
  const aoVoltar = () => document.visibilityState === "visible" && enviar();
  enviar();
  window.addEventListener("online", enviar);
  document.addEventListener("visibilitychange", aoVoltar);
  return () => {
    window.removeEventListener("online", enviar);
    document.removeEventListener("visibilitychange", aoVoltar);
  };
}
