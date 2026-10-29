import { useState } from "react";
import type { TipoDaEntrada } from "./EscolhaDoTipo";
import { TelaDeLancamento } from "./TelaDeLancamento";
import { TelaDeTransferencia } from "./TelaDeTransferencia";

/** O que o "+ Novo lançamento" e o atalho do ícone abrem: despesa, receita ou transferência. */
export function NovoLancamento() {
  const [tipo, setTipo] = useState<TipoDaEntrada>("despesa");
  if (tipo === "transferencia") return <TelaDeTransferencia onTipo={setTipo} />;
  return <TelaDeLancamento tipoInicial={tipo} onTransferencia={() => setTipo("transferencia")} />;
}
