/** Hoje em São Paulo, como `AAAA-MM-DD`: o dia do casal é o mesmo da API, qualquer que seja o fuso do aparelho. */
export function hoje(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

/** "às 14:32", ou "em 13/10 às 14:32" se não foi hoje. */
export function quando(iso: string): string {
  const em = new Date(iso);
  const hora = em.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });
  const dia = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(em);
  return dia === hoje() ? `às ${hora}` : `em ${dataPorExtenso(dia).slice(0, 5)} às ${hora}`;
}

/** `2026-10-02` vira `02/10/2026`. */
export function dataPorExtenso(iso: string): string {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}
