import { formatarCentavos } from "./dinheiro";
import type { Lancamento } from "./useCadastro";

type ComNome = { id: string; nome: string };

export const nomePorId = (lista: ComNome[], id: string) => lista.find((i) => i.id === id)?.nome ?? "?";

/** A descrição, ou as categorias quando não há descrição. */
export function tituloDoLancamento(l: Lancamento, categorias: ComNome[]): string {
  return l.descricao || l.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ");
}

export function ValorComSinal({ l }: { l: Lancamento }) {
  return (
    <span className={l.tipo === "despesa" ? "despesa" : "receita"}>
      {l.tipo === "despesa" ? "−" : "+"} {formatarCentavos(l.valor_centavos)}
    </span>
  );
}
