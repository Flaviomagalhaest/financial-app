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
  type Guardada,
  type ItemDaFila,
  type Lancamento,
  type NovoLancamento,
} from "./armazem";
import { descartar, enfileirarExcluir, enfileirarSalvar, enviarFila, ETIQUETA_DO_ENVIO, LISTA, type Remessa } from "./fila";

export type Conta = components["schemas"]["Conta"];
export type Categoria = components["schemas"]["Categoria"];
export type { ItemDaFila, Lancamento, NovoLancamento };

/** Lançamento como o aparelho o mostra: o do servidor com as mudanças da fila por cima. */
export type LancamentoNaTela = NovoLancamento & {
  situacao: "previsto" | "realizado";
  /** O do servidor; o não enviado repete o da versão que o servidor tem. */
  atrasado?: boolean;
  naoEnviado: boolean;
  recusa?: string;
};

const LEITURAS = {
  "/api/lancamentos": () => api.GET("/api/lancamentos"),
  "/api/contas": () => api.GET("/api/contas"),
  "/api/contas?arquivadas=true": () => api.GET("/api/contas", { params: { query: { arquivadas: true } } }),
  "/api/categorias": () => api.GET("/api/categorias"),
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
    if (item.acao === "excluir") {
      porId.delete(item.id);
      continue;
    }
    const lancamento = item.lancamento!;
    const situacao = situacaoNoAparelho(lancamento, anterior);
    // O atraso é regra do servidor: vale o dele enquanto a mudança não mexe em data nem situação.
    const atrasado = anterior?.data === lancamento.data && anterior.situacao === situacao ? anterior.atrasado : undefined;
    const mostrado = { ...lancamento, situacao, atrasado, naoEnviado: true, recusa: item.recusa };
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

/** Contas e categorias do casal; `carregado` quando há resposta do servidor, nova ou guardada. */
export function useCadastro() {
  const contas = useResposta("/api/contas");
  const categorias = useResposta("/api/categorias");
  const recarregar = useCallback(async () => {
    await Promise.all([contas.buscar(), categorias.buscar()]);
  }, [contas.buscar, categorias.buscar]);
  return {
    contas: contas.dados ?? [],
    categorias: categorias.dados ?? [],
    carregado: !!contas.dados && !!categorias.dados,
    atualizadoEm: contas.atualizadoEm ?? categorias.atualizadoEm,
    recarregar,
  };
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

export async function salvarLancamento(lancamento: NovoLancamento, novo: boolean): Promise<void> {
  await enfileirarSalvar(lancamento, novo);
  void enviarAgora();
}

export async function excluirLancamento(id: string): Promise<void> {
  await enfileirarExcluir(id);
  void enviarAgora();
}

export const descartarNaoEnviado = descartar;

/** Cadastro precisa de internet (ADR 0011): não entra na fila. `false` se o servidor recusou. */
export async function criarConta(nome: string, tipo: Conta["tipo"]): Promise<boolean> {
  return !!(await api.POST("/api/contas", { body: { nome, tipo } })).data;
}

export async function criarCategoria(nome: string, tipo: Categoria["tipo"]): Promise<boolean> {
  return !!(await api.POST("/api/categorias", { body: { nome, tipo } })).data;
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
