import type { Futuro } from "../dados";

const NOMES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const POR_EXTENSO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** `2026-04-01` vira `abr`; em janeiro, com o ano (`jan/27`), para a virada se ler no eixo. */
export function mesCurto(mes: string): string {
  const numero = Number(mes.slice(5, 7));
  return numero === 1 ? `jan/${mes.slice(2, 4)}` : NOMES[numero - 1];
}

/** `2026-04-01` vira `abril de 2026`. */
export const mesEAno = (mes: string) => `${POR_EXTENSO[Number(mes.slice(5, 7)) - 1]} de ${mes.slice(0, 4)}`;

const compacto = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

/** Para o eixo: `R$ 12,5 mil`, `R$ 1,2 mi`, `R$ 800`; o negativo leva o sinal. */
export function reaisCompactos(centavos: number): string {
  const reais = centavos / 100;
  const sinal = reais < 0 ? "−" : "";
  const absoluto = Math.abs(reais);
  if (absoluto >= 1_000_000) return `${sinal}R$ ${compacto.format(absoluto / 1_000_000)} mi`;
  if (absoluto >= 1_000) return `${sinal}R$ ${compacto.format(absoluto / 1_000)} mil`;
  return `${sinal}R$ ${Math.round(absoluto)}`;
}

/** Um ponto do gráfico: o fim de um mês, com o valor de cada linha que passa por ele. */
export type Ponto = {
  mes: string;
  realizado: number | null;
  soPrevistos: number | null;
  comPlanejamento: number | null;
};

/**
 * Os 12 meses que passaram e os 12 adiante. As duas linhas do futuro partem do último saldo
 * realizado, para o gráfico não ter um salto entre o passado e a projeção.
 */
export function pontosDaProjecao(futuro: Futuro): Ponto[] {
  const passado: Ponto[] = futuro.passado.map((m) => ({ mes: m.mes, realizado: m.saldo_centavos ?? null, soPrevistos: null, comPlanejamento: null }));
  const ultimo = passado.at(-1);
  if (ultimo && ultimo.realizado != null) {
    ultimo.soPrevistos = ultimo.realizado;
    ultimo.comPlanejamento = ultimo.realizado;
  }
  const adiante: Ponto[] = futuro.proximos_meses.map((m) => ({
    mes: m.mes,
    realizado: null,
    soPrevistos: m.so_previstos_centavos,
    comPlanejamento: m.com_planejamento_centavos,
  }));
  return [...passado, ...adiante];
}

/** Marcas redondas do eixo que cobrem o intervalo, sempre com o zero quando ele está perto. */
export function marcasDoEixo(minimo: number, maximo: number, quantas = 4): number[] {
  if (minimo === maximo) [minimo, maximo] = [minimo - 100_00, maximo + 100_00];
  const bruto = (maximo - minimo) / quantas;
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((x) => x * potencia).find((x) => x >= bruto) ?? 10 * potencia;
  const inicio = Math.floor(minimo / passo) * passo;
  const marcas: number[] = [];
  for (let v = inicio; v <= Math.ceil(maximo / passo) * passo + passo / 2; v += passo) marcas.push(v);
  return marcas;
}
