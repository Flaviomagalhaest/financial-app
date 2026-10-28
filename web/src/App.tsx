import { useCallback, useEffect, useState } from "react";
import { api } from "./api/cliente";
import { Casca } from "./casca/Casca";
import { sair, TelaDeLogin, useSessao } from "./login";

type Estado = "verificando" | "no ar" | "sem conexão";

const textos: Record<Estado, string> = {
  verificando: "Verificando…",
  "no ar": "API no ar",
  "sem conexão": "Sem conexão",
};

/** Lançamentos ainda não enviados neste aparelho; a fila chega no ticket 33. */
async function contarNaoEnviados(): Promise<number> {
  return 0;
}

async function sairDaConta() {
  const naoEnviados = await contarNaoEnviados();
  if (
    naoEnviados > 0 &&
    !window.confirm(
      `${naoEnviados === 1 ? "1 lançamento ainda não foi enviado" : `${naoEnviados} lançamentos ainda não foram enviados`}. ` +
        "Se sair agora, eles se perdem. Sair mesmo assim?",
    )
  ) {
    return;
  }
  await sair();
}

function Inicio({ email }: { email: string }) {
  const [estado, setEstado] = useState<Estado>("verificando");

  const verificar = useCallback(async () => {
    setEstado("verificando");
    try {
      const { data } = await api.GET("/api/eu");
      setEstado(data ? "no ar" : "sem conexão");
    } catch {
      setEstado("sem conexão");
    }
  }, []);

  useEffect(() => {
    void verificar();
  }, [verificar]);

  return (
    <Casca
      email={email}
      onSair={() => void sairDaConta()}
      hoje={
        <>
          <p data-testid="estado-da-api">{textos[estado]}</p>
          <button onClick={() => void verificar()}>Verificar de novo</button>
        </>
      }
    />
  );
}

export function App() {
  const sessao = useSessao();
  if (sessao.tipo === "carregando") return null;
  if (sessao.tipo === "fora") return <TelaDeLogin aviso={sessao.aviso} />;
  return <Inicio email={sessao.email} />;
}
