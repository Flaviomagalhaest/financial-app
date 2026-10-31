// A camada de dados do aparelho: o único ponto de leitura e escrita das telas (ADR 0011). Lê do
// servidor guardando a última resposta, escreve pela fila e a sobe sozinha quando dá.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { hoje, mesDepois } from "../lancamentos/datas";
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
  enfileirarConfirmar,
  enfileirarExcluir,
  enfileirarRecorrencia,
  enfileirarSalvar,
  enviarFila,
  ETIQUETA_DO_ENVIO,
  excluirMesmoAssim,
  lancarDeNovo,
  LISTA,
  naSemana,
  pelaData,
  type Ajustes,
  type Remessa,
} from "./fila";
import { saldoNoAparelho } from "./saldo";
import {
  avisoDePlanejamento,
  categoriasComItem,
  comAFila,
  fechamentoDaFatura,
  mesEmQueConta,
  ultimaEscolha,
  type Aviso,
  type CartaoDaCompra,
  type Contagem,
  type Mudanca,
  type Planejamento,
} from "./aviso";
import { fetchComTempoLimite, ouvirFalhaDeRede, redeVoltou, ultimaChamadaFalhou } from "./rede";
import { comValorPadrao, type DadosDoFavorito, type Favorito, type NovoFavorito, type Sugerido } from "./favoritos";
import { fonteDoHistorico, sugestaoDe, type FonteDeSugestao } from "./sugestao";
import { buscarNoAparelho, pedidoDaBusca, type Criterios, type LinhaNaTela, type ResultadoNaTela } from "./busca";

export type Conta = components["schemas"]["Conta"];
export type Categoria = components["schemas"]["Categoria"];
export type Pessoa = components["schemas"]["Pessoa"];
export type Cartao = components["schemas"]["Cartao"];
export type Fatura = components["schemas"]["Fatura"];
export type LeituraDoMes = components["schemas"]["LeituraDoMes"];
export type ItemDoModelo = components["schemas"]["ItemDoModelo"];
export type LeituraDaHoje = components["schemas"]["Hoje"];
export type LimiteDoCartao = components["schemas"]["LimiteDoCartao"];
export type Futuro = components["schemas"]["Futuro"];
export type Historico = components["schemas"]["Historico"];
export type { Aviso } from "./aviso";
export type { Ajustes, Campo } from "./fila";
export type { ContextoDaSugestao, FonteDeSugestao, Sugestao } from "./sugestao";
export type { Conflito, Exclusao, ItemDaFila, Lancamento, NovaRecorrencia, NovoLancamento };
export { identidadeDe, oferecerFavoritar, useOfertaDeFavoritar } from "./favoritos";
export { criteriosDoEndereco, enderecoDaBusca } from "./busca";
export type { Criterios, ParcelamentoNaTela, Transferencia } from "./busca";
export type { DadosDoFavorito, Favorito, Oferta, Sugerido } from "./favoritos";

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
  /** O parcelamento da parcela, o número dela e o total de parcelas (3 de 10). */
  parcelamento_id?: Lancamento["parcelamento_id"];
  parcela?: Lancamento["parcela"];
  parcelas?: Lancamento["parcelas"];
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

const SEM_CONTAS: Conta[] = [];

const LEITURAS = {
  "/api/lancamentos": () => api.GET("/api/lancamentos"),
  "/api/contas": () => api.GET("/api/contas"),
  "/api/contas?arquivadas=true": () => api.GET("/api/contas", { params: { query: { arquivadas: true } } }),
  "/api/categorias": () => api.GET("/api/categorias"),
  "/api/pessoas": () => api.GET("/api/pessoas"),
  "/api/tags": () => api.GET("/api/tags"),
  "/api/cartoes": () => api.GET("/api/cartoes"),
  "/api/cartoes?arquivados=true": () => api.GET("/api/cartoes", { params: { query: { arquivados: true } } }),
  "/api/sugestoes": () => api.GET("/api/sugestoes"),
  "/api/favoritos": () => api.GET("/api/favoritos"),
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
  return useRespostaDe<Fatura[]>(caminhoDasFaturas(cartaoId), faturasDe(cartaoId));
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

/** A projeção de saldo da aba Futuro: o realizado no passado e as duas linhas adiante. */
export function useFuturo() {
  return useRespostaDe<Futuro>("/api/futuro", () => api.GET("/api/futuro"));
}

/** A evolução de uma métrica na aba Histórico (uma leitura por métrica e mês), guardada para mostrar sem internet. */
export function useHistorico(metrica: Historico["metrica"], categoriaId: string | undefined, mesDoAno: number) {
  const query = { metrica, categoria_id: categoriaId, mes_do_ano: mesDoAno };
  const caminho = `/api/historico?metrica=${metrica}&categoria_id=${categoriaId ?? ""}&mes_do_ano=${mesDoAno}`;
  return useRespostaDe<Historico>(caminho, () => api.GET("/api/historico", { params: { query } }));
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

/** A resposta que o aparelho já guardou, sem ir ao servidor: quem só precisa dela não pede leitura a mais. */
function useRespostaGuardada<D>(caminho: string): D | null {
  const [guardada, setGuardada] = useState<D | null>(null);
  useEffect(() => {
    let ativo = true;
    const ler = () =>
      void lerResposta<D>(caminho).then((g) => {
        if (ativo && g) setGuardada(g.dados);
      });
    ler();
    const parar = ouvirMudancas(ler);
    return () => {
      ativo = false;
      parar();
    };
  }, [caminho]);
  return guardada;
}

/** "atualizado às 14:32", para a resposta guardada que a tela mostra sem internet. */
export function atualizadoAs(em: number): string {
  return `atualizado às ${new Date(em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
}

/** A fila do aparelho, atualizada a cada mudança; `lida` só depois da primeira leitura. */
function useFilaLida() {
  const [estado, setEstado] = useState<{ itens: ItemDaFila[]; lida: boolean }>({ itens: [], lida: false });
  useEffect(() => {
    let ativo = true;
    const ler = () => void lerFila().then((lidos) => ativo && setEstado({ itens: lidos, lida: true }));
    ler();
    const parar = ouvirMudancas(ler);
    return () => {
      ativo = false;
      parar();
    };
  }, []);
  return estado;
}

export function useFila(): ItemDaFila[] {
  return useFilaLida().itens;
}


/** A mesma regra do servidor: sem situação, data futura é prevista; só mudar a data refaz. */
function situacaoNoAparelho(lancamento: NovoLancamento, anterior?: Pick<LancamentoNaTela, "data" | "situacao">) {
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
  const { itens: fila, lida } = useFilaLida();
  const lancamentos = useMemo(() => (dados ? naTela(dados, fila) : semDados ? naTela([], fila) : null), [dados, fila, semDados]);
  return { lancamentos, atualizadoEm, semDados, filaLida: lida };
}

export type LinhaDaBusca = LinhaNaTela<LancamentoNaTela>;

const naTelaDoServidor = (l: Lancamento): LancamentoNaTela => ({ ...l, naoEnviado: false });

function linhaDoServidor(linha: components["schemas"]["LinhaDaBusca"]): LinhaDaBusca {
  if (linha.parcelamento) return { parcelamento: { ...linha.parcelamento, lancamentos: linha.parcelamento.lancamentos.map(naTelaDoServidor) } };
  if (linha.transferencia) return { transferencia: linha.transferencia };
  return { lancamento: naTelaDoServidor(linha.lancamento!) };
}

/**
 * A busca no servidor, página a página; sem resposta dele, a do aparelho sobre o que ele guarda,
 * com `parcial`. Os totais são sempre do resultado inteiro.
 */
export function useBusca(criterios: Criterios) {
  const chave = JSON.stringify(criterios);
  const [doServidor, setDoServidor] = useState<{ chave: string; resultado: ResultadoNaTela<LancamentoNaTela>; paginas: number; temMais: boolean } | null>(null);
  const [parcial, setParcial] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const pedido = useRef(0);
  const { lancamentos } = useLancamentos();
  const { cartoes } = useCadastro();

  const pedir = useCallback(
    async (pagina: number) => {
      const numero = ++pedido.current;
      setCarregando(true);
      const { data } = await api.POST("/api/busca", { body: pedidoDaBusca(JSON.parse(chave) as Criterios, pagina) }).catch(() => ({ data: undefined }));
      // Uma busca mais nova já saiu: esta resposta não vale mais.
      if (numero !== pedido.current) return;
      setCarregando(false);
      if (!data) return setParcial(true);
      setParcial(false);
      setDoServidor((antes) => {
        const linhas = data.linhas.map(linhaDoServidor);
        const anteriores = pagina > 0 && antes?.chave === chave ? antes.resultado.linhas : [];
        return { chave, resultado: { totais: data.totais, linhas: [...anteriores, ...linhas] }, paginas: pagina + 1, temMais: data.tem_mais };
      });
    },
    [chave],
  );

  useEffect(() => {
    void pedir(0);
    // A rede voltou: a busca completa substitui o resultado parcial.
    const deNovo = () => void pedir(0);
    window.addEventListener("online", deNovo);
    return () => window.removeEventListener("online", deNovo);
  }, [pedir]);

  // A fila subiu (ou mudou): o que estava só no aparelho já está no servidor.
  const naoEnviados = useFila().length;
  const antes = useRef(naoEnviados);
  useEffect(() => {
    if (antes.current === naoEnviados) return;
    antes.current = naoEnviados;
    void pedir(0);
  }, [naoEnviados, pedir]);

  const noAparelho = useMemo(() => (parcial && lancamentos ? buscarNoAparelho(lancamentos, JSON.parse(chave) as Criterios, cartoes) : null), [parcial, lancamentos, chave, cartoes]);
  const atual = doServidor?.chave === chave ? doServidor : null;
  return {
    resultado: noAparelho ?? atual?.resultado ?? null,
    /** Sem internet: só o que o aparelho guarda. */
    parcial: !!noAparelho,
    carregando,
    temMais: !noAparelho && !!atual?.temMais,
    carregarMais: () => atual && void pedir(atual.paginas),
  };
}

/**
 * A recorrência na fila, com o motivo da recusa quando o servidor não a aceitou. `podeDescartar`
 * só quando ela com certeza não está no servidor: nunca saiu do aparelho ou foi recusada.
 */
export type RecorrenciaNaoEnviada = NovaRecorrencia & { recusa?: string; podeDescartar: boolean };

/** As recorrências criadas no aparelho que ainda não subiram, da mais antiga à mais nova. */
export function useRecorrenciasNaoEnviadas(): RecorrenciaNaoEnviada[] {
  const fila = useFila();
  return useMemo(
    () =>
      fila.flatMap((item) =>
        item.recorrencia ? [{ ...item.recorrencia, recusa: item.recusa, podeDescartar: !!item.recusa || item.talvezNoServidor === undefined }] : [],
      ),
    [fila],
  );
}

/**
 * As contas da semana da leitura da Hoje com a fila por cima: o previsto criado ou mudado no
 * aparelho entra ou sai pela mesma janela do servidor, e o confirmado sai. O conflito e a recusa de
 * uma conta da semana ficam, para decidir ou confirmar de novo.
 */
export function useContasDaSemana(doServidor: Lancamento[] | null): LancamentoNaTela[] | null {
  const fila = useFila();
  return useMemo(() => {
    if (!doServidor) return null;
    const ids = new Set(doServidor.map((l) => l.id));
    const esperam = (l: LancamentoNaTela) => ids.has(l.id) && !!(l.conflito || l.recusa);
    return naTela(doServidor, fila)
      .filter((l) => esperam(l) || naSemana(l))
      .sort(pelaData);
  }, [doServidor, fila]);
}

/** A conta com o saldo que o aparelho mostra: o do servidor mais os não enviados (ticket 81). */
export type ContaNaTela = Conta & { saldoNaoEnviado: boolean };

/** As contas com o saldo do aparelho; toda tela que mostra saldo passa por aqui. */
function useComSaldoDoAparelho(contas: Conta[]): ContaNaTela[] {
  // Só lê a lista guardada: a leitura do servidor é das telas de lançamentos, e outra aqui mexeria no que elas mostram.
  const dados = useRespostaGuardada<Lancamento[]>(LISTA);
  const fila = useFila();
  return useMemo(() => {
    const doServidor = new Map((dados ?? []).map((l) => [l.id, l]));
    const naTelaPorId = new Map(naTela(dados ?? [], fila).map((l) => [l.id, l]));
    return contas.map((conta) => {
      const { centavos, naoEnviado } = saldoNoAparelho(conta, doServidor, naTelaPorId, fila);
      return { ...conta, saldo_centavos: centavos, saldoNaoEnviado: naoEnviado };
    });
  }, [contas, dados, fila]);
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
  const contasNaTela = useComSaldoDoAparelho(contas.dados ?? SEM_CONTAS);
  return {
    contas: contasNaTela,
    cartoes: cartoes.dados ?? [],
    contasECartoes: useMemo(() => [...contasNaTela, ...(cartoes.dados ?? [])], [contasNaTela, cartoes.dados]),
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

const planejamentoDe = (mes: string) => () => api.GET("/api/planejamento/{mes}", { params: { path: { mes } } });
const faturasDe = (id: string) => () => api.GET("/api/cartoes/{id}/faturas", { params: { path: { id } } });
const caminhoDasFaturas = (cartaoId: string) => `/api/cartoes/${cartaoId}/faturas`;
/** Os cartões que têm faturas: o adicional usa as do titular. */
const titulares = (cartoes: Cartao[]) => cartoes.filter((c) => !c.titular_id).map((c) => c.id);

/**
 * As faturas guardadas dos cartões titulares, buscadas de novo ao abrir: para o aparelho saber em
 * que fatura cai a compra no cartão sem internet (o fechamento que alguém acertou à mão).
 */
function useFaturasDosTitulares(cartoes: Cartao[]): Map<string, Fatura[]> {
  const chave = titulares(cartoes).sort().join();
  const [porCartao, setPorCartao] = useState(new Map<string, Fatura[]>());
  useEffect(() => {
    let ativo = true;
    const ids = chave ? chave.split(",") : [];
    const lerGuardadas = () =>
      void Promise.all(ids.map((id) => lerResposta<Fatura[]>(caminhoDasFaturas(id)))).then(
        (guardadas) => ativo && setPorCartao(new Map(ids.map((id, i) => [id, guardadas[i]?.dados ?? []]))),
      );
    lerGuardadas();
    for (const id of ids) void buscarEGuardar(caminhoDasFaturas(id), faturasDe(id));
    const parar = ouvirMudancas(lerGuardadas);
    return () => {
      ativo = false;
      parar();
    };
  }, [chave]);
  return porCartao;
}

/** Os dias e as faturas do titular, quando `contaId` é um cartão (o adicional usa os do titular). */
function cartaoDaCompra(cartoes: Cartao[], faturas: Map<string, Fatura[]>, contaId: string): CartaoDaCompra | undefined {
  const cartao = cartoes.find((c) => c.id === contaId);
  if (!cartao) return undefined;
  const titular = (cartao.titular_id && cartoes.find((c) => c.id === cartao.titular_id)) || cartao;
  return { titular, faturas: faturas.get(titular.id) ?? [] };
}

/** Um lançamento como conta no planejamento do aparelho, com a hora da última mudança (`em`). */
type NoAparelho = Contagem & { conta_id: string; data: string; parcela?: number | null; em: number };

/**
 * As mudanças da fila que o servidor ainda não tem, sobre a versão que ele tem (`servidor`), e a
 * versão que o aparelho mostra de cada lançamento. O conflito mostra a do servidor, e a exclusão que
 * venceu já saiu dela: nenhum dos dois muda nada.
 */
function contagensNoAparelho(servidor: Lancamento[], fila: ItemDaFila[], cartaoDe: (contaId: string) => CartaoDaCompra | undefined) {
  const porId = new Map<string, NoAparelho>(servidor.map((l) => [l.id, { ...l, em: Date.parse(l.alterado_em) }]));
  const mudancas: Mudanca[] = [];
  for (const item of fila) {
    if (item.conflito || item.exclusao) continue;
    const antes = porId.get(item.id);
    if (item.acao === "excluir" || !item.lancamento) {
      porId.delete(item.id);
      mudancas.push({ antes });
      continue;
    }
    const l = item.lancamento;
    const depois: NoAparelho = {
      ...l,
      // O estorno não muda de compra, nem a parcela de número: vale o que o servidor tem. Sem
      // escolha do item (a confirmação não a leva), fica a do servidor, como em `alteracao`.
      estorno_de: l.estorno_de ?? antes?.estorno_de,
      parcela: antes?.parcela,
      item_categoria_id: l.item_categoria_id || antes?.item_categoria_id,
      situacao: situacaoNoAparelho(l, antes),
      mes: mesEmQueConta(l, antes, cartaoDe(l.conta_id)),
      em: item.feitoEm ?? item.desde,
    };
    porId.set(item.id, depois);
    mudancas.push({ antes, depois });
  }
  return { mudancas, porId };
}

/** O lançamento que está na tela de lançar, como ele vai ser salvo. */
export type LancamentoEmEdicao = Pick<NovoLancamento, "id" | "valor_centavos" | "categoria_ids" | "conta_id" | "data" | "fatura_mes"> & {
  situacao: LancamentoNaTela["situacao"];
};

/**
 * O aviso de planejamento da tela de lançar, com e sem internet (ticket 52): o planejamento do mês
 * em que o lançamento conta (o do servidor ou o guardado) com a fila por cima, e o efeito do
 * lançamento nele. Com duas ou mais categorias com item, `escolha` é a escolha do item que vai ser
 * salva: a tocada na tela, a que o lançamento já tem ou, no lançamento novo, a última escolha para
 * aquele conjunto. Sem nenhuma, ele fica "a escolher" (no item em que já estava, se estava).
 */
export function useAvisoDePlanejamento(lancamento: LancamentoEmEdicao, escolhaTocada: string | null) {
  const { dados: servidor } = useResposta(LISTA);
  const { dados: cartoes } = useResposta("/api/cartoes");
  const fila = useFila();
  const faturas = useFaturasDosTitulares(cartoes ?? []);
  const cartaoDe = useCallback((contaId: string) => cartaoDaCompra(cartoes ?? [], faturas, contaId), [cartoes, faturas]);
  const { mudancas, porId } = useMemo(() => contagensNoAparelho(servidor ?? [], fila, cartaoDe), [servidor, fila, cartaoDe]);

  const antes = porId.get(lancamento.id) ?? null;
  const cartao = cartaoDe(lancamento.conta_id);
  const mes = mesEmQueConta(lancamento, antes ?? undefined, cartao);
  // Sem mês (cartão sem dia de fechamento), lê o deste mês, que o aviso não usa.
  const mesLido = (mes ?? hoje()).slice(0, 7);
  const guardado = useRespostaDe<Planejamento>(`/api/planejamento/${mesLido}`, planejamentoDe(mesLido));
  const planejamento = useMemo(() => (guardado.dados ? comAFila(guardado.dados, mudancas) : null), [guardado.dados, mudancas]);

  const comItem = planejamento ? categoriasComItem(planejamento, lancamento.categoria_ids) : [];
  const ultima = () => (antes || !planejamento ? null : ultimaEscolha(comItem, [...porId.values()], planejamento.itens.map((i) => i.categoria_id)));
  const escolha = comItem.length < 2 ? null : ([escolhaTocada, antes?.item_categoria_id, ultima()].find((c) => c && comItem.includes(c)) ?? null);

  const aviso: Aviso | null =
    planejamento && mes
      ? avisoDePlanejamento(planejamento, antes, {
          ...lancamento,
          item_categoria_id: escolha ?? antes?.item_categoria_id,
          estorno_de: antes?.estorno_de,
          mes,
        })
      : null;
  return {
    aviso,
    /** O mês em que o lançamento conta; `null` no cartão sem dia de fechamento e sem fatura escolhida. */
    mes,
    escolha,
    /** No cartão, o fechamento da fatura em que a compra cai. */
    fechamento: cartao && mes ? fechamentoDaFatura(cartao.titular, cartao.faturas, mes) : null,
    noCartao: !!cartao,
    atualizadoEm: guardado.atualizadoEm,
    semPlanejamento: guardado.semDados,
  };
}

/**
 * Os favoritos e os sugeridos, para lançar sem internet: a lista que o servidor mandou por último,
 * com o valor padrão do último lançamento que o aparelho conhece por cima.
 */
export function useFavoritos() {
  const { dados, atualizadoEm, semDados, buscar } = useResposta("/api/favoritos");
  const { lancamentos, filaLida } = useLancamentos();
  const favoritos = useMemo(() => comValorPadrao(dados?.favoritos ?? [], lancamentos ?? [], hoje()), [dados, lancamentos]);
  // `carregado` espera os lançamentos do aparelho: sem eles e sem a fila o valor padrão ainda não é o do último.
  return { favoritos, sugeridos: dados?.sugeridos ?? [], carregado: !!dados && lancamentos !== null && filaLida, atualizadoEm, semDados, recarregar: buscar };
}

/** Todas as contas, arquivadas inclusive, para a tela que as configura. */
export function useContasComArquivadas() {
  const { dados, atualizadoEm, buscar } = useResposta("/api/contas?arquivadas=true");
  const contas = useComSaldoDoAparelho(dados ?? SEM_CONTAS);
  return { contas, atualizadoEm, recarregar: buscar };
}

/** Todos os cartões, arquivados inclusive, para a tela que os configura; recarregar atualiza também a lista dos ativos. */
export function useCartoesComArquivados() {
  const todos = useResposta("/api/cartoes?arquivados=true");
  const ativos = useResposta("/api/cartoes");
  const recarregar = useCallback(async () => {
    await Promise.all([todos.buscar(), ativos.buscar()]);
  }, [todos.buscar, ativos.buscar]);
  return { cartoes: todos.dados ?? [], atualizadoEm: todos.atualizadoEm, recarregar };
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

/** Uma recorrência subiu: os previstos que o servidor gerou só vêm nas leituras dos lançamentos e da Hoje. */
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
  // O envio tira o item da fila e só atualiza a lista que já está guardada: sem ela, o lançamento
  // enviado sumiria do aparelho até a próxima leitura com internet (ticket 90).
  const pendentes = (await lerFila()).length;
  if (pendentes > 0 && !(await lerResposta(LISTA))) await buscarEGuardar(LISTA, LEITURAS[LISTA]);
  const enviou = await enviarFila(remeter);
  if (!enviou) pedirEnvioEmSegundoPlano();
  // O saldo guardado das contas não conta o que acabou de subir: sem a fila para cobrir a diferença, buscá-lo de novo (ticket 81).
  else if (pendentes > 0) void Promise.all((["/api/contas", "/api/contas?arquivadas=true"] as const).map((c) => buscarEGuardar(c, LEITURAS[c])));
  if (previstosNovos) {
    previstosNovos = false;
    await Promise.all([buscarEGuardar(LISTA, LEITURAS[LISTA]), buscarEGuardar("/api/hoje", () => api.GET("/api/hoje"))]);
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

/**
 * Confirma o previsto pela fila (ADR 0011) e já tenta subir. Devolve a mudança se ela ainda está na
 * fila: sem internet, recusada, em conflito ou vencida pela exclusão.
 */
export async function confirmarPrevisto(mostrado: LancamentoNaTela, ajustes: Ajustes = {}): Promise<ItemDaFila | undefined> {
  await enfileirarConfirmar(mostrado, ajustes, baseDe(mostrado));
  await enviarAgora();
  return (await lerFila()).find((item) => item.id === mostrado.id);
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

/** Favoritos mudam só com internet (ADR 0011): devolvem o motivo da recusa, ou `null` quando o servidor aceitou. */
async function mudarFavoritos(pedir: () => Promise<{ data?: unknown; error?: unknown; response: Response }>, padrao: string): Promise<string | null> {
  const motivo = await recusaDe(pedir, padrao);
  if (motivo === null) await buscarEGuardar("/api/favoritos", LEITURAS["/api/favoritos"]);
  return motivo;
}

/** Marca como favorito (a ⭐, o "Favoritar" depois de salvar ou a promoção de um sugerido). */
export function favoritar(dados: DadosDoFavorito & { id?: string }): Promise<string | null> {
  const novo: NovoFavorito = { ...dados, id: dados.id ?? crypto.randomUUID() };
  return mudarFavoritos(() => api.POST("/api/favoritos", { body: novo }), "o servidor recusou o favorito");
}

export function promoverSugerido({ chave: _chave, usos: _usos, ...dados }: Sugerido): Promise<string | null> {
  return favoritar(dados);
}

export function removerFavorito(id: string): Promise<string | null> {
  return mudarFavoritos(() => api.DELETE("/api/favoritos/{id}", { params: { path: { id } } }), "o servidor recusou remover o favorito");
}

export function reordenarFavoritos(ids: string[]): Promise<string | null> {
  return mudarFavoritos(() => api.PUT("/api/favoritos/ordem", { body: { ids } }), "o servidor recusou a nova ordem");
}

export function dispensarSugerido(chave: string): Promise<string | null> {
  return mudarFavoritos(() => api.POST("/api/favoritos/sugeridos/dispensar", { body: { chave } }), "o servidor recusou dispensar o sugerido");
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
 * A fila sobe ao abrir o app, ao voltar para ele e quando a rede volta; o índice de sugestão, os
 * favoritos, o planejamento e as faturas vêm logo depois, para o aparelho tê-los sem internet mesmo
 * sem ter aberto o novo lançamento.
 */
export function iniciarEnvioAutomatico(): () => void {
  // Os favoritos também vêm antes de a rede cair: a fileira do novo lançamento funciona sem internet.
  const enviar = () =>
    void enviarAgora().then(() =>
      Promise.all([
        buscarEGuardar("/api/sugestoes", LEITURAS["/api/sugestoes"]),
        buscarEGuardar("/api/favoritos", LEITURAS["/api/favoritos"]),
        // Para o aviso de planejamento sem internet: o planejamento do mês anterior ao próximo (a
        // compra no cartão conta no mês da fatura) e as faturas dos cartões.
        ...[-1, 0, 1].map((n) => {
          const mes = mesDepois(hoje(), n).slice(0, 7);
          return buscarEGuardar(`/api/planejamento/${mes}`, planejamentoDe(mes));
        }),
        buscarEGuardar("/api/cartoes", LEITURAS["/api/cartoes"]).then((cartoes) =>
          Promise.all(titulares(cartoes ?? []).map((id) => buscarEGuardar(caminhoDasFaturas(id), faturasDe(id)))),
        ),
      ]),
    );
  const aoVoltar = () => document.visibilityState === "visible" && enviar();
  enviar();
  window.addEventListener("online", enviar);
  document.addEventListener("visibilitychange", aoVoltar);
  return () => {
    window.removeEventListener("online", enviar);
    document.removeEventListener("visibilitychange", aoVoltar);
  };
}
