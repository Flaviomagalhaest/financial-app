import { useState } from "react";
import { api } from "../api/cliente";
import { nomePorId as nome, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { dataPorExtenso } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { Teclado } from "./Teclado";
import { comoNovo, guardarConflito, useCadastro, usePessoas, type Lancamento } from "../dados";

type Ajuste = { centavos: number; data: string; contaId: string };

type Props = {
  /** Os previstos que a leitura da Hoje trouxe; `null` enquanto não há resposta, nem guardada. */
  lancamentos: Lancamento[] | null;
  /** Lê a Hoje de novo, depois de confirmar. */
  aoMudar: () => Promise<void>;
};

/** Previstos a confirmar (atrasados e os dos próximos 7 dias), com "Confirmar" em um toque ou "Ajustar". */
export function ContasDaSemana({ lancamentos, aoMudar }: Props) {
  const { contas, contasECartoes, categorias } = useCadastro();
  const { nomeDe } = usePessoas();
  const [ajustando, setAjustando] = useState<{ id: string } & Ajuste | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  async function confirmar(l: Lancamento, ajuste?: Ajuste) {
    setErro("");
    setEnviando(true);
    // Só o que a pessoa ajustou, sobre a versão que a tela mostrava: o resto fica como o servidor tem.
    const corpo = ajuste && {
      versao: l.versao,
      ...(ajuste.centavos !== l.valor_centavos && { valor_centavos: ajuste.centavos }),
      ...(ajuste.data !== l.data && { data: ajuste.data }),
      ...(ajuste.contaId !== l.conta_id && { conta_id: ajuste.contaId }),
    };
    try {
      const { error, response } = await api.POST("/api/lancamentos/{id}/confirmar", { params: { path: { id: l.id } }, body: corpo ?? {} });
      if (response.status === 409 && error && "campos" in error && ajuste) {
        // Já confirmado com outros valores: a decisão é campo a campo, na tela de conflito.
        const meu = { ...comoNovo(l), situacao: "realizado" as const, valor_centavos: ajuste.centavos, data: ajuste.data, conta_id: ajuste.contaId };
        await guardarConflito(meu, l, error);
        window.location.hash = `#/conflito/${l.id}`;
        return;
      }
      if (response.status === 410) {
        setAjustando(null);
        await aoMudar();
        const exclusao = error && "excluido_por" in error ? error : undefined;
        const quem = exclusao?.por_voce ? "Você" : nomeDe(exclusao?.excluido_por);
        return setErro(`${quem[0].toUpperCase()}${quem.slice(1)} excluiu este lançamento.`);
      }
      if (error) return setErro("O servidor recusou a confirmação.");
      setAjustando(null);
      await aoMudar();
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
                {dataPorExtenso(l.data)} · {nome(contasECartoes, l.conta_id)}
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
