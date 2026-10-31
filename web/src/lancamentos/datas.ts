/** O dia de um instante em São Paulo, como `AAAA-MM-DD`: o dia do casal é o mesmo da API, qualquer que seja o fuso do aparelho. */
export function diaEmSaoPaulo(em: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(em);
}

/** Hoje em São Paulo, como `AAAA-MM-DD`. */
export function hoje(): string {
  return diaEmSaoPaulo(new Date());
}

/** "às 14:32", ou "em 13/10 às 14:32" se não foi hoje. */
export function quando(iso: string): string {
  const em = new Date(iso);
  const hora = em.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });
  const dia = diaEmSaoPaulo(em);
  return dia === hoje() ? `às ${hora}` : `em ${dataPorExtenso(dia).slice(0, 5)} às ${hora}`;
}

/** `2026-10-02` vira `02/10/2026`. */
export function dataPorExtenso(iso: string): string {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

/** `2026-11-01` vira `11/2026`. */
export const mesPorExtenso = (mes: string) => `${mes.slice(5, 7)}/${mes.slice(0, 4)}`;

/** `2026-11-01` vira "fatura de 11/2026". */
export function rotuloDaFatura(mes: string): string {
  return `fatura de ${mesPorExtenso(mes)}`;
}

/** O primeiro dia do mês `deslocamento` meses depois do de `iso`, como `AAAA-MM-01`. */
export function mesDepois(iso: string, deslocamento: number): string {
  const [ano, mes] = iso.split("-").map(Number);
  return new Date(Date.UTC(ano, mes - 1 + deslocamento, 1)).toISOString().slice(0, 10);
}

/** O dia antes de `iso` (`AAAA-MM-DD`), sem passar pelo fuso do aparelho. */
export function diaAnterior(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return new Date(Date.UTC(ano, mes - 1, dia - 1)).toISOString().slice(0, 10);
}

/** "hoje", "ontem" ou `02/10/2026`. */
export function rotuloDaData(iso: string): string {
  const dia = hoje();
  if (iso === dia) return "hoje";
  if (iso === diaAnterior(dia)) return "ontem";
  return dataPorExtenso(iso);
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** `2026-10-01` (ou `2026-10`) vira "out/26". */
export function rotuloDoMes(mes: string): string {
  return `${MESES[Number(mes.slice(5, 7)) - 1]}/${mes.slice(2, 4)}`;
}
