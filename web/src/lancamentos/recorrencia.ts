import type { AlteracaoDeRecorrencia, NovaRecorrencia } from "../dados";
import { dataPorExtenso, maisDias, maisMeses } from "./datas";

/** O "Repete? Recorrente" da folha de detalhes, como a tela o edita. */
export type RecorrenciaNaFolha = {
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
export const RECORRENCIA_PADRAO: RecorrenciaNaFolha = { aCada: 1, unidade: "meses", fim: "nunca", ate: "", vezes: 2, tipoDoValor: "estimado", automatico: false };

/** Os campos da regra que a folha dá, a partir da data da primeira ocorrência. */
export function regraDa(r: RecorrenciaNaFolha, inicio: string) {
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
export function problemaDa(r: RecorrenciaNaFolha, inicio: string): string | null {
  if (!Number.isInteger(r.aCada) || r.aCada < 1) return "Diga a cada quantas semanas ou meses.";
  if (r.fim === "vezes" && (!Number.isInteger(r.vezes) || r.vezes < 1)) return "Diga quantas vezes.";
  if (r.fim === "data" && !r.ate) return "Escolha a última data.";
  if (r.fim === "data" && r.ate < inicio) return "A última data vem antes da primeira vez.";
  return null;
}

/** "toda semana", "a cada 3 meses", "todo ano": anual é a cada 12 meses. */
function calendario(n: number, unidade: NovaRecorrencia["unidade"]): string {
  if (unidade === "semanas") return n === 1 ? "toda semana" : `a cada ${n} semanas`;
  if (n === 12) return "todo ano";
  if (n % 12 === 0) return `a cada ${n / 12} anos`;
  return n === 1 ? "todo mês" : `a cada ${n} meses`;
}

/** "todo mês", "a cada 2 semanas, 3 vezes", "todo ano, até 10/12/2027, automático". */
export function rotuloDaRecorrencia(regra: Pick<NovaRecorrencia, "a_cada" | "unidade" | "ate" | "vezes" | "automatico">): string {
  const fim = regra.ate ? `até ${dataPorExtenso(regra.ate)}` : regra.vezes ? (regra.vezes === 1 ? "1 vez" : `${regra.vezes} vezes`) : "";
  return [calendario(regra.a_cada, regra.unidade), fim, regra.automatico ? "automático" : ""].filter(Boolean).join(", ");
}

/** Os mesmos nomes do motivo da recusa do servidor (`_NOMES_DOS_CAMPOS` em `recorrencias.py`). */
const NOMES_DOS_CAMPOS: Partial<Record<keyof AlteracaoDeRecorrencia, string>> = {
  descricao: "descrição",
  valor_centavos: "valor",
  tipo_do_valor: "fixo ou estimado",
  automatico: "automático",
  conta_id: "conta",
  categoria_ids: "categorias",
  tags: "tags",
  pessoa: "pessoa",
  a_cada: "calendário",
  unidade: "calendário",
  inicio: "calendário",
};

/** "valor, descrição", "termina na 3ª vez", "termina em 10/12/2026": o que a mudança não enviada faz. */
export function oQueMuda(alteracao: AlteracaoDeRecorrencia): string {
  const campos = Object.keys(alteracao).flatMap((campo) => NOMES_DOS_CAMPOS[campo as keyof AlteracaoDeRecorrencia] ?? []);
  const partes = [...new Set(campos)];
  if (alteracao.vezes) partes.push(`termina na ${alteracao.vezes}ª vez`);
  else if (alteracao.ate) partes.push(`termina em ${dataPorExtenso(alteracao.ate)}`);
  else if ("ate" in alteracao || "vezes" in alteracao) partes.push("sem fim");
  return partes.join(", ");
}

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

/** "1 ocorrência não será lançada: cai antes de hoje.", ou `null` sem puladas. */
export function avisoDasPuladas(puladas: number, termo: { um: string; varios: string }): string | null {
  if (puladas <= 0) return null;
  return puladas === 1 ? `1 ${termo.um} não será lançada: cai antes de hoje.` : `${puladas} ${termo.varios} não serão lançadas: caem antes de hoje.`;
}
