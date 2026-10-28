import { useCallback, useEffect, useState } from "react";
import { api } from "../api/cliente";
import type { components } from "../api/schema";

export type Conta = components["schemas"]["Conta"];
export type Categoria = components["schemas"]["Categoria"];
export type Lancamento = components["schemas"]["Lancamento"];

/** Contas e categorias do casal; `carregado` só vira verdadeiro quando o servidor respondeu. */
export function useCadastro() {
  const [contas, setContas] = useState<Conta[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [carregado, setCarregado] = useState(false);

  const recarregar = useCallback(async () => {
    try {
      const [c, k] = await Promise.all([api.GET("/api/contas"), api.GET("/api/categorias")]);
      if (c.data && k.data) {
        setContas(c.data);
        setCategorias(k.data);
        setCarregado(true);
      }
    } catch {
      // Sem internet: segue com o que já tinha; a fila de envio chega no ticket 33.
    }
  }, []);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  return { contas, categorias, carregado, recarregar };
}
