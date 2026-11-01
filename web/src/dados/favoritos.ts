// Favoritos (ticket 62): lançamentos-modelo para lançar com um toque. O servidor guarda a lista; o
// aparelho a guarda para lançar sem internet e põe por cima o valor do último lançamento feito
// com cada favorito, mesmo o que ainda não subiu.
import { useSyncExternalStore } from "react";
import type { components } from "../api/schema";
import { chaveDaDescricao } from "./sugestao";

export type Favorito = components["schemas"]["Favorito"];
export type Sugerido = components["schemas"]["Sugerido"];
export type NovoFavorito = components["schemas"]["NovoFavorito"];
export type DadosDoFavorito = Omit<NovoFavorito, "id">;

type ParteIdentificavel = { descricao?: string | null; categoria_ids: string[]; tags?: string[] | null; pessoa?: string | null; valor_centavos: number };

type Identificavel = {
  descricao?: string | null;
  tipo: string;
  conta_id: string;
  categoria_ids: string[];
  tags?: string[] | null;
  pessoa?: string | null;
  /** A compra com partes: com elas, `valor_centavos` é o total (ADR 0022). */
  partes?: ParteIdentificavel[] | null;
  valor_centavos?: number;
};

/** A fatia da parte no total, em pontos-base (`proporcao` em `app/sugestao.py`). */
const proporcao = (valor: number, total: number) => Math.floor((2 * valor * 10_000 + total) / (2 * total));

/** A parte como entra na identidade: o que ela é e a fatia da compra (`identidade_da_parte`). */
export const identidadeDaParte = (p: ParteIdentificavel, total: number) => [
  chaveDaDescricao(p.descricao ?? ""),
  [...p.categoria_ids].sort(),
  (p.tags ?? []).map((t) => t.toLowerCase()).sort(),
  p.pessoa ?? null,
  proporcao(p.valor_centavos, total),
];

/**
 * O que faz dois lançamentos serem "o mesmo" (`identidade_de` em `app/favoritos.py`). Com partes,
 * entram também a descrição, as categorias, as tags, a pessoa e a proporção de cada uma.
 */
export const identidadeDe = (l: Identificavel) => {
  const partes = l.partes ?? [];
  const total = partes.reduce((soma, p) => soma + p.valor_centavos, 0);
  return JSON.stringify([
    chaveDaDescricao(l.descricao ?? ""),
    l.tipo,
    l.conta_id,
    [...l.categoria_ids].sort(),
    (l.tags ?? []).map((t) => t.toLowerCase()).sort(),
    l.pessoa ?? null,
    ...(partes.length ? [partes.map((p) => identidadeDaParte(p, total))] : []),
  ]);
};

/**
 * O valor padrão de cada favorito: o do último lançamento com a mesma identidade entre os que a
 * tela mostra (servidor e fila, do mais novo ao mais antigo), ou o que o servidor já calculou.
 */
export function comValorPadrao<L extends Identificavel & { valor_centavos: number; data: string; conflito?: boolean; exclusao?: unknown }>(
  favoritos: Favorito[],
  lancamentos: L[],
  hoje: string,
): Favorito[] {
  const ultimos = new Map<string, number>();
  for (const l of lancamentos) {
    if (l.conflito || l.exclusao || l.data > hoje || l.valor_centavos <= 0) continue;
    const chave = identidadeDe(l);
    if (!ultimos.has(chave)) ultimos.set(chave, l.valor_centavos);
  }
  return favoritos.map((f) => ({ ...f, valor_padrao_centavos: ultimos.get(identidadeDe(f)) ?? f.valor_padrao_centavos }));
}

/** O lançamento que acabou de ser salvo e pode virar favorito: a oferta "⭐ Favoritar" depois do Salvar. */
export type Oferta = DadosDoFavorito & { id: string };

let oferta: Oferta | null = null;
const ouvintes = new Set<() => void>();
const avisar = () => ouvintes.forEach((o) => o());

export function oferecerFavoritar(nova: Oferta | null) {
  oferta = nova;
  avisar();
}

export function useOfertaDeFavoritar(): Oferta | null {
  return useSyncExternalStore(
    (ouvinte) => {
      ouvintes.add(ouvinte);
      return () => void ouvintes.delete(ouvinte);
    },
    () => oferta,
  );
}
