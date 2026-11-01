// A sugestão pela descrição (tickets 22 e 63), que roda no aparelho, sem internet. O contrato é o
// de uma fonte de sugestão: entra a descrição (e o contexto do lançamento) e sai uma lista de
// sugestões, cada uma com a sua origem. A v1 só tem a fonte "histórico", feita do índice que o
// servidor monta (`app/sugestao.py`) com os lançamentos que o aparelho mudou depois por cima.
import type { components } from "../api/schema";
import { config } from "../config";
import type { NovoLancamento } from "./armazem";
import { chaveDaDescricao, identidadeDaParte } from "./identidade";

/** Categorias, tags, conta e pessoa de um lançamento anterior; escolher preenche esses campos. */
export type Sugestao = components["schemas"]["Sugestao"];

/** O que a tela sabe do lançamento além da descrição; a fonte do histórico não usa. */
export type ContextoDaSugestao = Partial<Pick<NovoLancamento, "tipo" | "valor_centavos" | "conta_id" | "data">>;

export type FonteDeSugestao = (descricao: string, contexto?: ContextoDaSugestao) => Sugestao[];

export { chaveDaDescricao };

/**
 * A sugestão de um lançamento que o aparelho mudou depois do índice; `em` é a hora da mudança (ms).
 * Sem descrição ou sem categoria, nenhuma, como no servidor.
 */
export function sugestaoDe(lancamento: NovoLancamento, em: number): Sugestao | null {
  const partes = (lancamento.partes ?? []).map(({ descricao, valor_centavos, categoria_ids, tags, pessoa }) => ({ descricao, valor_centavos, categoria_ids, tags: tags ?? [], pessoa: pessoa ?? null }));
  if (!lancamento.descricao?.trim() || (lancamento.categoria_ids.length === 0 && partes.length === 0)) return null;
  return {
    chave: chaveDaDescricao(lancamento.descricao),
    descricao: lancamento.descricao,
    tipo: lancamento.tipo,
    conta_id: lancamento.conta_id,
    categoria_ids: [...lancamento.categoria_ids].sort(),
    tags: lancamento.tags ?? [],
    pessoa: lancamento.pessoa ?? null,
    partes,
    em: new Date(em).toISOString(),
    origem: "historico",
  };
}

/** A mesma sugestão vinda de dois lançamentos aparece uma vez só. */
const identidade = (s: Sugestao) => {
  const total = s.partes.reduce((soma, p) => soma + p.valor_centavos, 0);
  return [
    s.tipo,
    s.conta_id,
    [...s.categoria_ids].sort().join(),
    s.tags.map((t) => t.toLowerCase()).sort().join("\u0000"),
    s.pessoa ?? "",
    JSON.stringify(s.partes.map((p) => identidadeDaParte(p, total))),
  ].join("|");
};

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
 * cada um, da sugestão mais recente à mais antiga, sem repetir, a partir de 2 letras e até 3.
 */
export function fonteDoHistorico(sugestoes: Sugestao[]): FonteDeSugestao {
  return (descricao) => {
    const digitado = chaveDaDescricao(descricao);
    if (digitado.length < config.sugestao.letrasMinimas) return [];
    const casados = sugestoes
      .map((sugestao) => ({ sugestao, nivel: casamento(sugestao.chave, digitado) }))
      .filter((c): c is { sugestao: Sugestao; nivel: number } => c.nivel !== null)
      .sort((a, b) => a.nivel - b.nivel || Date.parse(b.sugestao.em) - Date.parse(a.sugestao.em));
    const vistas = new Set<string>();
    const escolhidas: Sugestao[] = [];
    for (const { sugestao } of casados) {
      if (escolhidas.length === config.sugestao.maximoDeSugestoes) break;
      if (vistas.has(identidade(sugestao))) continue;
      vistas.add(identidade(sugestao));
      escolhidas.push(sugestao);
    }
    return escolhidas;
  };
}
