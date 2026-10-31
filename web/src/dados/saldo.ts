// O saldo da conta no aparelho: o guardado do servidor mais o efeito dos não enviados da fila.
// Sem React, como `fila.ts`, para ser a única conta do saldo em qualquer tela.
import { deLancamento, type ItemDaFila, type Lancamento } from "./armazem";

/** O que a conta precisa para a conta do saldo: o saldo guardado e a data de abertura. */
interface ContaComSaldo {
  id: string;
  saldo_centavos: number;
  data_abertura?: string | null;
}

/** O lançamento do jeito que o saldo o vê (o do servidor ou o da tela com a fila por cima). */
type ParaOSaldo = Pick<Lancamento, "tipo" | "situacao" | "valor_centavos" | "data" | "conta_id">;

/** Só o realizado depois do saldo de abertura mexe no saldo, como no servidor. */
function efeito(l: ParaOSaldo | undefined, conta: ContaComSaldo): number {
  if (!l || l.situacao !== "realizado" || l.conta_id !== conta.id) return 0;
  if (conta.data_abertura && l.data <= conta.data_abertura) return 0;
  return l.tipo === "receita" ? l.valor_centavos : -l.valor_centavos;
}

/**
 * As contas guardadas com os lançamentos que acabaram de subir: a leitura delas é de antes do envio,
 * e o item sai da fila na mesma hora, então o saldo guardado passa a contá-los até a próxima leitura
 * (ticket 120). `antes` e `depois` são como a lista guardada tinha e passa a ter cada lançamento.
 */
export function comOsEnviados<C extends ContaComSaldo>(contas: C[], enviados: [antes: ParaOSaldo | undefined, depois: ParaOSaldo | undefined][]): C[] {
  return contas.map((conta) => {
    const mudou = enviados.reduce((soma, [antes, depois]) => soma + efeito(depois, conta) - efeito(antes, conta), 0);
    return mudou === 0 ? conta : { ...conta, saldo_centavos: conta.saldo_centavos + mudou };
  });
}

/**
 * Saldo guardado + (como cada lançamento da fila fica no aparelho − como o servidor o tem):
 * criar soma, excluir tira, editar vale a diferença. `naTela` é a lista do servidor com a fila por
 * cima; só lançamentos entram, porque transferência precisa de internet (ADR 0011). A mudança recusada
 * conta, como na lista, que a mostra com ⏳ até ser corrigida ou descartada; a em conflito ou já excluída pela outra pessoa não mexe no saldo.
 */
export function saldoNoAparelho(
  conta: ContaComSaldo,
  doServidor: Map<string, ParaOSaldo>,
  naTela: Map<string, ParaOSaldo>,
  fila: ItemDaFila[],
): { centavos: number; naoEnviado: boolean } {
  let centavos = conta.saldo_centavos;
  let naoEnviado = false;
  for (const item of fila) {
    if (!deLancamento(item) || item.conflito || item.exclusao) continue;
    const mudou = efeito(naTela.get(item.id), conta) - efeito(doServidor.get(item.id), conta);
    if (mudou === 0) continue;
    centavos += mudou;
    naoEnviado = true;
  }
  return { centavos, naoEnviado };
}
