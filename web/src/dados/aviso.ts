// O aviso de planejamento ao lançar (ticket 52): cálculo puro sobre o planejamento do mês e o
// lançamento em edição, para rodar igual com e sem internet. Repete do servidor só o que o aviso
// precisa, conferido pelas mesmas tabelas (`tabelas-de-teste/`).
import type { components } from "../api/schema";
import { mesDepois } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";

/**
 * A categoria cujo item conta o lançamento (ou nenhuma) e se ele está "a escolher", dadas as
 * categorias dele com item no mês, a escolhida e a do item atual (`onde_conta` no servidor).
 */
export function ondeConta(comItem: Set<string>, escolhida: string | null | undefined, atual: string | null | undefined): [string | null, boolean] {
  if (escolhida && comItem.has(escolhida)) return [escolhida, false];
  if (atual && comItem.has(atual)) return [atual, comItem.size > 1];
  if (comItem.size === 1) return [[...comItem][0], false];
  return [null, comItem.size > 1];
}

/** (realizado + previsto) sobre o planejado, com o meio arredondado para o par, como o `round` do servidor. */
export function percentual(realizadoEPrevisto: number, planejado: number): number {
  const exato = (realizadoEPrevisto * 100) / planejado;
  const piso = Math.floor(exato);
  const resto = exato - piso;
  const arredondado = resto > 0.5 || (resto === 0.5 && piso % 2 !== 0) ? piso + 1 : piso;
  // Sem o zero negativo de -0,5.
  return arredondado + 0;
}

/** Os dias que decidem a fatura: os do titular (o adicional usa os dele). */
export type DiasDoTitular = { dia_fechamento?: number | null; mes_anterior_ao_fechamento?: boolean };
/** A fatura como o aparelho a guarda: o mês e o fechamento gravado, se há. */
export type FechamentoGravado = { mes: string; fechamento?: string | null };

/** O dia no mês (`AAAA-MM-01`); dia 31 em mês curto cai no último dia. */
function noMes(mes: string, dia: number): string {
  const [ano, numero] = mes.split("-").map(Number);
  const ultimo = new Date(Date.UTC(ano, numero, 0)).getUTCDate();
  return `${mes.slice(0, 8)}${String(Math.min(dia, ultimo)).padStart(2, "0")}`;
}

/** O fechamento da fatura de `mes`: o gravado ou, sem ele, o do dia padrão; `null` sem nenhum dos dois. */
export function fechamentoDaFatura(titular: DiasDoTitular, faturas: FechamentoGravado[], mes: string): string | null {
  const gravado = faturas.find((f) => f.mes === mes)?.fechamento;
  if (gravado) return gravado;
  // A fatura do mês anterior ao fechamento fecha no mês seguinte ao dela.
  return titular.dia_fechamento ? noMes(mesDepois(mes, titular.mes_anterior_ao_fechamento ? 1 : 0), titular.dia_fechamento) : null;
}

/**
 * A fatura (o mês, `AAAA-MM-01`) em que cai a compra no cartão feita em `data`: a primeira que fecha
 * depois dela, pelo fechamento gravado ou pelo dia padrão (`escolher_fatura` no servidor). `null`
 * quando o cartão não tem dia de fechamento: aí só a fatura escolhida à mão vale.
 */
export function mesDaCompra(titular: DiasDoTitular, faturas: FechamentoGravado[], data: string): string | null {
  const ateOFechamento = titular.mes_anterior_ao_fechamento ? 1 : 0;
  // Começa pela fatura do mês anterior: um fechamento editado pode ter escorregado para o mês da compra.
  for (let n = 0; n < 4; n++) {
    const mes = mesDepois(data, n - 1 - ateOFechamento);
    const fechamento = fechamentoDaFatura(titular, faturas, mes);
    if (!fechamento) return null;
    if (fechamento > data) return mes;
  }
  return null;
}

/** O cartão de uma compra, para o aparelho saber a fatura dela: os dias do titular e as faturas guardadas. */
export type CartaoDaCompra = { titular: DiasDoTitular; faturas: FechamentoGravado[] };

/**
 * O mês em que o lançamento conta (`AAAA-MM-01`): o da data, na conta; no cartão, a fatura escolhida
 * à mão, a que o servidor deu se a data e o cartão não mudaram, ou a da data (`mesDaCompra`), que na
 * parcela n vem n - 1 faturas depois (`mes_da_parcela` no servidor).
 */
export function mesEmQueConta(
  l: { conta_id: string; data: string; fatura_mes?: string | null },
  anterior: { conta_id: string; data: string; mes?: string | null; parcela?: number | null } | undefined,
  cartao: CartaoDaCompra | undefined,
): string | null {
  if (!cartao) return mesDepois(l.data, 0);
  if (l.fatura_mes) return l.fatura_mes;
  if (anterior?.mes && anterior.conta_id === l.conta_id && anterior.data === l.data) return anterior.mes;
  const daCompra = mesDaCompra(cartao.titular, cartao.faturas, l.data);
  return daCompra && mesDepois(daCompra, (anterior?.parcela ?? 1) - 1);
}

export type Planejamento = components["schemas"]["Planejamento"];
type AEscolher = Planejamento["a_escolher"][number];

/** O que decide onde e quanto um lançamento conta no planejamento. */
export type Contagem = {
  id: string;
  valor_centavos: number;
  categoria_ids: string[];
  item_categoria_id?: string | null;
  estorno_de?: string | null;
  estorno_avulso?: boolean | null;
  situacao: "previsto" | "realizado";
  /** O mês em que conta (`AAAA-MM-01`); `null` quando o aparelho não sabe (cartão sem fatura). */
  mes: string | null;
  /** Na compra com partes, cada parte conta no item dela (ADR 0022). */
  partes?: { id: string; valor_centavos: number; categoria_ids: string[]; item_categoria_id?: string | null }[] | null;
};

/** O que conta num item: o lançamento sem partes, ou cada parte da compra que tem partes. */
type Pedaco = { parte_id: string | null; valor_centavos: number; categoria_ids: string[]; item_categoria_id?: string | null };

function pedacosDe(l: Contagem): Pedaco[] {
  if (!l.partes?.length) return [{ parte_id: null, valor_centavos: l.valor_centavos, categoria_ids: l.categoria_ids, item_categoria_id: l.item_categoria_id }];
  return l.partes.map((p) => ({ parte_id: p.id, valor_centavos: p.valor_centavos, categoria_ids: p.categoria_ids, item_categoria_id: p.item_categoria_id }));
}

export type EstadoDoItem = Pick<Planejamento["itens"][number], "percentual" | "ainda_da_para_gastar_centavos">;

export type Aviso = {
  /** Na compra com partes, a parte de que é o aviso (uma linha por parte). */
  parte_id?: string;
  /** O mês em que o lançamento conta (`AAAA-MM-01`). */
  mes: string;
  /** As categorias do lançamento que têm item no mês, na ordem dele: as que se pode escolher. */
  categoriasComItem: string[];
  /** Duas ou mais com item e nenhuma escolha que valha. */
  aEscolher: boolean;
  /** O item em que ele conta, antes e depois do lançamento; `null` quando não conta em item. */
  item: { categoria_id: string; planejado_centavos: number; antes: EstadoDoItem; depois: EstadoDoItem } | null;
};

const doMes = (p: Planejamento, l: Contagem) => !!l.mes && l.mes.slice(0, 7) === p.mes;

/** As categorias, das dadas, que têm item no mês, na mesma ordem. */
export function categoriasComItem(p: Planejamento, categorias: string[]): string[] {
  const comItem = new Set(p.itens.map((i) => i.categoria_id));
  return categorias.filter((c) => comItem.has(c));
}

/** O item em que o lançamento (ou a parte dele) ficou quando surgiu a ambiguidade, que só o servidor sabe. */
export const itemAtual = (p: Planejamento, id: string, parteId: string | null = null) =>
  p.a_escolher.find((a) => a.lancamento_id === id && (a.parte_id ?? null) === parteId)?.item_categoria_id;

/** O planejamento sem a versão `antes` do lançamento e com a `depois`, somado como no servidor. */
function trocar(p: Planejamento, antes?: Contagem | null, depois?: Contagem | null): Planejamento {
  const id = (antes ?? depois)?.id;
  if (!id) return p;
  const somas = new Map(p.itens.map((i) => [i.categoria_id, { realizado: i.realizado_centavos, previsto: i.previsto_centavos }]));
  let aEscolher: AEscolher[] = p.a_escolher.filter((a) => a.lancamento_id !== id);
  for (const [l, sinal] of [[antes, -1], [depois, 1]] as const) {
    if (!l || !doMes(p, l)) continue;
    for (const pedaco of pedacosDe(l)) {
      const comItem = categoriasComItem(p, pedaco.categoria_ids);
      const [conta, fica] = ondeConta(new Set(comItem), pedaco.item_categoria_id, itemAtual(p, id, pedaco.parte_id));
      // O estorno diminui o item da compra que ele devolve; o avulso, o que ele escolhe.
      if (conta) somas.get(conta)![l.situacao] += sinal * (l.estorno_de || l.estorno_avulso ? -pedaco.valor_centavos : pedaco.valor_centavos);
      if (sinal > 0 && fica) aEscolher = [...aEscolher, { lancamento_id: id, ...(pedaco.parte_id && { parte_id: pedaco.parte_id }), item_categoria_id: conta, categorias_com_item: [...comItem].sort() }];
    }
  }
  const itens = p.itens.map((i) => {
    const { realizado, previsto } = somas.get(i.categoria_id)!;
    const usado = realizado + previsto;
    return { ...i, realizado_centavos: realizado, previsto_centavos: previsto, percentual: percentual(usado, i.planejado_centavos), ainda_da_para_gastar_centavos: i.planejado_centavos - usado };
  });
  // Como no servidor: o item estourado não abate a sobra dos outros, e o ajuste de fatura sim.
  const sobra = itens.reduce((total, i) => total + Math.max(i.ainda_da_para_gastar_centavos, 0), 0);
  return { ...p, itens, a_escolher: aEscolher, ainda_da_para_gastar_centavos: sobra - p.ajustes_de_fatura_centavos };
}

/** Uma mudança do aparelho que o servidor ainda não tem: a versão que ele tem e a do aparelho. */
export type Mudanca = { antes?: Contagem | null; depois?: Contagem | null };

/**
 * A mudança de um criar enviado sem resposta: o servidor talvez já o tenha (`jaNoServidor`, o que
 * foi enviado) e, se o planejamento foi lido depois do envio (`tentadoEm`), já o contou.
 */
export type MudancaTalvezJaContada = Mudanca & { talvez?: { tentadoEm: number; jaNoServidor: Contagem } };

/**
 * As mudanças sem contar duas vezes o criar que talvez já esteja no servidor: se o planejamento
 * foi lido (`lidoEm`) depois do envio, ele já traz o que foi enviado, e a fila só troca essa versão
 * pela do aparelho. É um palpite: se o envio nem chegou, o aviso fica um lançamento a menos até a fila subir.
 */
export function semContarDeNovo(mudancas: MudancaTalvezJaContada[], lidoEm: number): Mudanca[] {
  return mudancas.map(({ talvez, ...m }) => (talvez && lidoEm >= talvez.tentadoEm ? { ...m, antes: talvez.jaNoServidor } : m));
}

/** "Ainda dá para gastar R$ 180,00" ou "Passa R$ 50,00 do planejado"; na receita e na transferência, o que falta para o planejado. */
export function oQueSobra(tipo: "despesa" | "receita" | "transferencia", centavos: number): string {
  if (tipo !== "despesa") {
    if (centavos > 0) return `Faltam ${formatarCentavos(centavos)} para o planejado`;
    return centavos === 0 ? "Chega ao planejado" : `${formatarCentavos(-centavos)} acima do planejado`;
  }
  if (centavos > 0) return `Ainda dá para gastar ${formatarCentavos(centavos)}`;
  return centavos === 0 ? "Chega ao limite do planejado" : `Passa ${formatarCentavos(-centavos)} do planejado`;
}

/** O planejamento do servidor com as mudanças não enviadas por cima, na ordem. */
export function comAFila(p: Planejamento, mudancas: Mudanca[]): Planejamento {
  return mudancas.reduce((q, m) => trocar(q, m.antes, m.depois), p);
}

/**
 * O efeito do lançamento no planejamento do mês em que ele conta: `antes` é a versão que já conta
 * em `p` (na edição), `depois` a que está na tela. `null` quando `p` é de outro mês.
 */
export function avisoDePlanejamento(p: Planejamento, antes: Contagem | null, depois: Contagem): Aviso | null {
  return doMes(p, depois) ? avisoDoPedaco(p, antes, depois, pedacosDe({ ...depois, partes: null })[0]) : null;
}

/**
 * O aviso da compra com partes: uma linha por parte, no item dela, com o efeito da compra inteira
 * (duas partes no mesmo item somam). Vazio quando `p` é de outro mês.
 */
export function avisosDasPartes(p: Planejamento, antes: Contagem | null, depois: Contagem): Aviso[] {
  return doMes(p, depois) ? pedacosDe(depois).map((pedaco) => avisoDoPedaco(p, antes, depois, pedaco)) : [];
}

function avisoDoPedaco(p: Planejamento, antes: Contagem | null, depois: Contagem, pedaco: Pedaco): Aviso {
  const comItem = categoriasComItem(p, pedaco.categoria_ids);
  const [conta, aEscolher] = ondeConta(new Set(comItem), pedaco.item_categoria_id, itemAtual(p, depois.id, pedaco.parte_id));
  const aviso: Aviso = { ...(pedaco.parte_id && { parte_id: pedaco.parte_id }), mes: depois.mes!, categoriasComItem: comItem, aEscolher, item: null };
  if (!conta) return aviso;
  const estado = (q: Planejamento): EstadoDoItem => {
    const { percentual, ainda_da_para_gastar_centavos } = q.itens.find((i) => i.categoria_id === conta)!;
    return { percentual, ainda_da_para_gastar_centavos };
  };
  const planejado_centavos = p.itens.find((i) => i.categoria_id === conta)!.planejado_centavos;
  return { ...aviso, item: { categoria_id: conta, planejado_centavos, antes: estado(p), depois: estado(trocar(p, antes, depois)) } };
}

/**
 * A escolha mais recente (`em`) de um lançamento do mesmo conjunto: o que tem, das categorias com
 * item no mês (`comItemNoMes`), exatamente as do conjunto. O aparelho não sabe quando a escolha mudou,
 * só quando o lançamento mudou.
 */
export function ultimaEscolha(
  conjunto: string[],
  lancamentos: { categoria_ids: string[]; item_categoria_id?: string | null; em: number }[],
  comItemNoMes: string[],
): string | null {
  const doConjunto = (categorias: string[]) => {
    const comItem = categorias.filter((c) => comItemNoMes.includes(c));
    return comItem.length === conjunto.length && conjunto.every((c) => comItem.includes(c));
  };
  let ultima: { escolha: string; em: number } | null = null;
  for (const l of lancamentos) {
    const escolha = l.item_categoria_id;
    if (!escolha || !conjunto.includes(escolha) || !doConjunto(l.categoria_ids)) continue;
    if (!ultima || l.em > ultima.em) ultima = { escolha, em: l.em };
  }
  return ultima?.escolha ?? null;
}
