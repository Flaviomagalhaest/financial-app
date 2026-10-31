import type { Fatura } from "../dados";
import { formatarCentavos } from "../lancamentos/dinheiro";

export const SITUACAO: Record<Fatura["situacao"], string> = { aberta: "Aberta", fechada: "Fechada", paga: "Paga" };

/** `2026-11-01` vira `11/2026`. */
export const mesPorExtenso = (mes: string) => `${mes.slice(5, 7)}/${mes.slice(0, 4)}`;

/**
 * A fatura atual é a primeira aberta; a anterior e a próxima são as vizinhas dela. Sem nenhuma
 * aberta, não há atual: a última é a anterior.
 */
export function faturasDaLinha(faturas: Fatura[]): { rotulo: "Anterior" | "Atual" | "Próxima"; fatura: Fatura }[] {
  const posicao = faturas.findIndex((f) => f.situacao === "aberta");
  const atual = posicao === -1 ? faturas.length : posicao;
  return [
    { rotulo: "Anterior" as const, fatura: faturas[atual - 1] },
    { rotulo: "Atual" as const, fatura: faturas[atual] },
    { rotulo: "Próxima" as const, fatura: faturas[atual + 1] },
  ].filter((linha) => linha.fatura);
}

/** "+ R$ 5,00" ou "− R$ 5,00"; o zero fica sem sinal. */
export function comSinal(centavos: number): string {
  return centavos === 0 ? formatarCentavos(0) : `${centavos > 0 ? "+" : "−"} ${formatarCentavos(Math.abs(centavos))}`;
}
