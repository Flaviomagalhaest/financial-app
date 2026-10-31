import type { Fatura } from "../dados";
import { mesDepois } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";

export const SITUACAO: Record<Fatura["situacao"], string> = { aberta: "Aberta", fechada: "Fechada", paga: "Paga" };

type Rotulo = "Anterior" | "Antes" | "Atual" | "Próxima" | "Depois";

/**
 * A fatura atual é a primeira aberta; a anterior e a próxima são as vizinhas dela na lista. Se falta
 * uma fatura no meio (mês sem compra), a vizinha não é o mês adjacente e o rótulo diz só "Antes" ou
 * "Depois": "Anterior" e "Próxima" ficam para o mês de fato adjacente. Sem nenhuma aberta, não há
 * atual: a última é a anterior.
 */
export function faturasDaLinha(faturas: Fatura[]): { rotulo: Rotulo; fatura: Fatura }[] {
  const posicao = faturas.findIndex((f) => f.situacao === "aberta");
  const atual = posicao === -1 ? faturas.length : posicao;
  const antes = faturas[atual - 1];
  const depois = faturas[atual + 1];
  // Sem atual, a de referência para "adjacente" é o mês depois da última.
  const referencia = faturas[atual]?.mes ?? (antes && mesDepois(antes.mes, 1));
  const linhas: { rotulo: Rotulo; fatura: Fatura | undefined }[] = [
    { rotulo: antes && referencia && mesDepois(antes.mes, 1) === referencia ? "Anterior" : "Antes", fatura: antes },
    { rotulo: "Atual", fatura: faturas[atual] },
    { rotulo: depois && mesDepois(faturas[atual].mes, 1) === depois.mes ? "Próxima" : "Depois", fatura: depois },
  ];
  return linhas.flatMap((l) => (l.fatura ? [{ rotulo: l.rotulo, fatura: l.fatura }] : []));
}

/** "+ R$ 5,00" ou "− R$ 5,00"; o zero fica sem sinal. */
export function comSinal(centavos: number): string {
  return centavos === 0 ? formatarCentavos(0) : `${centavos > 0 ? "+" : "−"} ${formatarCentavos(Math.abs(centavos))}`;
}
