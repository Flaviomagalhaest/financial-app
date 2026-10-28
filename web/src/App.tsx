import { useCallback, useEffect, useState } from "react";
import { api } from "./api/cliente";

type Estado = "verificando" | "no ar" | "sem conexão";

const textos: Record<Estado, string> = {
  verificando: "Verificando…",
  "no ar": "API no ar",
  "sem conexão": "Sem conexão",
};

export function App() {
  const [estado, setEstado] = useState<Estado>("verificando");

  const verificar = useCallback(async () => {
    setEstado("verificando");
    try {
      const { data } = await api.GET("/api/saude");
      setEstado(data?.status === "ok" ? "no ar" : "sem conexão");
    } catch {
      setEstado("sem conexão");
    }
  }, []);

  useEffect(() => {
    void verificar();
  }, [verificar]);

  return (
    <main>
      <h1>Financial App</h1>
      <p data-testid="estado-da-api">{textos[estado]}</p>
      <button onClick={() => void verificar()}>Verificar de novo</button>
    </main>
  );
}
