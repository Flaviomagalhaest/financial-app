// O que faz dois lançamentos serem "o mesmo" (favorito, sugerido, sugestão), igual ao servidor
// (`identidade_de` em `app/favoritos.py`).

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

type ParteIdentificavel = { descricao?: string | null; categoria_ids: string[]; tags?: string[] | null; pessoa?: string | null; valor_centavos: number };

export type Identificavel = {
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

/** A fatia da parte no total, em percentual inteiro (`proporcao` em `app/sugestao.py`). */
const proporcao = (valor: number, total: number) => Math.floor((2 * valor * 100 + total) / (2 * total));

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

