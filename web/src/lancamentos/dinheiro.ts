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

/** "1.234,56" ou "1234.56" em centavos; vazio é `null` e o que não for número é `undefined`. */
export function emCentavos(texto: string): number | null | undefined {
  const limpo = texto.trim().replace(/\./g, texto.includes(",") ? "" : ".").replace(",", ".");
  if (limpo === "") return null;
  const reais = Number(limpo);
  return Number.isFinite(reais) ? Math.round(reais * 100) : undefined;
}
