import type { LeituraDoMes } from "../dados";
import { mesDepois } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";

const NOMES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** `2026-10` vira "outubro de 2026". */
export function nomeDoMes(mes: string): string {
  return `${NOMES[Number(mes.slice(5, 7)) - 1]} de ${mes.slice(0, 4)}`;
}

/** `2026-10` vira "out/26", para o cabeçalho estreito da comparação. */
export function mesCurto(mes: string): string {
  return `${NOMES[Number(mes.slice(5, 7)) - 1].slice(0, 3)}/${mes.slice(2, 4)}`;
}

/** O mês `deslocamento` meses depois de `mes`, como `AAAA-MM`. */
export function mesVizinho(mes: string, deslocamento: number): string {
  return mesDepois(`${mes}-01`, deslocamento).slice(0, 7);
}

/** "▲ 25%" ou "▼ 20%" do antigo para o atual; "novo" quando antes não havia, "—" quando nunca houve. */
export function variacao(atual: number, antigo: number): string {
  if (!antigo) return atual ? "novo" : "—";
  const porcentagem = Math.round(((atual - antigo) * 100) / Math.abs(antigo));
  return porcentagem === 0 ? "= 0%" : `${porcentagem > 0 ? "▲" : "▼"} ${Math.abs(porcentagem)}%`;
}

const capitular = (texto: string) => texto.charAt(0).toUpperCase() + texto.slice(1);

/** Junta "a, b e c". */
function lista(itens: string[]): string {
  return itens.length < 2 ? (itens[0] ?? "") : `${itens.slice(0, -1).join(", ")} e ${itens.at(-1)}`;
}

function frasesDaVariacao(porcentagem: number | null | undefined, outro: string): string {
  if (porcentagem === null || porcentagem === undefined) return `${capitular(outro)} não teve despesas para comparar.`;
  if (porcentagem === 0) return `Em relação a ${outro}, as despesas ficaram iguais.`;
  return `Em relação a ${outro}, as despesas ${porcentagem > 0 ? "subiram" : "caíram"} ${Math.abs(porcentagem)}%.`;
}

/** O fechamento do mês (glossário) em texto corrido, um parágrafo por assunto. */
export function textoDoFechamento(leitura: LeituraDoMes, nomeDaCategoria: (id: string) => string): string[] {
  const f = leitura.fechamento;
  if (!f) return [];
  const dinheiro = formatarCentavos;
  const sobra =
    f.sobra_centavos >= 0
      ? `Sobraram ${dinheiro(f.sobra_centavos)}${f.sobra_percentual !== null ? ` (${f.sobra_percentual}% das receitas)` : ""}`
      : `Faltaram ${dinheiro(-f.sobra_centavos)}: as despesas passaram das receitas`;
  const guardado = f.guardado_centavos ? `, e ${dinheiro(f.guardado_centavos)} foram guardados` : "";
  const paragrafos = [
    `${capitular(nomeDoMes(leitura.mes))} fechou com ${dinheiro(f.receitas_centavos)} de receitas e ${dinheiro(f.despesas_centavos)} de despesas. ${sobra}${guardado}.`,
  ];
  if (f.itens_de_despesa > 0) {
    const dentro = f.itens_de_despesa - f.itens_acima.length;
    const contagem = `${dentro} de ${f.itens_de_despesa} ${f.itens_de_despesa === 1 ? "item ficou" : "itens ficaram"} dentro`;
    paragrafos.push(
      f.itens_acima.length
        ? `Passou do planejado em ${lista(f.itens_acima.map((i) => `${nomeDaCategoria(i.categoria_id)} (+${dinheiro(i.passou_centavos)})`))}; ${contagem}.`
        : `Nenhum item passou do planejado; ${contagem}.`,
    );
  } else {
    paragrafos.push("O mês não teve planejamento de despesas.");
  }
  paragrafos.push(
    `${frasesDaVariacao(f.variacao_anterior_percentual, nomeDoMes(leitura.comparacao.anterior))} ${frasesDaVariacao(f.variacao_ano_passado_percentual, nomeDoMes(leitura.comparacao.ano_passado))}`,
  );
  if (f.previstos > 0) {
    paragrafos.push(`${f.previstos === 1 ? "1 previsto ficou sem confirmar e não entra" : `${f.previstos} previstos ficaram sem confirmar e não entram`} nas contas acima.`);
  }
  return paragrafos;
}
