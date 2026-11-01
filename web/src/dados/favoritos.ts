// Favoritos (ticket 62): lançamentos-modelo para lançar com um toque. O servidor guarda a lista; o
// aparelho a guarda para lançar sem internet e põe por cima o valor do último lançamento feito
// com cada favorito, mesmo o que ainda não subiu.
import { useSyncExternalStore } from "react";
import type { components } from "../api/schema";
import { identidadeDe, type Identificavel } from "./identidade";

export { identidadeDe };

export type Favorito = components["schemas"]["Favorito"];
export type Sugerido = components["schemas"]["Sugerido"];
export type NovoFavorito = components["schemas"]["NovoFavorito"];
export type DadosDoFavorito = Omit<NovoFavorito, "id">;

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
