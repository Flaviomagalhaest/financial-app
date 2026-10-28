import { useCallback, useEffect, useState } from "react";
import { api } from "../api/cliente";
import { nomePorId as nome, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { dataPorExtenso } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { Teclado } from "./Teclado";
import { useCadastro, type Lancamento } from "./useCadastro";

type Ajuste = { centavos: number; data: string; contaId: string };

/** Previstos a confirmar (atrasados e os dos próximos 7 dias), com "Confirmar" em um toque ou "Ajustar". */
export function ContasDaSemana() {
  const { contas, categorias } = useCadastro();
  const [lancamentos, setLancamentos] = useState<Lancamento[] | null>(null);
  const [ajustando, setAjustando] = useState<{ id: string } & Ajuste | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.GET("/api/contas-da-semana");
      if (data) setLancamentos(data.lancamentos);
      else setErro("Não foi possível carregar as contas da semana.");
    } catch {
      setErro("Sem internet: não foi possível carregar as contas da semana.");
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function confirmar(l: Lancamento, ajuste?: Ajuste) {
    setErro("");
    setEnviando(true);
    const corpo = ajuste && { valor_centavos: ajuste.centavos, data: ajuste.data, conta_id: ajuste.contaId };
    try {
      const { error, response } = await api.POST("/api/lancamentos/{id}/confirmar", { params: { path: { id: l.id } }, body: corpo ?? {} });
      if (response.status === 409) {
        setAjustando(null);
        await carregar();
        return setErro("Outra pessoa já confirmou com outros valores; confira no Histórico.");
      }
      if (error) return setErro("O servidor recusou a confirmação.");
      setAjustando(null);
      await carregar();
    } catch {
      // A confirmação sem internet entra na fila do ticket 33.
      setErro("Sem internet: confirmar ainda precisa de internet.");
    } finally {
      setEnviando(false);
    }
  }

  const quantas = lancamentos?.length ?? 0;

  return (
    <section aria-labelledby="contas-da-semana" className="contas-da-semana">
      <h3 id="contas-da-semana">Contas da semana</h3>
      {lancamentos && (
        <p data-testid="quantas-contas">
          {quantas === 0
            ? "Nenhuma conta da semana para confirmar."
            : `${quantas} ${quantas === 1 ? "conta" : "contas"} da semana para confirmar`}
        </p>
      )}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <ul className="lista">
        {lancamentos?.map((l) => {
          const titulo = tituloDoLancamento(l, categorias);
          const ajuste = ajustando?.id === l.id ? ajustando : null;
          return (
            <li key={l.id}>
              <div>
                <strong>{titulo}</strong>
                <ValorComSinal l={l} />
              </div>
              <p className="vazio">
                {l.atrasado && <span className="selo-atrasado">atrasado</span>}
                {dataPorExtenso(l.data)} · {nome(contas, l.conta_id)}
              </p>
              {ajuste ? (
                <div className="ajuste" role="group" aria-label={`Ajuste de ${titulo}`}>
                  <p className="valor" data-testid="valor" aria-live="polite">
                    {formatarCentavos(ajuste.centavos)}
                  </p>
                  <Teclado centavos={ajuste.centavos} onMudar={(centavos) => setAjustando({ ...ajuste, centavos })} />
                  <label htmlFor={`data-${l.id}`}>Data</label>
                  <input id={`data-${l.id}`} type="date" value={ajuste.data} required onChange={(e) => setAjustando({ ...ajuste, data: e.target.value })} />
                  <div className="fileira" role="group" aria-label="Conta">
                    {contas.map((c) => (
                      <button type="button" key={c.id} className={`ficha${c.id === ajuste.contaId ? " marcada" : ""}`} aria-pressed={c.id === ajuste.contaId} onClick={() => setAjustando({ ...ajuste, contaId: c.id })}>
                        {c.nome}
                      </button>
                    ))}
                  </div>
                  <div className="acoes">
                    <button type="button" disabled={enviando || ajuste.centavos === 0 || !ajuste.data} onClick={() => void confirmar(l, ajuste)}>
                      Confirmar com ajuste
                    </button>
                    <button type="button" className="secundario" onClick={() => setAjustando(null)}>
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="acoes">
                  <button type="button" disabled={enviando} aria-label={`Confirmar ${titulo}`} onClick={() => void confirmar(l)}>
                    Confirmar
                  </button>
                  <button
                    type="button"
                    className="secundario"
                    aria-label={`Ajustar ${titulo}`}
                    onClick={() => setAjustando({ id: l.id, centavos: l.valor_centavos, data: l.data, contaId: l.conta_id })}
                  >
                    Ajustar
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
