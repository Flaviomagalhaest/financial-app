import { useEffect, useState } from "react";

export const ABAS = [
  { id: "hoje", nome: "Hoje" },
  { id: "mes", nome: "Mês" },
  { id: "cartoes", nome: "Cartões" },
  { id: "historico", nome: "Histórico" },
  { id: "futuro", nome: "Futuro" },
] as const;

export type Rota = (typeof ABAS)[number]["id"] | "novo" | "estornar" | "favorito" | "favoritos" | "conflito" | "parcelamento" | "recorrencia" | "contas-e-categorias" | "configuracoes" | "modelo-do-planejamento" | "busca" | "edicoes-em-lote";

/** A rota vive no hash (`/#/mes`), para o endereço do app nunca mudar e servir qualquer cache. */
export function lerRota(hash: string): { rota: Rota; id?: string; mes?: string; consulta?: string; parcela?: number } {
  const [caminho, consulta = ""] = hash.replace(/^#\/?/, "").split("?");
  // `#/busca?<critérios>` abre a busca já filtrada (`enderecoDaBusca`).
  if (caminho === "busca") return { rota: "busca", consulta };
  const [tela, id, mes] = caminho.split("/");
  const conhecida =
    tela === "novo" ||
    (tela === "estornar" && !!id) ||
    (tela === "favorito" && !!id) ||
    tela === "favoritos" ||
    (tela === "conflito" && !!id) ||
    (tela === "parcelamento" && !!id) ||
    (tela === "recorrencia" && !!id) ||
    tela === "contas-e-categorias" ||
    tela === "configuracoes" ||
    tela === "modelo-do-planejamento" ||
    tela === "edicoes-em-lote" ||
    ABAS.some((aba) => aba.id === tela);
  // `#/favorito/<id>` abre o novo lançamento já preenchido pelo favorito `<id>`.
  // `#/estornar/<id>` abre o estorno da compra `<id>`.
  // `#/novo/<id>` edita o lançamento de identidade `<id>`; `#/conflito/<id>` decide o conflito dele.
  // `#/parcelamento/<id>` corrige ou exclui o parcelamento `<id>`; `#/parcelamento/<id>/<n>`, aberto
  // da parcela n, pergunta se a mudança vale só para ela, para ela e as próximas ou para todas.
  // `#/recorrencia/<id>` muda, pula ou encerra a recorrência do lançamento `<id>`, a partir dele.
  // `#/cartoes/<cartão>/<AAAA-MM-01>` abre a fatura desse mês do cartão.
  // `#/mes/<AAAA-MM>` abre esse mês na aba Mês; sem o mês, o atual.
  if (conhecida && tela === "mes") return /^\d{4}-(0[1-9]|1[0-2])$/.test(id ?? "") ? { rota: "mes", mes: id } : { rota: "mes" };
  if (conhecida && tela === "parcelamento" && /^[1-9]\d*$/.test(mes ?? "")) return { rota: "parcelamento", id, parcela: Number(mes) };
  if (conhecida && tela === "cartoes") return id && mes ? { rota: "cartoes", id, mes } : { rota: "cartoes" };
  return conhecida ? { rota: tela as Rota, id: ["novo", "estornar", "favorito", "conflito", "parcelamento", "recorrencia"].includes(tela) ? id : undefined } : { rota: "hoje" };
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
