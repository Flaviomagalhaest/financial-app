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
