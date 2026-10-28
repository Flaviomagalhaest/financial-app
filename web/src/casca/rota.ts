import { useEffect, useState } from "react";

export const ABAS = [
  { id: "hoje", nome: "Hoje" },
  { id: "mes", nome: "Mês" },
  { id: "cartoes", nome: "Cartões" },
  { id: "historico", nome: "Histórico" },
  { id: "futuro", nome: "Futuro" },
] as const;

export type Rota = (typeof ABAS)[number]["id"] | "novo" | "contas-e-categorias" | "configuracoes";

/** A rota vive no hash (`/#/mes`), para o endereço do app nunca mudar e servir qualquer cache. */
export function lerRota(hash: string): { rota: Rota; id?: string } {
  const [tela, id] = hash.replace(/^#\/?/, "").split("/");
  const conhecida =
    tela === "novo" || tela === "contas-e-categorias" || tela === "configuracoes" || ABAS.some((aba) => aba.id === tela);
  // `#/novo/<id>` edita o lançamento de identidade `<id>`.
  return conhecida ? { rota: tela as Rota, id: tela === "novo" ? id : undefined } : { rota: "hoje" };
}

export function useRota(): { rota: Rota; id?: string } {
  const [rota, setRota] = useState(() => lerRota(window.location.hash));
  useEffect(() => {
    const aoMudar = () => setRota(lerRota(window.location.hash));
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);
  return rota;
}
