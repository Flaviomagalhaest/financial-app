/** Hoje em São Paulo, como `AAAA-MM-DD`: o dia do casal é o mesmo da API, qualquer que seja o fuso do aparelho. */
export function hoje(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

/** `2026-10-02` vira `02/10/2026`. */
export function dataPorExtenso(iso: string): string {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}
