import { useState } from "react";
import type { TipoDaEntrada } from "./EscolhaDoTipo";
import { TelaDeLancamento } from "./TelaDeLancamento";
import { TelaDeTransferencia } from "./TelaDeTransferencia";

/** O que o "+ Novo lançamento" e o atalho do ícone abrem: despesa, receita ou transferência. */
export function NovoLancamento() {
  const [tipo, setTipo] = useState<TipoDaEntrada>("despesa");
  // O valor segue ao trocar de tela; o resto é de cada uma.
  const [centavos, setCentavos] = useState(0);
  function trocar(novo: TipoDaEntrada, digitados: number) {
    setTipo(novo);
    setCentavos(digitados);
  }
  if (tipo === "transferencia") return <TelaDeTransferencia centavosIniciais={centavos} onTipo={trocar} />;
  return <TelaDeLancamento tipoInicial={tipo} centavosIniciais={centavos} onTransferencia={(digitados) => trocar("transferencia", digitados)} />;
}
