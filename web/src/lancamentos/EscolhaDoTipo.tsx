export type TipoDaEntrada = "despesa" | "receita" | "transferencia";

const NOMES: Record<TipoDaEntrada, string> = { despesa: "Despesa", receita: "Receita", transferencia: "Transferência" };

type Props = { tipo: TipoDaEntrada; onMudar: (tipo: TipoDaEntrada) => void; comTransferencia: boolean };

/** Despesa, receita e, no lançamento novo, transferência, no topo da tela. */
export function EscolhaDoTipo({ tipo, onMudar, comTransferencia }: Props) {
  const tipos: TipoDaEntrada[] = comTransferencia ? ["despesa", "receita", "transferencia"] : ["despesa", "receita"];
  return (
    <div className={`alternancia${comTransferencia ? " tres" : ""}`} role="group" aria-label="Tipo">
      {tipos.map((t) => (
        <button type="button" key={t} className={tipo === t ? "" : "secundario"} aria-pressed={tipo === t} onClick={() => tipo !== t && onMudar(t)}>
          {NOMES[t]}
        </button>
      ))}
    </div>
  );
}
