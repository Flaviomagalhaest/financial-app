import { formatarCentavos } from "./dinheiro";
import { dataPorExtenso } from "./datas";
import type { Cartao, NovoLancamento } from "../dados";

type ComNome = { id: string; nome: string };

export const nomePorId = (lista: ComNome[], id: string) => lista.find((i) => i.id === id)?.nome ?? "?";

/** A descrição, ou as categorias quando não há descrição. */
export function tituloDoLancamento(l: Pick<NovoLancamento, "descricao" | "categoria_ids">, categorias: ComNome[]): string {
  return l.descricao || l.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ");
}

/** O estorno é uma despesa que devolve dinheiro: aparece como crédito (ADR 0016). */
export const eCredito = (l: Pick<NovoLancamento, "tipo" | "estorno_de">) => l.tipo !== "despesa" || !!l.estorno_de;

export function ValorComSinal({ l }: { l: NovoLancamento }) {
  return (
    <span className={eCredito(l) ? "receita" : "despesa"}>
      {eCredito(l) ? "+" : "−"} {formatarCentavos(l.valor_centavos)}
    </span>
  );
}

type ParaEstorno = Pick<NovoLancamento, "id" | "tipo" | "valor_centavos" | "data" | "estorno_de" | "descricao" | "categoria_ids">;

/** Os estornos de cada compra, pelo id da compra, e as compras pelo id, para ligar uma ponta à outra. */
export function indiceDeEstornos<L extends ParaEstorno>(lancamentos: L[]) {
  const compras = new Map<string, L>();
  const estornos = new Map<string, L[]>();
  for (const l of lancamentos) {
    compras.set(l.id, l);
    if (l.estorno_de) estornos.set(l.estorno_de, [...(estornos.get(l.estorno_de) ?? []), l]);
  }
  return { compras, estornos };
}

export type IndiceDeEstornos = ReturnType<typeof indiceDeEstornos>;

/** Quanto da compra ainda pode ser estornado: o valor menos os estornos, sem contar `exceto` (o que se edita). */
export function restanteDaCompra(compra: ParaEstorno, indice: IndiceDeEstornos, exceto?: string): number {
  const estornado = (indice.estornos.get(compra.id) ?? []).filter((e) => e.id !== exceto).reduce((soma, e) => soma + e.valor_centavos, 0);
  return compra.valor_centavos - estornado;
}

/** "estorno de ..." no estorno e "estornada em ..." na compra; vazio no resto. */
export function ligacaoDoEstorno(l: ParaEstorno, indice: IndiceDeEstornos, categorias: ComNome[]): string {
  if (l.estorno_de) {
    const compra = indice.compras.get(l.estorno_de);
    return `estorno de ${compra ? tituloDoLancamento(compra, categorias) : "uma compra"}`;
  }
  const estornos = indice.estornos.get(l.id);
  if (!estornos?.length) return "";
  const em = [...estornos].sort((a, b) => a.data.localeCompare(b.data)).map((e) => `${dataPorExtenso(e.data)} (${formatarCentavos(e.valor_centavos)})`);
  return `estornada em ${em.join(", ")}`;
}

/** "Estornar" só na compra no cartão que o servidor já tem e que ainda não foi toda devolvida. */
export function podeEstornar(l: ParaEstorno & { conta_id: string; naoEnviado?: boolean; conflito?: boolean; exclusao?: unknown; recusa?: string }, cartoes: Cartao[], indice: IndiceDeEstornos): boolean {
  return (
    l.tipo === "despesa" &&
    !l.estorno_de &&
    !l.naoEnviado &&
    !l.conflito &&
    !l.exclusao &&
    !l.recusa &&
    cartoes.some((c) => c.id === l.conta_id) &&
    restanteDaCompra(l, indice) > 0
  );
}

/** O nome de um favorito (ou sugerido): a descrição, ou as categorias quando não há descrição. */
export function tituloDoFavorito(f: { descricao: string; categoria_ids: string[] }, categorias: ComNome[]): string {
  return f.descricao || f.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ");
}
