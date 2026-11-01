// O que o app repete do servidor só para avisar das ocorrências e parcelas que caem antes de hoje
// e não viram lançamento (ticket 87, ADR 0018). Conferido pela tabela `tabelas-de-teste/puladas.json`.
import { maisDias, maisMeses } from "./datas";
import { problemaDa, type RecorrenciaNaFolha } from "./recorrencia";

/**
 * Quantas ocorrências caem antes de `hoje` e por isso não viram lançamento. A conta repete a do
 * servidor (`_gerar_um_lote`: o calendário é contado do início, o fim por `vezes` ou `ate` vale)
 * só para mostrar, como a ADR 0018.
 */
export function ocorrenciasPuladas(r: RecorrenciaNaFolha, inicio: string, hoje: string): number {
  if (problemaDa(r, inicio)) return 0;
  let puladas = 0;
  for (let n = 0; ; n++) {
    if (r.fim === "vezes" && n >= r.vezes) break;
    const dia = r.unidade === "semanas" ? maisDias(inicio, n * r.aCada * 7) : maisMeses(inicio, n * r.aCada);
    if (dia >= hoje || (r.fim === "data" && dia > r.ate)) break;
    puladas++;
  }
  return puladas;
}

/** "1 ocorrência não será lançada: cai antes de hoje.", ou vazio sem puladas. */
export function avisoDasPuladas(puladas: number, termo: { um: string; varios: string }): string {
  if (puladas <= 0) return "";
  return puladas === 1 ? `1 ${termo.um} não será lançada: cai antes de hoje.` : `${puladas} ${termo.varios} não serão lançadas: caem antes de hoje.`;
}

/**
 * Quantas parcelas do boleto vencem antes de `hoje` e não serão lançadas (o cartão gera todas).
 * Repete `parcelas_puladas` do servidor só para mostrar, como a ADR 0018.
 */
export function parcelasPuladas(parcelas: number, data: string, hoje: string, noCartao: boolean): number {
  if (noCartao || !Number.isInteger(parcelas) || parcelas < 2) return 0;
  let puladas = 0;
  while (puladas < parcelas && maisMeses(data, puladas) < hoje) puladas++;
  return puladas;
}
