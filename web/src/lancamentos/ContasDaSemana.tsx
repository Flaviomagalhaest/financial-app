import { useState } from "react";
import { nomePorId as nome, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { dataPorExtenso } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { Teclado } from "./Teclado";
import { confirmarPrevisto, confirmarTransferencia, useCadastro, useConexao, usePessoas, type Ajustes, type LancamentoNaTela, type Transferencia } from "../dados";

type Props = {
  /** As contas da semana da leitura da Hoje, com a fila por cima; `null` enquanto não há resposta, nem guardada. */
  lancamentos: LancamentoNaTela[] | null;
  /** As transferências previstas da leitura da Hoje; confirmar precisa de internet (ADR 0011). */
  transferencias?: Transferencia[] | null;
};

/** A transferência prevista: "Confirmar" em um toque ou "Ajustar" valor e data, só com internet. */
function ContaDeTransferencia({ t, onConfirmada }: { t: Transferencia; onConfirmada: () => void }) {
  const { contasECartoes } = useCadastro();
  const online = useConexao();
  const [ajuste, setAjuste] = useState<{ valor_centavos: number; data: string } | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const titulo = t.descricao || (t.fatura_mes ? "Pagamento de fatura" : "Transferência");

  async function confirmar(ajustes?: { valor_centavos: number; data: string }) {
    setErro("");
    setEnviando(true);
    const recusa = await confirmarTransferencia(t.id, ajustes);
    setEnviando(false);
    if (recusa) setErro(`Não foi possível confirmar: ${recusa}.`);
    else onConfirmada();
  }

  return (
    <li>
      <div>
        <strong>{titulo}</strong>
        <span>⇄ {formatarCentavos(t.valor_centavos)}</span>
      </div>
      <p className="vazio">
        {t.atrasado && <span className="selo-atrasado">atrasado</span>}
        {dataPorExtenso(t.data)} · {nome(contasECartoes, t.conta_origem_id)} → {nome(contasECartoes, t.conta_destino_id)}
      </p>
      {!online && <p className="vazio">Sem internet: a transferência precisa de internet para confirmar.</p>}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      {ajuste ? (
        <div className="ajuste" role="group" aria-label={`Ajuste de ${titulo}`}>
          <p className="valor" data-testid="valor" aria-live="polite">
            {formatarCentavos(ajuste.valor_centavos)}
          </p>
          <Teclado centavos={ajuste.valor_centavos} onMudar={(valor_centavos) => setAjuste({ ...ajuste, valor_centavos })} />
          <label htmlFor={`data-${t.id}`}>Data</label>
          <input id={`data-${t.id}`} type="date" value={ajuste.data} required onChange={(e) => setAjuste({ ...ajuste, data: e.target.value })} />
          <div className="acoes">
            <button type="button" disabled={!online || enviando || ajuste.valor_centavos === 0 || !ajuste.data} onClick={() => void confirmar(ajuste)}>
              Confirmar com ajuste
            </button>
            <button type="button" className="secundario" onClick={() => setAjuste(null)}>
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <div className="acoes">
          <button type="button" disabled={!online || enviando} aria-label={`Confirmar ${titulo}`} onClick={() => void confirmar()}>
            Confirmar
          </button>
          <button type="button" className="secundario" aria-label={`Ajustar ${titulo}`} onClick={() => setAjuste({ valor_centavos: t.valor_centavos, data: t.data })}>
            Ajustar
          </button>
        </div>
      )}
    </li>
  );
}

/**
 * Previstos a confirmar (atrasados e os dos próximos 7 dias), com "Confirmar" em um toque ou
 * "Ajustar". A confirmação vai pela fila: sem internet, o previsto sai daqui e fica realizado ⏳.
 */
export function ContasDaSemana({ lancamentos, transferencias }: Props) {
  const { contas, contasECartoes, categorias } = useCadastro();
  const { nomeDe } = usePessoas();
  const [ajustando, setAjustando] = useState<{ id: string } & Required<Ajustes> | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  async function confirmar(l: LancamentoNaTela, ajustes?: Ajustes) {
    setErro("");
    setEnviando(true);
    try {
      const naFila = await confirmarPrevisto(l, ajustes);
      // O envio pode terminar depois de a pessoa abrir o ajuste de outra conta: esse fica aberto.
      setAjustando((aberto) => (aberto?.id === l.id ? null : aberto));
      // Já confirmado com outros valores: a decisão é campo a campo, na tela de conflito.
      if (naFila?.conflito) window.location.hash = `#/conflito/${l.id}`;
      else if (naFila?.exclusao) {
        const { por_voce, excluido_por } = naFila.exclusao;
        const quem = por_voce ? "Você" : nomeDe(excluido_por);
        setErro(`${quem[0].toUpperCase()}${quem.slice(1)} excluiu este lançamento.`);
      }
    } catch {
      setErro("Não foi possível guardar a confirmação no aparelho.");
    } finally {
      setEnviando(false);
    }
  }

  const quantas = (lancamentos?.length ?? 0) + (transferencias?.length ?? 0);

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
        {transferencias?.map((t) => (
          <ContaDeTransferencia key={t.id} t={t} onConfirmada={() => setErro("")} />
        ))}
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
              {/* A confirmação recusada fica aqui para confirmar de novo, com outra conta, por exemplo. */}
              {l.recusa && <p className="erro">⏳ não enviado: {l.recusa}</p>}
              {l.conflito ? (
                // A mudança do aparelho espera a decisão: confirmar por cima a perderia.
                <div className="acoes">
                  <p className="erro">⚠ conflito: sua mudança espera decisão</p>
                  <a className="botao" href={`#/conflito/${l.id}`} aria-label={`Decidir ${titulo}`}>
                    Decidir
                  </a>
                </div>
              ) : ajuste ? (
                <div className="ajuste" role="group" aria-label={`Ajuste de ${titulo}`}>
                  <p className="valor" data-testid="valor" aria-live="polite">
                    {formatarCentavos(ajuste.valor_centavos)}
                  </p>
                  <Teclado centavos={ajuste.valor_centavos} onMudar={(valor_centavos) => setAjustando({ ...ajuste, valor_centavos })} />
                  <label htmlFor={`data-${l.id}`}>Data</label>
                  <input id={`data-${l.id}`} type="date" value={ajuste.data} required onChange={(e) => setAjustando({ ...ajuste, data: e.target.value })} />
                  <div className="fileira" role="group" aria-label="Conta">
                    {contas.map((c) => (
                      <button type="button" key={c.id} className={`ficha${c.id === ajuste.conta_id ? " marcada" : ""}`} aria-pressed={c.id === ajuste.conta_id} onClick={() => setAjustando({ ...ajuste, conta_id: c.id })}>
                        {c.nome}
                      </button>
                    ))}
                  </div>
                  <div className="acoes">
                    <button
                      type="button"
                      disabled={enviando || ajuste.valor_centavos === 0 || !ajuste.data}
                      onClick={() => {
                        const { id: _, ...ajustes } = ajuste;
                        void confirmar(l, ajustes);
                      }}
                    >
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
                    onClick={() => setAjustando({ id: l.id, valor_centavos: l.valor_centavos, data: l.data, conta_id: l.conta_id })}
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
