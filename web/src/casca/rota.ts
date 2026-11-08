import { useEffect, useState } from "react";

export const ABAS = [
  { id: "hoje", nome: "Hoje" },
  { id: "mes", nome: "Mês" },
  { id: "cartoes", nome: "Cartões" },
  { id: "historico", nome: "Histórico" },
  { id: "futuro", nome: "Futuro" },
] as const;

export type Rota = (typeof ABAS)[number]["id"] | "novo" | "estornar" | "credito" | "favorito" | "favoritos" | "conflito" | "parcelamento" | "recorrencia" | "contas-e-categorias" | "configuracoes" | "modelo-do-planejamento" | "busca" | "edicoes-em-lote" | "explorar";

/** A rota vive no hash (`/#/mes`), para o endereço do app nunca mudar e servir qualquer cache. */
export function lerRota(hash: string): { rota: Rota; id?: string; mes?: string; consulta?: string } {
  const [caminho, consulta = ""] = hash.replace(/^#\/?/, "").split("?");
  // `#/busca?<critérios>` abre a busca já filtrada (`enderecoDaBusca`).
  if (caminho === "busca") return { rota: "busca", consulta };
  const [tela, id, mes] = caminho.split("/");
  const conhecida =
    tela === "novo" ||
    (tela === "estornar" && !!id) ||
    (tela === "credito" && !!id) ||
    (tela === "favorito" && !!id) ||
    tela === "favoritos" ||
    (tela === "conflito" && !!id) ||
    (tela === "parcelamento" && !!id) ||
    (tela === "recorrencia" && !!id) ||
    tela === "contas-e-categorias" ||
    tela === "configuracoes" ||
    tela === "modelo-do-planejamento" ||
    tela === "edicoes-em-lote" ||
    tela === "explorar" ||
    ABAS.some((aba) => aba.id === tela);
  // `#/favorito/<id>` abre o novo lançamento já preenchido pelo favorito `<id>`.
  // `#/estornar/<id>` abre o estorno da compra `<id>`.
  // `#/credito/<cartão>` abre o estorno avulso (crédito sem compra) no cartão `<cartão>`.
  // `#/novo/<id>` edita o lançamento de identidade `<id>`; `#/conflito/<id>` decide o conflito dele.
  // `#/parcelamento/<id>` corrige ou exclui o parcelamento `<id>`.
  // `#/recorrencia/<id>` muda, pula ou encerra a recorrência do lançamento `<id>`, a partir dele.
  // `#/cartoes/<cartão>/<AAAA-MM-01>` abre a fatura desse mês do cartão.
  // `#/mes/<AAAA-MM>` abre esse mês na aba Mês; sem o mês, o atual.
  if (conhecida && tela === "mes") return /^\d{4}-(0[1-9]|1[0-2])$/.test(id ?? "") ? { rota: "mes", mes: id } : { rota: "mes" };
  if (conhecida && tela === "cartoes") return id && mes ? { rota: "cartoes", id, mes } : { rota: "cartoes" };
  return conhecida ? { rota: tela as Rota, id: ["novo", "estornar", "credito", "favorito", "conflito", "parcelamento", "recorrencia"].includes(tela) ? id : undefined } : { rota: "hoje" };
}

export function useRota(): ReturnType<typeof lerRota> {
  const [rota, setRota] = useState(() => lerRota(window.location.hash));
  useEffect(() => {
    const aoMudar = () => setRota(lerRota(window.location.hash));
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);
  return rota;
}

/** As telas de lançar: nelas o botão + some (ticket 204). */
export const TELAS_DE_LANCAR: Rota[] = ["novo", "estornar", "credito", "favorito"];

/** Telas que não marcam nada na tela larga: as do Menu da conta, Explorar, as de lançar e as de decidir uma linha. */
const SEM_MARCA_NA_LARGA: Rota[] = ["explorar", "favoritos", "contas-e-categorias", "configuracoes", "conflito", "parcelamento", "recorrencia", ...TELAS_DE_LANCAR];

/** Telas que não marcam nada no celular (ticket 211): as de lançar e as de decidir uma linha. */
const SEM_MARCA_NO_CELULAR: Rota[] = [...TELAS_DE_LANCAR, "conflito", "parcelamento", "recorrencia"];

/**
 * Qual item da barra de navegação fica marcado. Tela larga: a busca e as edições em lote marcam Histórico (ticket 24),
 * o modelo do planejamento marca Mês e as telas do Menu da conta não marcam. Celular (ticket 211): Hoje, Mês e Cartões
 * marcam a si, o modelo marca Mês e toda outra tela marca a grade (Explorar), venha de onde vier.
 */
export function itemMarcado(rota: Rota, larga: boolean): Rota | undefined {
  if (rota === "modelo-do-planejamento") return "mes";
  if (larga) {
    if (rota === "busca" || rota === "edicoes-em-lote") return "historico";
    return SEM_MARCA_NA_LARGA.includes(rota) ? undefined : rota;
  }
  if (rota === "hoje" || rota === "mes" || rota === "cartoes") return rota;
  return SEM_MARCA_NO_CELULAR.includes(rota) ? undefined : "explorar";
}
