import { useEffect, useState } from "react";
import { api } from "../api/cliente";

type Formato = "backup" | "planilha";

function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const atualizar = () => setOnline(navigator.onLine);
    window.addEventListener("online", atualizar);
    window.addEventListener("offline", atualizar);
    return () => {
      window.removeEventListener("online", atualizar);
      window.removeEventListener("offline", atualizar);
    };
  }, []);
  return online;
}

/** Pede o arquivo à API e abre a URL assinada; o S3 responde como download (Content-Disposition). */
async function baixar(formato: Formato) {
  const { data } = await api.POST("/api/exportacoes", { body: { formato } });
  if (!data) throw new Error("exportação recusada");
  window.location.assign(data.url);
}

/** Exportar não vai para a fila: sem internet o botão fica desligado (ADR 0011). */
export function Configuracoes() {
  const online = useOnline();
  const [gerando, setGerando] = useState<Formato | null>(null);
  const [erro, setErro] = useState(false);

  async function exportar(formato: Formato) {
    setGerando(formato);
    setErro(false);
    try {
      await baixar(formato);
    } catch {
      setErro(true);
    } finally {
      setGerando(null);
    }
  }

  const desligado = !online || gerando !== null;
  return (
    <section>
      <h2>Configurações</h2>
      <h3>Exportar</h3>
      <p className="vazio">
        O backup traz todas as tabelas com os ids originais. A planilha traz os lançamentos de todo
        o histórico, com nomes no lugar dos ids, para abrir no Excel ou no Google Planilhas.
      </p>
      <div className="acoes">
        <button disabled={desligado} onClick={() => void exportar("backup")}>
          {gerando === "backup" ? "Gerando…" : "Exportar tudo (backup .zip)"}
        </button>
        <button className="secundario" disabled={desligado} onClick={() => void exportar("planilha")}>
          {gerando === "planilha" ? "Gerando…" : "Exportar lançamentos (planilha .csv)"}
        </button>
      </div>
      {!online && <p className="aviso">Exportar precisa de internet.</p>}
      {erro && (
        <p role="alert" className="erro">
          Não foi possível exportar. Tente de novo.
        </p>
      )}
    </section>
  );
}
