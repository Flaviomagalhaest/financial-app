import { dividirEmParcelas, dividirNaProporcao, formatarCentavos } from "./dinheiro";
import { dataPorExtenso } from "./datas";
import { idNaParcela } from "./uuid5";
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

type DoEstorno = Pick<NovoLancamento, "estorno_de" | "estorno_avulso" | "estorno_parcelamento_id">;

/** O estorno, ligado a uma compra (ou à parte dela), a todas as parcelas ou avulso, é uma despesa que devolve dinheiro (ADR 0016). */
export const eEstorno = (l: DoEstorno) => !!l.estorno_de || !!l.estorno_avulso || !!l.estorno_parcelamento_id;

/** O estorno é uma despesa que devolve dinheiro: aparece como crédito (ADR 0016). */
export const eCredito = (l: Pick<NovoLancamento, "tipo"> & DoEstorno) => l.tipo !== "despesa" || eEstorno(l);

export function ValorComSinal({ l }: { l: Pick<NovoLancamento, "tipo" | "valor_centavos"> & DoEstorno }) {
  return (
    <span className={eCredito(l) ? "receita" : "despesa"}>
      {eCredito(l) ? "+" : "−"} {formatarCentavos(l.valor_centavos)}
    </span>
  );
}

type ParaEstorno = Pick<NovoLancamento, "id" | "tipo" | "valor_centavos" | "data" | "estorno_de" | "estorno_avulso" | "descricao" | "categoria_ids"> &
  Partial<Pick<NovoLancamento, "partes" | "estorno_parte_id" | "estorno_parcelamento_id">> & {
    /** A parcela de um parcelamento (lançamento lido do servidor). */
    parcelamento_id?: string | null;
    parcela?: number | null;
    parcelas?: number | null;
    tags?: string[];
    pessoa?: string | null;
  };

/**
 * Os estornos de cada compra, pelo id da compra, e as compras pelo id, para ligar uma ponta à outra.
 * `todas` são os estornos de todas as parcelas, pelo id do parcelamento, `parcelas` as parcelas de cada parcelamento e `totais`
 * o total de cada um (que o aparelho guarda com a lista dos parcelamentos).
 */
export function indiceDeEstornos<L extends ParaEstorno>(lancamentos: L[], parcelamentos: ParcelamentoDoEstorno[] = []) {
  const compras = new Map<string, L>();
  const estornos = new Map<string, L[]>();
  const todas = new Map<string, L[]>();
  const parcelas = new Map<string, L[]>();
  for (const l of lancamentos) {
    compras.set(l.id, l);
    if (l.estorno_de) estornos.set(l.estorno_de, [...(estornos.get(l.estorno_de) ?? []), l]);
    if (l.estorno_parcelamento_id) todas.set(l.estorno_parcelamento_id, [...(todas.get(l.estorno_parcelamento_id) ?? []), l]);
    if (l.parcelamento_id) parcelas.set(l.parcelamento_id, [...(parcelas.get(l.parcelamento_id) ?? []), l]);
  }
  const totais = new Map(parcelamentos.map((p) => [p.id, p.valor_total_centavos]));
  const regras = new Map(parcelamentos.map((p) => [p.id, p]));
  return { compras, estornos, todas, parcelas, totais, regras };
}

/** O parcelamento como o aparelho o guarda, com as partes dele (ticket 139) quando tem. */
type ParcelamentoDoEstorno = {
  id: string;
  valor_total_centavos: number;
  parcelas?: number;
  partes?: { id: string; valor_centavos: number; descricao?: string; categoria_ids?: string[] }[];
};

export type IndiceDeEstornos = ReturnType<typeof indiceDeEstornos>;

const soma = (lista: { id: string; valor_centavos: number }[], exceto?: string) => lista.filter((e) => e.id !== exceto).reduce((total, e) => total + e.valor_centavos, 0);

/** Quanto da compra ainda pode ser estornado: o valor menos os estornos, sem contar `exceto` (o que se edita). */
export function restanteDaCompra(compra: ParaEstorno, indice: IndiceDeEstornos, exceto?: string): number {
  return compra.valor_centavos - soma(indice.estornos.get(compra.id) ?? [], exceto);
}

/** Quanto de uma parte da compra ainda pode ser estornado: o valor dela menos os estornos dela (ticket 138). */
export function restanteDaParte(compra: ParaEstorno, parteId: string, indice: IndiceDeEstornos, exceto?: string): number {
  const parte = compra.partes?.find((p) => p.id === parteId);
  if (!parte) return 0;
  return parte.valor_centavos - soma((indice.estornos.get(compra.id) ?? []).filter((e) => e.estorno_parte_id === parteId), exceto);
}

/**
 * Quanto do parcelamento ainda pode ser estornado, entre uma parcela e todas: o total menos o estornado em cada parcela e em
 * todas (ticket 138). O `total` é o do parcelamento, que o aparelho guarda com a lista dele.
 */
export function restanteDoParcelamento(total: number, parcelamentoId: string, indice: IndiceDeEstornos, exceto?: string): number {
  const dasParcelas = (indice.parcelas.get(parcelamentoId) ?? []).flatMap((p) => indice.estornos.get(p.id) ?? []);
  return total - soma(dasParcelas, exceto) - soma(indice.todas.get(parcelamentoId) ?? [], exceto);
}

/**
 * Quanto cada parte do parcelamento soma nas parcelas: cada parcela dividida na proporção das partes, como o servidor divide
 * (`somas_nas_parcelas`, ticket 160). Repete as contas de `dividirEmParcelas` e `dividirNaProporcao` (ADR 0018).
 */
export function somasDasPartes(regra: ParcelamentoDoEstorno): Map<string, number> {
  const partes = regra.partes ?? [];
  const parcelas = regra.parcelas ?? 0;
  if (!partes.length || !parcelas) return new Map();
  const { primeira, outras } = dividirEmParcelas(regra.valor_total_centavos, parcelas);
  const pesos = partes.map((p) => p.valor_centavos);
  const daPrimeira = dividirNaProporcao(pesos, primeira);
  const dasOutras = dividirNaProporcao(pesos, outras);
  return new Map(partes.map((p, i) => [p.id, daPrimeira[i] + dasOutras[i] * (parcelas - 1)]));
}

/**
 * A parte do parcelamento de que veio a parte de uma parcela: a cujo `idNaParcela` (uuid5 da parcela e da parte) é o da parte da
 * parcela, a mesma ligação do servidor (`id_na_parcela`, ticket 190). A parte própria da parcela não tem parte do parcelamento.
 */
export function parteDoParcelamento(parcela: ParaEstorno, parteId: string, regra: ParcelamentoDoEstorno | undefined): string | undefined {
  return regra?.partes?.find((r) => idNaParcela(parcela.id, r.id) === parteId)?.id;
}

/** A parte da parcela que veio de uma parte do parcelamento, o caminho inverso de `parteDoParcelamento`, pela mesma conta. */
export function parteDaParcela(parcela: ParaEstorno, parteId: string, regra: ParcelamentoDoEstorno | undefined): string | undefined {
  if (!regra?.partes?.some((r) => r.id === parteId)) return undefined;
  const id = idNaParcela(parcela.id, parteId);
  return parcela.partes?.find((p) => p.id === id)?.id;
}

/**
 * Quanto de uma parte do parcelamento ainda pode ser estornado: a soma dela nas parcelas menos o estornado nela, em todas as parcelas
 * e na parte de cada parcela que veio dela (ticket 160).
 */
export function restanteDaParteDoParcelamento(parcelamentoId: string, parteId: string, indice: IndiceDeEstornos, exceto?: string): number {
  const regra = indice.regras.get(parcelamentoId);
  const total = regra ? somasDasPartes(regra).get(parteId) : undefined;
  if (total === undefined) return 0;
  const deTodas = (indice.todas.get(parcelamentoId) ?? []).filter((e) => e.estorno_parte_id === parteId);
  const dasParcelas = (indice.parcelas.get(parcelamentoId) ?? []).flatMap((p) =>
    (indice.estornos.get(p.id) ?? []).filter((e) => e.estorno_parte_id && parteDoParcelamento(p, e.estorno_parte_id, regra) === parteId),
  );
  return total - soma(deTodas, exceto) - soma(dasParcelas, exceto);
}

/** O que cabe no estorno de uma compra ou parcela: o que resta dela e, na parcela, do parcelamento (se o aparelho já o conhece). */
export function restanteDaParcela(parcela: ParaEstorno, indice: IndiceDeEstornos, exceto?: string): number {
  const dela = restanteDaCompra(parcela, indice, exceto);
  const total = parcela.parcelamento_id ? indice.totais.get(parcela.parcelamento_id) : undefined;
  return total === undefined ? dela : Math.min(dela, restanteDoParcelamento(total, parcela.parcelamento_id!, indice, exceto));
}

/** O que cabe no estorno que a tela monta: de uma parte, de todas as parcelas ou da compra (ou da parcela). */
export function restanteDoEstorno(
  compra: ParaEstorno | undefined,
  parteId: string | null,
  todas: boolean,
  parcelamentoId: string | undefined,
  indice: IndiceDeEstornos,
  exceto?: string,
): number {
  const total = parcelamentoId ? indice.totais.get(parcelamentoId) : undefined;
  if (todas) {
    if (!parcelamentoId || total === undefined) return 0;
    const doParcelamento = restanteDoParcelamento(total, parcelamentoId, indice, exceto);
    // No parcelamento com partes, `parteId` é uma parte dele (ticket 160).
    return parteId ? Math.min(restanteDaParteDoParcelamento(parcelamentoId, parteId, indice, exceto), doParcelamento) : doParcelamento;
  }
  if (!compra) return 0;
  const daParcela = restanteDaParcela(compra, indice, exceto);
  if (!parteId) return daParcela;
  const daParte = Math.min(restanteDaParte(compra, parteId, indice, exceto), daParcela);
  // A parte da parcela também respeita o que resta da parte do parcelamento de que veio.
  const deQual = compra.parcelamento_id ? parteDoParcelamento(compra, parteId, indice.regras.get(compra.parcelamento_id)) : undefined;
  return deQual ? Math.min(daParte, restanteDaParteDoParcelamento(compra.parcelamento_id!, deQual, indice, exceto)) : daParte;
}

/** A descrição da parte, ou as categorias dela. */
export const nomeDaParte = (parte: { descricao?: string; categoria_ids?: string[] }, categorias: ComNome[]) =>
  parte.descricao || (parte.categoria_ids ?? []).map((c) => nomePorId(categorias, c)).join(", ");

/** "estorno de ..." no estorno, "estorno avulso" no avulso e "estornada em ..." na compra; vazio no resto. */
export function ligacaoDoEstorno(l: ParaEstorno, indice: IndiceDeEstornos, categorias: ComNome[]): string {
  if (l.estorno_avulso) return "estorno avulso";
  if (l.estorno_parcelamento_id) {
    const parte = l.estorno_parte_id ? indice.regras.get(l.estorno_parcelamento_id)?.partes?.find((p) => p.id === l.estorno_parte_id) : undefined;
    return `estorno de todas as parcelas${parte ? ` — ${nomeDaParte(parte, categorias)}` : ""}`;
  }
  if (l.estorno_de) {
    const compra = indice.compras.get(l.estorno_de);
    const parte = l.estorno_parte_id ? compra?.partes?.find((p) => p.id === l.estorno_parte_id) : undefined;
    const daParte = parte ? ` — ${nomeDaParte(parte, categorias)}` : "";
    return `estorno de ${compra ? tituloDoLancamento(compra, categorias) : "uma compra"}${daParte}`;
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
    !l.naoEnviado &&
    !l.conflito &&
    !l.exclusao &&
    !l.recusa &&
    cartoes.some((c) => c.id === l.conta_id) &&
    restanteDaParcela(l, indice) > 0
  );
}

/** O nome de um favorito (ou sugerido): a descrição, ou as categorias quando não há descrição. */
export function tituloDoFavorito(f: { descricao: string; categoria_ids: string[]; partes?: { categoria_ids: string[] }[] }, categorias: ComNome[]): string {
  const ids = f.categoria_ids.length ? f.categoria_ids : [...new Set((f.partes ?? []).flatMap((p) => p.categoria_ids))];
  return f.descricao || ids.map((c) => nomePorId(categorias, c)).join(", ");
}
