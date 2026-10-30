import { useEffect, useState } from "react";

export const ABAS = [
  { id: "hoje", nome: "Hoje" },
  { id: "mes", nome: "Mês" },
  { id: "cartoes", nome: "Cartões" },
  { id: "historico", nome: "Histórico" },
  { id: "futuro", nome: "Futuro" },
] as const;

export type Rota = (typeof ABAS)[number]["id"] | "novo" | "estornar" | "favorito" | "favoritos" | "conflito" | "contas-e-categorias" | "configuracoes" | "modelo-do-planejamento";

/** A rota vive no hash (`/#/mes`), para o endereço do app nunca mudar e servir qualquer cache. */
export function lerRota(hash: string): { rota: Rota; id?: string; mes?: string } {
  const [tela, id, mes] = hash.replace(/^#\/?/, "").split("/");
  const conhecida =
    tela === "novo" ||
    (tela === "estornar" && !!id) ||
    (tela === "favorito" && !!id) ||
    tela === "favoritos" ||
    (tela === "conflito" && !!id) ||
    tela === "contas-e-categorias" ||
    tela === "configuracoes" ||
    tela === "modelo-do-planejamento" ||
    ABAS.some((aba) => aba.id === tela);
  // `#/favorito/<id>` abre o novo lançamento já preenchido pelo favorito `<id>`.
  // `#/estornar/<id>` abre o estorno da compra `<id>`.
  // `#/novo/<id>` edita o lançamento de identidade `<id>`; `#/conflito/<id>` decide o conflito dele.
  // `#/cartoes/<cartão>/<AAAA-MM-01>` abre a fatura desse mês do cartão.
  // `#/mes/<AAAA-MM>` abre esse mês na aba Mês; sem o mês, o atual.
  if (conhecida && tela === "mes") return /^\d{4}-(0[1-9]|1[0-2])$/.test(id ?? "") ? { rota: "mes", mes: id } : { rota: "mes" };
  if (conhecida && tela === "cartoes") return id && mes ? { rota: "cartoes", id, mes } : { rota: "cartoes" };
  return conhecida ? { rota: tela as Rota, id: tela === "novo" || tela === "estornar" || tela === "favorito" || tela === "conflito" ? id : undefined } : { rota: "hoje" };
}

export function useRota(): { rota: Rota; id?: string; mes?: string } {
  const [rota, setRota] = useState(() => lerRota(window.location.hash));
  useEffect(() => {
    const aoMudar = () => setRota(lerRota(window.location.hash));
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);
  return rota;
}
