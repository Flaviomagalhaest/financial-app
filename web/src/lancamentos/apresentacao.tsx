import { formatarCentavos } from "./dinheiro";
import { dataPorExtenso } from "./datas";
import type { Cartao, NovoLancamento } from "../dados";

type ComNome = { id: string; nome: string };

/** `3` e "conta atrasada"/"contas atrasadas" vira "3 contas atrasadas". */
export const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

export const nomePorId = (lista: ComNome[], id: string) => lista.find((i) => i.id === id)?.nome ?? "?";

/** A descrição, ou as categorias quando não há descrição. */
export function tituloDoLancamento(l: Pick<NovoLancamento, "descricao" | "categoria_ids"> & Partial<Pick<NovoLancamento, "partes">>, categorias: ComNome[]): string {
  const dasCategorias = (ids: string[]) => ids.map((c) => nomePorId(categorias, c)).join(", ");
  // A compra com partes sem descrição se nomeia pelas partes (ADR 0022).
  if (!l.descricao && l.partes?.length) return l.partes.map((p) => p.descricao || dasCategorias(p.categoria_ids)).join(" + ");
  return l.descricao || dasCategorias(l.categoria_ids) || "Crédito";
}

/** `3` de `10` vira `03/10`, como a fatura mostra a parcela. */
export const numeroDaParcela = (parcela: number, parcelas: number) => `${String(parcela).padStart(2, "0")}/${String(parcelas).padStart(2, "0")}`;

/** O estorno, ligado a uma compra ou avulso, é uma despesa que devolve dinheiro (ADR 0016). */
export const eEstorno = (l: Pick<NovoLancamento, "estorno_de" | "estorno_avulso">) => !!l.estorno_de || !!l.estorno_avulso;

/** O estorno é uma despesa que devolve dinheiro: aparece como crédito (ADR 0016). */
export const eCredito = (l: Pick<NovoLancamento, "tipo" | "estorno_de" | "estorno_avulso">) => l.tipo !== "despesa" || eEstorno(l);

export function ValorComSinal({ l }: { l: Pick<NovoLancamento, "tipo" | "valor_centavos" | "estorno_de" | "estorno_avulso"> }) {
  return (
    <span className={eCredito(l) ? "receita" : "despesa"}>
      {eCredito(l) ? "+" : "−"} {formatarCentavos(l.valor_centavos)}
    </span>
  );
}

type ParaEstorno = Pick<NovoLancamento, "id" | "tipo" | "valor_centavos" | "data" | "estorno_de" | "estorno_avulso" | "descricao" | "categoria_ids"> & Partial<Pick<NovoLancamento, "partes">>;

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

/** "estorno de ..." no estorno, "estorno avulso" no avulso e "estornada em ..." na compra; vazio no resto. */
export function ligacaoDoEstorno(l: ParaEstorno, indice: IndiceDeEstornos, categorias: ComNome[]): string {
  if (l.estorno_avulso) return "estorno avulso";
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
    !eEstorno(l) &&
    // O estorno de uma parte da compra é do ticket 138 (ADR 0022).
    !l.partes?.length &&
    !l.naoEnviado &&
    !l.conflito &&
    !l.exclusao &&
    !l.recusa &&
    cartoes.some((c) => c.id === l.conta_id) &&
    restanteDaCompra(l, indice) > 0
  );
}

/** O nome de um favorito (ou sugerido): a descrição, ou as categorias quando não há descrição. */
export function tituloDoFavorito(f: { descricao: string; categoria_ids: string[]; partes?: { categoria_ids: string[] }[] }, categorias: ComNome[]): string {
  const ids = f.categoria_ids.length ? f.categoria_ids : [...new Set((f.partes ?? []).flatMap((p) => p.categoria_ids))];
  return f.descricao || ids.map((c) => nomePorId(categorias, c)).join(", ");
}
