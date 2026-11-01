const formato = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

/** Centavos inteiros viram "R$ 1.203,00"; o espaço do Intl é o não separável, trocado por comum. */
export function formatarCentavos(centavos: number): string {
  return formato.format(centavos / 100).replace(/\s/g, " ");
}

/** Maior valor que o teclado aceita: R$ 99.999.999,99. */
const MAXIMO = 9_999_999_999;

/** Digita pela direita: "5" ou "00" entram como centavos; passar do máximo ignora a tecla. */
export function digitar(centavos: number, tecla: string): number {
  const novo = centavos * 10 ** tecla.length + Number(tecla);
  return novo > MAXIMO ? centavos : novo;
}

export function apagar(centavos: number): number {
  return Math.floor(centavos / 10);
}

/**
 * O total dividido por igual em parcelas, com os centavos que sobram na 1ª, como o servidor divide
 * (`valor_da_parcela`). Só para mostrar e para o aviso de planejamento; a tabela
 * `tabelas-de-teste/divisao-das-parcelas.json` prende as duas contas juntas (ADR 0018).
 */
export function dividirEmParcelas(total: number, parcelas: number): { primeira: number; outras: number } {
  const outras = Math.floor(total / parcelas);
  return { primeira: outras + (total % parcelas), outras };
}

/**
 * As partes divididas de novo para um valor, na proporção que têm, como o servidor divide
 * (`partes.redividir`): cada uma com a parte inteira da conta, e os centavos que sobram na maior (a
 * primeira, no empate). `null` quando alguma ficaria sem nenhum centavo, que o servidor recusa. Só
 * para mostrar a ocorrência e a regra antes da resposta; a tabela
 * `tabelas-de-teste/redivisao-das-partes.json` prende as duas contas juntas (ADR 0018).
 */
export function redividir<P extends { valor_centavos: number }>(partes: P[], valor: number): P[] | null {
  const pesos = partes.map((p) => BigInt(p.valor_centavos));
  const total = pesos.reduce((soma, peso) => soma + peso, 0n);
  // Em BigInt: o valor vezes o peso passa do inteiro exato do JavaScript nos valores grandes.
  const valores = pesos.map((peso) => Number((BigInt(valor) * peso) / total));
  const maior = partes.reduce((m, p, i) => (p.valor_centavos > partes[m].valor_centavos ? i : m), 0);
  valores[maior] += valor - valores.reduce((soma, v) => soma + v, 0);
  if (valores.some((v) => v <= 0)) return null;
  return partes.map((p, i) => ({ ...p, valor_centavos: valores[i] }));
}

/** "1.234,56" ou "1234.56" em centavos; vazio é `null` e o que não for número é `undefined`. */
export function emCentavos(texto: string): number | null | undefined {
  const limpo = texto.trim().replace(/\./g, texto.includes(",") ? "" : ".").replace(",", ".");
  if (limpo === "") return null;
  const reais = Number(limpo);
  return Number.isFinite(reais) ? Math.round(reais * 100) : undefined;
}

/** "1.200,00": o valor como se digita no campo, sem o "R$". */
export const comoDigitado = (centavos: number) => (centavos / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
