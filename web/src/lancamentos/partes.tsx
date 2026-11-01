// As partes da compra (ADR 0022): a compra que junta coisas diferentes, dividida em pedaços com
// classificação própria. A fatura e o extrato mostram a compra numa linha só, que abre as partes;
// quem filtra por categoria, tag ou pessoa vê só a parte que bate, com o valor dela.
import type { ReactNode } from "react";
import type { components } from "../api/schema";
import { chaveDaTag, type Categoria, type Pessoa } from "../dados";
import { nomePorId } from "./apresentacao";
import { comoDigitado, emCentavos, formatarCentavos } from "./dinheiro";
import { SeletorDeTags } from "./SeletorDeTags";

export type Parte = components["schemas"]["Parte"];

/** A classificação de um lançamento sem partes ou de uma parte: o que os filtros olham. */
type Classificado = { categoria_ids: string[]; tags?: string[]; pessoa?: string | null };

/** O filtro de classificação; campo vazio não restringe. `null` em `pessoas` é o conjunto. */
export type FiltroDeClassificacao = { categorias?: string[]; tags?: string[]; pessoas?: (string | null)[] };

const filtra = (f: FiltroDeClassificacao) => !!(f.categorias?.length || f.tags?.length || f.pessoas?.length);

function bate(c: Classificado, f: FiltroDeClassificacao): boolean {
  if (f.categorias?.length && !c.categoria_ids.some((id) => f.categorias!.includes(id))) return false;
  if (f.tags?.length && !(c.tags ?? []).some((t) => f.tags!.some((ft) => chaveDaTag(ft) === chaveDaTag(t)))) return false;
  if (f.pessoas?.length && !f.pessoas.includes(c.pessoa ?? null)) return false;
  return true;
}

/**
 * Das partes da compra, as que batem com todos os filtros, como no servidor (`partes_achadas`):
 * `null` quando não há filtro ou o lançamento não tem partes (vale ele inteiro).
 */
export function partesQueBatem(l: Classificado & { partes?: Parte[] | null }, f: FiltroDeClassificacao): Parte[] | null {
  if (!l.partes?.length || !filtra(f)) return null;
  return l.partes.filter((p) => bate(p, f));
}

/** O lançamento passa no filtro: ele mesmo, ou uma das partes dele. */
export function bateComOFiltro(l: Classificado & { partes?: Parte[] | null }, f: FiltroDeClassificacao): boolean {
  if (!filtra(f)) return true;
  const partes = partesQueBatem(l, f);
  return partes ? partes.length > 0 : bate(l, f);
}

/** O valor que conta no filtro: o das partes que batem, ou o do lançamento. */
export function valorNoFiltro(l: Classificado & { valor_centavos: number; partes?: Parte[] | null }, f: FiltroDeClassificacao): number {
  const partes = partesQueBatem(l, f);
  return partes ? partes.reduce((soma, p) => soma + p.valor_centavos, 0) : l.valor_centavos;
}

/** "Roupa · #presente · Fulana": a classificação de uma parte, numa linha. */
export function resumoDaParte(p: Parte, categorias: Categoria[], nomeDe: (id: string) => string): string {
  return [p.categoria_ids.map((c) => nomePorId(categorias, c)).join(", "), ...p.tags.map((t) => `#${t}`), p.pessoa ? nomeDe(p.pessoa) : "conjunto"].filter(Boolean).join(" · ");
}

/** "Vestido R$ 500,00 (Roupa); Fone R$ 250,00 (Eletrônico)": as partes numa linha, para a tela de conflito. */
export function partesEmTexto(partes: Parte[], categorias: Categoria[], nomeDe: (id: string) => string): string {
  if (!partes.length) return "(sem partes)";
  return partes.map((p) => `${p.descricao || "Parte"} ${formatarCentavos(p.valor_centavos)} (${resumoDaParte(p, categorias, nomeDe)})`).join("; ");
}

/**
 * As partes de uma compra, para abrir na linha dela (Histórico, fatura, busca). Com `so`, só essas,
 * que são as que batem com o filtro da tela.
 */
export function PartesDaCompra(props: { partes: Parte[]; so?: Parte[] | null; categorias: Categoria[]; nomeDe: (id: string) => string; titulo: string }) {
  const mostradas = props.so ?? props.partes;
  const rotulo = props.so ? `${mostradas.length} de ${props.partes.length} partes` : `${props.partes.length} partes`;
  return (
    <details className="partes-da-compra">
      <summary aria-label={`Partes de ${props.titulo}`}>{rotulo}</summary>
      <ul aria-label={`Partes de ${props.titulo}`}>
        {mostradas.map((p) => (
          <li key={p.id}>
            <div>
              <span>{p.descricao || "Parte"}</span>
              <span className="despesa">− {formatarCentavos(p.valor_centavos)}</span>
            </div>
            <p className="vazio">{resumoDaParte(p, props.categorias, props.nomeDe)}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

/**
 * O valor dividido pelas partes na proporção dos `pesos`, como no servidor (`app/partes.py`): cada
 * parte com a sua fatia sem os centavos, e os que sobram na maior parte (a primeira, no empate).
 */
export function dividirPelaProporcao(valor: number, pesos: number[]): number[] {
  if (!pesos.length) return [];
  // Em BigInt: o produto do valor pelo peso passa do inteiro exato do número em compras grandes.
  const total = BigInt(pesos.reduce((soma, p) => soma + p, 0));
  const valores = pesos.map((p) => Number((BigInt(valor) * BigInt(p)) / total));
  const maior = pesos.reduce((m, p, i) => (p > pesos[m] ? i : m), 0);
  valores[maior] += valor - valores.reduce((soma, v) => soma + v, 0);
  return valores;
}

/** A parte como a tela a edita: o valor como se digita, e o da última é o que falta (`restoDaUltima`). */
export type ParteEmEdicao = Omit<Parte, "valor_centavos"> & { valor: string };

export const emEdicao = (p: Parte): ParteEmEdicao => ({ ...p, valor: comoDigitado(p.valor_centavos) });

/** Uma parte vazia, com o id que nasce no aparelho. */
export const parteNova = (): ParteEmEdicao => ({ id: crypto.randomUUID(), descricao: "", valor: "", categoria_ids: [], tags: [], pessoa: null, item_categoria_id: null });

/** O valor de cada parte: as que se digitam e, na última, o que falta para o total. */
export function valoresDasPartes(partes: ParteEmEdicao[], total: number): number[] {
  const digitados = partes.slice(0, -1).map((p) => emCentavos(p.valor) ?? 0);
  return [...digitados, total - digitados.reduce((soma, v) => soma + v, 0)];
}

/** Por que as partes ainda não salvam; vazio quando estão prontas. No parcelado, `menorParcela` também se divide por elas. */
export function problemaDasPartes(partes: ParteEmEdicao[], total: number, menorParcela?: number): string {
  const valores = valoresDasPartes(partes, total);
  if (partes.slice(0, -1).some((p) => !emCentavos(p.valor) || emCentavos(p.valor)! <= 0)) return "Cada parte precisa de um valor.";
  if (valores[valores.length - 1] <= 0) return "As partes passam do valor da compra.";
  if (partes.some((p) => p.categoria_ids.length === 0)) return "Cada parte precisa de uma categoria.";
  if (menorParcela !== undefined && Math.min(...dividirPelaProporcao(menorParcela, valores)) <= 0) return "A parcela não chega a um centavo por parte.";
  return "";
}

/** As partes como vão ao servidor, com o valor de cada uma. */
export function partesParaSalvar(partes: ParteEmEdicao[], total: number): Parte[] {
  const valores = valoresDasPartes(partes, total);
  return partes.map(({ valor: _, ...p }, i) => ({ ...p, valor_centavos: valores[i] }));
}

type PropsDoEditor = {
  partes: ParteEmEdicao[];
  total: number;
  /** No parcelado, a menor parcela, que também se divide pelas partes. */
  menorParcela?: number;
  categorias: Categoria[];
  pessoas: Pessoa[];
  opcoesDeTags: string[];
  onMudar: (partes: ParteEmEdicao[]) => void;
  /** A penúltima parte saiu: a compra volta a ser uma, com a classificação da que ficou. */
  onJuntar: (fica: ParteEmEdicao) => void;
  /** O aviso de planejamento de cada parte, embaixo dela. */
  avisoDaParte?: (parte: ParteEmEdicao) => ReactNode;
};

/** As partes da compra na tela de lançar: cada uma com descrição, valor, categorias, tags e pessoa. */
export function EditorDePartes(props: PropsDoEditor) {
  const valores = valoresDasPartes(props.partes, props.total);
  const problema = problemaDasPartes(props.partes, props.total, props.menorParcela);

  function mudar(id: string, mudanca: Partial<ParteEmEdicao>) {
    props.onMudar(props.partes.map((p) => (p.id === id ? { ...p, ...mudanca } : p)));
  }

  /** A que era a última passa a ter o valor que tinha (o que faltava); a nova fica com o resto. */
  function acrescentar() {
    const resto = valores[valores.length - 1];
    const antes = props.partes.map((p, i) => (i === props.partes.length - 1 ? { ...p, valor: resto > 0 ? comoDigitado(resto) : "" } : p));
    props.onMudar([...antes, parteNova()]);
  }

  function tirar(id: string) {
    const ficam = props.partes.filter((p) => p.id !== id);
    if (ficam.length === 1) props.onJuntar(ficam[0]);
    else props.onMudar(ficam);
  }

  return (
    <section className="partes" aria-label="Partes da compra">
      <h3>Partes</h3>
      <p className="vazio">Cada parte conta na categoria, na tag e na pessoa dela; a fatura e o mês contam a compra inteira.</p>
      {props.partes.map((p, i) => {
        const ultima = i === props.partes.length - 1;
        const nome = p.descricao || `Parte ${i + 1}`;
        return (
          <div key={p.id} className="parte" role="group" aria-label={`Parte ${i + 1}`}>
            <label>
              Descrição da parte
              <input value={p.descricao} placeholder={`Parte ${i + 1}`} onChange={(e) => mudar(p.id, { descricao: e.target.value })} />
            </label>
            {ultima ? (
              <p className="valor-da-parte" aria-label={`Valor de ${nome}`}>
                {valores[i] > 0 ? formatarCentavos(valores[i]) : "—"} <span className="vazio">o que falta da compra</span>
              </p>
            ) : (
              <label>
                Valor da parte
                <input inputMode="decimal" value={p.valor} placeholder="0,00" onChange={(e) => mudar(p.id, { valor: e.target.value })} />
              </label>
            )}
            <div className="fileira rolavel" role="group" aria-label={`Categorias de ${nome}`}>
              {props.categorias.map((c) => {
                const marcada = p.categoria_ids.includes(c.id);
                return (
                  <button
                    type="button"
                    key={c.id}
                    className={`ficha${marcada ? " marcada" : ""}`}
                    aria-pressed={marcada}
                    onClick={() => mudar(p.id, { categoria_ids: marcada ? p.categoria_ids.filter((x) => x !== c.id) : [...p.categoria_ids, c.id] })}
                  >
                    {c.nome}
                  </button>
                );
              })}
            </div>
            <SeletorDeTags tags={p.tags} opcoes={props.opcoesDeTags} onTags={(tags) => mudar(p.id, { tags })} />
            <div className={`alternancia${props.pessoas.length === 2 ? " tres" : ""}`} role="group" aria-label={`Pessoa de ${nome}`}>
              {[{ id: null, nome: "Conjunto" }, ...props.pessoas].map((pessoa) => (
                <button type="button" key={pessoa.id ?? "conjunto"} className={p.pessoa === pessoa.id ? "" : "secundario"} aria-pressed={p.pessoa === pessoa.id} onClick={() => mudar(p.id, { pessoa: pessoa.id })}>
                  {pessoa.nome}
                </button>
              ))}
            </div>
            {props.avisoDaParte?.(p)}
            <button type="button" className="secundario" aria-label={`Tirar ${nome}`} onClick={() => tirar(p.id)}>
              Tirar a parte
            </button>
          </div>
        );
      })}
      <button type="button" className="secundario" onClick={acrescentar}>
        + Parte
      </button>
      {problema && <p className="erro">{problema}</p>}
    </section>
  );
}
