import type { NovaRecorrencia } from "../dados";
import { dataPorExtenso } from "./datas";

/** O "Repete? Recorrente" da folha de detalhes, como a tela o edita. */
export type Repeticao = {
  aCada: number;
  unidade: NovaRecorrencia["unidade"];
  fim: "nunca" | "data" | "vezes";
  /** A última data possível (`AAAA-MM-DD`), quando `fim` é "data". */
  ate: string;
  vezes: number;
  tipoDoValor: NovaRecorrencia["tipo_do_valor"];
  /** Só vale no fixo: o estimado sempre pede confirmação. */
  automatico: boolean;
};

/** Todo mês, sem fim, valor estimado: a luz, o salário. */
export const REPETICAO_PADRAO: Repeticao = { aCada: 1, unidade: "meses", fim: "nunca", ate: "", vezes: 2, tipoDoValor: "estimado", automatico: false };

/** Os campos da regra que a repetição dá, a partir da data da primeira ocorrência. */
export function regraDa(r: Repeticao, inicio: string) {
  return {
    inicio,
    a_cada: r.aCada,
    unidade: r.unidade,
    ate: r.fim === "data" ? r.ate : null,
    vezes: r.fim === "vezes" ? r.vezes : null,
    tipo_do_valor: r.tipoDoValor,
    automatico: r.tipoDoValor === "fixo" && r.automatico,
  };
}

/** O que impede salvar a regra, na voz da tela; `null` quando está tudo certo. */
export function problemaDa(r: Repeticao, inicio: string): string | null {
  if (!Number.isInteger(r.aCada) || r.aCada < 1) return "Diga a cada quantas semanas ou meses.";
  if (r.fim === "vezes" && (!Number.isInteger(r.vezes) || r.vezes < 1)) return "Diga quantas vezes.";
  if (r.fim === "data" && !r.ate) return "Escolha a última data.";
  if (r.fim === "data" && r.ate < inicio) return "A última data vem antes da primeira vez.";
  return null;
}

/** "todo mês", "a cada 2 semanas, 3 vezes", "todo ano, até 10/12/2027, automático". */
export function rotuloDaRecorrencia(regra: Pick<NovaRecorrencia, "a_cada" | "unidade" | "ate" | "vezes" | "automatico">): string {
  const { a_cada: n, unidade } = regra;
  const calendario =
    unidade === "semanas"
      ? n === 1
        ? "toda semana"
        : `a cada ${n} semanas`
      : n % 12 === 0
        ? n === 12
          ? "todo ano"
          : `a cada ${n / 12} anos`
        : n === 1
          ? "todo mês"
          : `a cada ${n} meses`;
  const fim = regra.ate ? `até ${dataPorExtenso(regra.ate)}` : regra.vezes ? (regra.vezes === 1 ? "1 vez" : `${regra.vezes} vezes`) : "";
  return [calendario, fim, regra.automatico ? "automático" : ""].filter(Boolean).join(", ");
}
