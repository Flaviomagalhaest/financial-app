import { useEffect, useState } from "react";

export const ABAS = [
  { id: "hoje", nome: "Hoje" },
  { id: "mes", nome: "Mês" },
  { id: "cartoes", nome: "Cartões" },
  { id: "historico", nome: "Histórico" },
  { id: "futuro", nome: "Futuro" },
] as const;

export type Rota = (typeof ABAS)[number]["id"] | "novo";

/** A rota vive no hash (`/#/mes`), para o endereço do app nunca mudar e servir qualquer cache. */
export function lerRota(hash: string): Rota {
  const id = hash.replace(/^#\/?/, "");
  return id === "novo" || ABAS.some((aba) => aba.id === id) ? (id as Rota) : "hoje";
}

export function useRota(): Rota {
  const [rota, setRota] = useState(() => lerRota(window.location.hash));
  useEffect(() => {
    const aoMudar = () => setRota(lerRota(window.location.hash));
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);
  return rota;
}
