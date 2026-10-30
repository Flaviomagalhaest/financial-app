import { formatarCentavos } from "./dinheiro";
import type { NovoLancamento } from "../dados";

type ComNome = { id: string; nome: string };

export const nomePorId = (lista: ComNome[], id: string) => lista.find((i) => i.id === id)?.nome ?? "?";

/** A descrição, ou as categorias quando não há descrição. */
export function tituloDoLancamento(l: NovoLancamento, categorias: ComNome[]): string {
  return l.descricao || l.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ");
}

export function ValorComSinal({ l }: { l: NovoLancamento }) {
  return (
    <span className={l.tipo === "despesa" ? "despesa" : "receita"}>
      {l.tipo === "despesa" ? "−" : "+"} {formatarCentavos(l.valor_centavos)}
    </span>
  );
}

/** O nome de um favorito (ou sugerido): a descrição, ou as categorias quando não há descrição. */
export function tituloDoFavorito(f: { descricao: string; categoria_ids: string[] }, categorias: ComNome[]): string {
  return f.descricao || f.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ");
}
