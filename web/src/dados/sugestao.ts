// A sugestão pela descrição (ticket 22), que roda no aparelho, sem internet. O contrato é o de
// uma fonte de sugestão: entra a descrição (e o contexto do lançamento) e sai uma lista de pacotes,
// cada um com a sua origem. A v1 só tem a fonte "histórico", feita do índice que o servidor monta
// (`app/sugestao.py`) com os lançamentos que o aparelho mudou depois por cima.
import type { components } from "../api/schema";
import { config } from "../config";
import type { NovoLancamento } from "./armazem";

/** Categorias, tags, conta e pessoa de um lançamento anterior; escolher preenche esses campos. */
export type Sugestao = components["schemas"]["Pacote"];

/** O que a tela sabe do lançamento além da descrição; a fonte do histórico não usa. */
export type ContextoDaSugestao = Partial<Pick<NovoLancamento, "tipo" | "valor_centavos" | "conta_id" | "data">>;

export type FonteDeSugestao = (descricao: string, contexto?: ContextoDaSugestao) => Sugestao[];

const PARCELA = /\(\s*\d+\s*\/\s*\d+\s*\)/g;

/** Como o servidor compara (`chave` em `app/sugestao.py`): sem acento, sem maiúscula, sem `(n/total)`. */
export function chaveDaDescricao(descricao: string): string {
  return descricao
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(PARCELA, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

/** O pacote de um lançamento que o aparelho mudou depois do índice; `em` é a hora da mudança (ms). */
export function pacoteDe(lancamento: NovoLancamento, em: number): Sugestao {
  return {
    chave: chaveDaDescricao(lancamento.descricao ?? ""),
    descricao: lancamento.descricao ?? "",
    tipo: lancamento.tipo,
    conta_id: lancamento.conta_id,
    categoria_ids: [...lancamento.categoria_ids].sort(),
    tags: lancamento.tags ?? [],
    pessoa: lancamento.pessoa ?? null,
    em: new Date(em).toISOString(),
    origem: "historico",
  };
}

const igual = (s: Sugestao) =>
  [s.tipo, s.conta_id, [...s.categoria_ids].sort().join(), s.tags.map((t) => t.toLowerCase()).sort().join("\u0000"), s.pessoa ?? ""].join("|");

const letraOuNumero = /[\p{L}\p{N}]/u;

/** 0 para a descrição igual, 1 para a que começa com o digitado, 2 para a palavra que começa com ele. */
function casamento(chave: string, digitado: string): number | null {
  if (chave === digitado) return 0;
  if (chave.startsWith(digitado)) return 1;
  for (let i = chave.indexOf(digitado, 1); i > 0; i = chave.indexOf(digitado, i + 1)) {
    if (!letraOuNumero.test(chave[i - 1])) return 2;
  }
  return null;
}

/**
 * A fonte do histórico: igual, depois "começa com", depois palavra que começa com o digitado; em
 * cada um, do pacote mais recente ao mais antigo, sem repetir pacote, a partir de 2 letras e até 3.
 */
export function fonteDoHistorico(pacotes: Sugestao[]): FonteDeSugestao {
  return (descricao) => {
    const digitado = chaveDaDescricao(descricao);
    if (digitado.length < config.sugestao.letrasMinimas) return [];
    const casados = pacotes
      .map((pacote) => ({ pacote, nivel: casamento(pacote.chave, digitado) }))
      .filter((c): c is { pacote: Sugestao; nivel: number } => c.nivel !== null)
      .sort((a, b) => a.nivel - b.nivel || Date.parse(b.pacote.em) - Date.parse(a.pacote.em));
    const vistos = new Set<string>();
    const sugestoes: Sugestao[] = [];
    for (const { pacote } of casados) {
      if (sugestoes.length === config.sugestao.maximoDeSugestoes) break;
      if (vistos.has(igual(pacote))) continue;
      vistos.add(igual(pacote));
      sugestoes.push(pacote);
    }
    return sugestoes;
  };
}
