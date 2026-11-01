// A busca (ticket 59, ADR 0013). A completa roda no servidor (`app/busca.py`); sem internet, o
// aparelho aplica os mesmos critérios ao que guarda (os lançamentos da última lista e os não
// enviados), sem as transferências, e a tela avisa que o resultado é parcial.
import type { components } from "../api/schema";
import { eEstorno } from "../lancamentos/apresentacao";

type PedidoDeBusca = components["schemas"]["PedidoDeBusca"];
/** Sem um critério, ele não restringe. */
export type Criterios = Partial<Omit<PedidoDeBusca, "pagina">>;
export type Transferencia = components["schemas"]["Transferencia"];
type TotaisDaBusca = components["schemas"]["TotaisDaBusca"];

/** O que a busca precisa do lançamento como a tela o mostra (`LancamentoNaTela`). */
export type LancamentoDaBusca = {
  id: string;
  tipo: "despesa" | "receita";
  situacao: "previsto" | "realizado";
  valor_centavos: number;
  data: string;
  descricao?: string;
  conta_id: string;
  categoria_ids: string[];
  tags?: string[];
  pessoa?: string | null;
  fatura_mes?: string | null;
  mes?: string;
  estorno_de?: string | null;
  estorno_avulso?: boolean | null;
  estorno_parcelamento_id?: string | null;
  parcelamento_id?: string | null;
  parcela?: number | null;
  parcelas?: number | null;
  /** As partes da compra (ADR 0022): os filtros de classificação olham cada uma. */
  partes?: { id: string; descricao?: string; valor_centavos: number; categoria_ids: string[]; tags: string[]; pessoa?: string | null }[] | null;
};

export type ParcelamentoNaTela<L> = {
  parcelamento_id: string;
  descricao: string;
  data: string;
  parcelas: number;
  valor_centavos: number;
  lancamentos: L[];
};

/** `partes_achadas`: com filtro de categoria, tag ou pessoa, as partes da compra que batem; a linha vale a soma delas. */
export type LinhaNaTela<L> = { lancamento: L; partes_achadas?: string[] | null } | { parcelamento: ParcelamentoNaTela<L> } | { transferencia: Transferencia };

export type ResultadoNaTela<L> = { totais: TotaisDaBusca; linhas: LinhaNaTela<L>[] };

/** O pedido completo, com os valores padrão do servidor no que a tela não escolheu. */
export function pedidoDaBusca(criterios: Criterios, pagina: number): PedidoDeBusca {
  return {
    texto: "",
    categoria_ids: [],
    tags: [],
    sem_categoria: false,
    sem_tag: false,
    conta_ids: [],
    pessoas: [],
    conjunto: false,
    situacoes: [],
    tipos: [],
    ordem: "recentes",
    ...criterios,
    pagina,
  };
}

/** O pedaço do endereço (`#/busca?...`) de cada critério; as listas repetem a chave. */
const LISTAS = { categoria_ids: "categoria", tags: "tag", conta_ids: "conta", pessoas: "pessoa", situacoes: "situacao", tipos: "tipo" } as const;
const MARCAS = { sem_categoria: "sem-categoria", sem_tag: "sem-tag", conjunto: "conjunto" } as const;

/** `#/busca` com os critérios, para os atalhos e para a tela guardar o que se escolheu. */
export function enderecoDaBusca(criterios: Criterios): string {
  const p = new URLSearchParams();
  if (criterios.texto?.trim()) p.set("texto", criterios.texto.trim());
  if (criterios.valor_minimo_centavos != null) p.set("minimo", String(criterios.valor_minimo_centavos));
  if (criterios.valor_maximo_centavos != null) p.set("maximo", String(criterios.valor_maximo_centavos));
  for (const [campo, chave] of Object.entries(LISTAS)) for (const valor of criterios[campo as keyof typeof LISTAS] ?? []) p.append(chave, valor);
  for (const [campo, chave] of Object.entries(MARCAS)) if (criterios[campo as keyof typeof MARCAS]) p.set(chave, "1");
  if (criterios.periodo_de) p.set("de", criterios.periodo_de);
  if (criterios.periodo_ate) p.set("ate", criterios.periodo_ate);
  if (criterios.fatura) {
    p.set("fatura", criterios.fatura.mes.slice(0, 7));
    if (criterios.fatura.cartao_id) p.set("cartao", criterios.fatura.cartao_id);
  }
  if (criterios.ordem === "valor") p.set("ordem", "valor");
  const consulta = p.toString();
  return consulta ? `#/busca?${consulta}` : "#/busca";
}

const MES = /^\d{4}-(0[1-9]|1[0-2])$/;
const DIA = /^\d{4}-\d{2}-\d{2}$/;

/** Os critérios do endereço; o que não se entende fica de fora. */
export function criteriosDoEndereco(consulta: string): Criterios {
  const p = new URLSearchParams(consulta);
  const criterios: Criterios = {};
  const texto = p.get("texto");
  if (texto) criterios.texto = texto;
  const centavos = (chave: string) => {
    const valor = Number(p.get(chave) ?? NaN);
    return Number.isInteger(valor) && valor >= 0 ? valor : undefined;
  };
  if (centavos("minimo") !== undefined) criterios.valor_minimo_centavos = centavos("minimo");
  if (centavos("maximo") !== undefined) criterios.valor_maximo_centavos = centavos("maximo");
  for (const [campo, chave] of Object.entries(LISTAS)) {
    const valores = p.getAll(chave).filter(Boolean);
    if (valores.length) (criterios as Record<string, unknown>)[campo] = valores;
  }
  if (criterios.situacoes) criterios.situacoes = criterios.situacoes.filter((s) => s === "previsto" || s === "realizado");
  if (criterios.tipos) criterios.tipos = criterios.tipos.filter((t) => t === "despesa" || t === "receita" || t === "transferencia");
  for (const [campo, chave] of Object.entries(MARCAS)) if (p.get(chave) === "1") criterios[campo as keyof typeof MARCAS] = true;
  const de = p.get("de");
  const ate = p.get("ate");
  if (de && DIA.test(de)) criterios.periodo_de = de;
  if (ate && DIA.test(ate)) criterios.periodo_ate = ate;
  const fatura = p.get("fatura");
  if (fatura && MES.test(fatura)) criterios.fatura = { mes: `${fatura}-01`, cartao_id: p.get("cartao") || undefined };
  if (p.get("ordem") === "valor") criterios.ordem = "valor";
  return criterios;
}

/** Como o servidor compara o texto: sem acento e sem maiúscula. */
export function semAcento(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
}

/** O mês em que o lançamento conta: o da fatura no cartão, o da data no resto (ADR 0003). */
const mesEmQueConta = (l: LancamentoDaBusca) => l.mes ?? l.fatura_mes ?? `${l.data.slice(0, 7)}-01`;

type Cartao = { id: string; titular_id?: string | null };

/**
 * A busca no aparelho, com as regras da do servidor: entre filtros é E, dentro de um filtro OU; o
 * período pela data da compra; fora do filtro Fatura, o parcelamento numa linha. O aparelho não
 * guarda transferências nem o parcelamento: a data da compra é a da primeira parcela que ele tem.
 */
export function buscarNoAparelho<L extends LancamentoDaBusca>(lancamentos: L[], criterios: Criterios, cartoes: Cartao[]): ResultadoNaTela<L> {
  const agrupar = !criterios.fatura;
  const dataDaCompra = new Map<string, string>();
  for (const l of lancamentos) {
    if (!l.parcelamento_id) continue;
    const antes = dataDaCompra.get(l.parcelamento_id);
    if (!antes || l.data < antes) dataDaCompra.set(l.parcelamento_id, l.data);
  }
  const dataDaLinha = (l: L) => (agrupar && l.parcelamento_id ? dataDaCompra.get(l.parcelamento_id)! : l.data);
  const texto = semAcento(criterios.texto ?? "");
  const tags = new Set((criterios.tags ?? []).map((t) => t.trim().toLowerCase()));
  const doCartao = criterios.fatura?.cartao_id ? new Set(cartoes.filter((c) => c.id === criterios.fatura!.cartao_id || c.titular_id === criterios.fatura!.cartao_id).map((c) => c.id)) : null;
  const algum = <T>(lista: T[] | undefined, teste: (valor: T) => boolean) => !lista?.length || lista.some(teste);
  // Os filtros de categoria, tag e pessoa, sobre o lançamento sem partes ou sobre uma parte.
  const classifica = !!(criterios.categoria_ids?.length || criterios.sem_categoria || tags.size || criterios.sem_tag || criterios.pessoas?.length || criterios.conjunto);
  const bate = (c: { categoria_ids: string[]; tags?: string[]; pessoa?: string | null }) =>
    (!(criterios.categoria_ids?.length || criterios.sem_categoria) || c.categoria_ids.some((id) => criterios.categoria_ids?.includes(id)) || (!!criterios.sem_categoria && !c.categoria_ids.length)) &&
    (!(tags.size || criterios.sem_tag) || (c.tags ?? []).some((t) => tags.has(t.toLowerCase())) || (!!criterios.sem_tag && !c.tags?.length)) &&
    (!(criterios.pessoas?.length || criterios.conjunto) || (!!c.pessoa && !!criterios.pessoas?.includes(c.pessoa)) || (!!criterios.conjunto && !c.pessoa));
  // A compra com partes bate pelas partes que batem com todos os filtros de classificação (ADR 0022).
  const achadasDe = (l: L) => (classifica && l.partes?.length ? l.partes.filter(bate) : null);
  const valorDe = (l: L) => {
    const achadas = achadasDe(l);
    return achadas ? achadas.reduce((soma, p) => soma + p.valor_centavos, 0) : l.valor_centavos;
  };

  const achados = lancamentos.filter((l) => {
    if (texto && !semAcento(l.descricao ?? "").includes(texto) && !(l.partes ?? []).some((p) => semAcento(p.descricao ?? "").includes(texto))) return false;
    const achadas = achadasDe(l);
    if (achadas ? achadas.length === 0 : !bate(l)) return false;
    if (!algum(criterios.conta_ids, (c) => c === l.conta_id)) return false;
    if (criterios.periodo_de && dataDaLinha(l) < criterios.periodo_de) return false;
    if (criterios.periodo_ate && dataDaLinha(l) > criterios.periodo_ate) return false;
    if (criterios.fatura && (mesEmQueConta(l) !== criterios.fatura.mes || (doCartao && !doCartao.has(l.conta_id)))) return false;
    if (!algum(criterios.situacoes, (s) => s === l.situacao)) return false;
    return algum(criterios.tipos, (t) => t === l.tipo);
  });

  const grupos = new Map<string, L[]>();
  for (const l of achados) {
    const chave = agrupar && l.parcelamento_id ? l.parcelamento_id : l.id;
    grupos.set(chave, [...(grupos.get(chave) ?? []), l]);
  }
  const linhas = [...grupos.entries()]
    .map(([chave, doGrupo]) => {
      const valor = doGrupo.reduce((soma, l) => soma + valorDe(l), 0);
      const primeira = doGrupo[0];
      const linha: LinhaNaTela<L> =
        agrupar && primeira.parcelamento_id
          ? {
              parcelamento: {
                parcelamento_id: chave,
                descricao: primeira.descricao ?? "",
                data: dataDaLinha(primeira),
                parcelas: primeira.parcelas ?? doGrupo.length,
                valor_centavos: valor,
                lancamentos: [...doGrupo].sort((a, b) => (a.parcela ?? 0) - (b.parcela ?? 0)),
              },
            }
          : { lancamento: primeira, partes_achadas: achadasDe(primeira)?.map((p) => p.id) ?? null };
      return { linha, doGrupo, valor, data: dataDaLinha(primeira) };
    })
    .filter(({ valor }) => (criterios.valor_minimo_centavos == null || valor >= criterios.valor_minimo_centavos) && (criterios.valor_maximo_centavos == null || valor <= criterios.valor_maximo_centavos))
    // A lista do aparelho já vem da mais recente à mais antiga: o sort estável a mantém no mesmo dia.
    .sort((a, b) => (criterios.ordem === "valor" && b.valor !== a.valor ? b.valor - a.valor : b.data.localeCompare(a.data)));

  const somas = { despesa: { realizado: 0, previsto: 0 }, receita: { realizado: 0, previsto: 0 } };
  for (const { doGrupo } of linhas) for (const l of doGrupo) somas[l.tipo][l.situacao] += (l.tipo === "despesa" && eEstorno(l) ? -1 : 1) * valorDe(l);
  const porSituacao = (s: { realizado: number; previsto: number }) => ({ realizado_centavos: s.realizado, previsto_centavos: s.previsto });
  return {
    totais: {
      quantidade: linhas.length,
      despesas: porSituacao(somas.despesa),
      receitas: porSituacao(somas.receita),
      saldo: porSituacao({ realizado: somas.receita.realizado - somas.despesa.realizado, previsto: somas.receita.previsto - somas.despesa.previsto }),
    },
    linhas: linhas.map(({ linha }) => linha),
  };
}
