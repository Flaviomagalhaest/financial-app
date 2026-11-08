import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api/cliente";
import { Casca } from "./casca/Casca";
import { apagarDadosDoAparelho, contarNaoEnviados, iniciarEnvioAutomatico } from "./dados";
import { sair, TelaDeLogin, useSessao } from "./login";

type Estado = "verificando" | "no ar" | "sem conexão" | "sessão vencida" | "api fora";

const textos: Record<Estado, string> = {
  verificando: "Verificando…",
  "no ar": "API no ar",
  "sem conexão": "Sem conexão",
  "sessão vencida": "Sessão vencida",
  "api fora": "API ocupada ou fora do ar",
};

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
  // Sair apaga do aparelho a fila e as respostas guardadas, que são do casal.
  await apagarDadosDoAparelho().catch(() => undefined);
  await sair();
}

function Inicio({ email }: { email: string }) {
  const [estado, setEstado] = useState<Estado>("verificando");

  const emAndamento = useRef(false);

  // `silenciosa`: as verificações automáticas não trocam o texto por "Verificando…".
  const verificar = useCallback(async (silenciosa = false) => {
    if (emAndamento.current) return;
    emAndamento.current = true;
    if (!silenciosa) setEstado("verificando");
    try {
      const { data, response } = await api.GET("/api/eu");
      if (data) setEstado("no ar");
      else if (response.status === 401) setEstado("sessão vencida");
      else setEstado("api fora");
    } catch {
      // Sem resposta: sem rede ou tempo-limite.
      setEstado("sem conexão");
    } finally {
      emAndamento.current = false;
    }
  }, []);

  useEffect(() => {
    void verificar();
    // Uma falha passageira não pode deixar a aba com o aviso para sempre.
    const aoVoltar = () => void verificar(true);
    const aoVisivel = () => {
      if (document.visibilityState === "visible") aoVoltar();
    };
    window.addEventListener("online", aoVoltar);
    window.addEventListener("focus", aoVoltar);
    document.addEventListener("visibilitychange", aoVisivel);
    return () => {
      window.removeEventListener("online", aoVoltar);
      window.removeEventListener("focus", aoVoltar);
      document.removeEventListener("visibilitychange", aoVisivel);
    };
  }, [verificar]);

  useEffect(() => iniciarEnvioAutomatico(), []);

  return (
    <Casca
      email={email}
      onSair={() => void sairDaConta()}
      hoje={
        <p className="estado-da-api">
          <span data-testid="estado-da-api" data-estado={estado}>
            {textos[estado]}
          </span>
          <button type="button" onClick={() => void verificar()}>
            Verificar de novo
          </button>
          {estado === "sessão vencida" && (
            <button type="button" onClick={() => void sairDaConta()}>
              Entrar de novo
            </button>
          )}
        </p>
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
