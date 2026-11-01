import { config } from "../config";
import type { AvisoDeRealizadas, NovoParcelamento } from "../dados";
import { numeroDaParcela } from "./apresentacao";
import { dataPorExtenso } from "./datas";
import { dividirEmParcelas, formatarCentavos } from "./dinheiro";

/** Sem juros, o total se divide pelas parcelas; com juros, cada parcela vale o digitado. */
export type ValorDigitado = "total" | "parcela";

/** O "Repete? Parcelado" da folha de detalhes, como a tela o edita; o valor do teclado é o total ou o da parcela. */
export type ParcelamentoNaFolha = {
  parcelas: number;
  valorDigitado: ValorDigitado;
  /** Só fora do cartão: no cartão o parcelamento já é automático, e o servidor recusa o contrário. */
  automatico: boolean;
};

/** Duas parcelas, o total digitado, e o boleto pede confirmação de cada parcela. */
export const PARCELAMENTO_PADRAO: ParcelamentoNaFolha = { parcelas: 2, valorDigitado: "total", automatico: false };

type Valores = Pick<NovoParcelamento, "parcelas" | "valor_total_centavos" | "valor_da_parcela_centavos" | "automatico">;

/** Os campos do parcelamento que a folha dá; no cartão, `automatico` fica de fora e o servidor o liga. */
export function pedidoDo(p: ParcelamentoNaFolha, centavos: number, noCartao: boolean): Valores {
  return {
    parcelas: p.parcelas,
    ...(p.valorDigitado === "total" ? { valor_total_centavos: centavos } : { valor_da_parcela_centavos: centavos }),
    ...(!noCartao && { automatico: p.automatico }),
  };
}

/** O que impede salvar o parcelamento, na voz da tela; `null` quando está tudo certo. */
export function problemaDo(p: ParcelamentoNaFolha, centavos: number): string | null {
  if (!Number.isInteger(p.parcelas) || p.parcelas < 2) return "Diga em quantas parcelas: duas ou mais.";
  if (p.parcelas > config.maximoDeParcelas) return `No máximo ${config.maximoDeParcelas} parcelas.`;
  if (p.valorDigitado === "total" && centavos > 0 && centavos < p.parcelas) return "O total não chega a um centavo por parcela.";
  return null;
}

/** O total do pedido e como ele se divide pelas parcelas. */
export function divisao({ parcelas, valor_total_centavos, valor_da_parcela_centavos }: Valores) {
  const total = valor_total_centavos ?? (valor_da_parcela_centavos ?? 0) * parcelas;
  return { total, ...dividirEmParcelas(total, parcelas) };
}

/** "10x de R$ 99,90", "3x: R$ 33,34 na 1ª e R$ 33,33 nas outras", com o total quando ele não foi o digitado. */
export function rotuloDasParcelas(valores: Valores): string {
  const { total, primeira, outras } = divisao(valores);
  const parcelas = primeira === outras ? `${valores.parcelas}x de ${formatarCentavos(outras)}` : `${valores.parcelas}x: ${formatarCentavos(primeira)} na 1ª e ${formatarCentavos(outras)} nas outras`;
  return valores.valor_total_centavos == null ? `${parcelas}, total ${formatarCentavos(total)}` : parcelas;
}

/** Quantas das outras parcelas ficaram como estavam, numa frase; vazio quando nenhuma ficou. */
export function avisoDasMantidas(mantidas: number | undefined): string {
  if (!mantidas) return "";
  return mantidas === 1
    ? "1 parcela ficou como estava: alguém a mudou à mão."
    : `${mantidas} parcelas ficaram como estavam: alguém as mudou à mão.`;
}

/** "01/06 · R$ 100,00 → R$ 200,00 · 01/08/2026", ou "· sai": uma parcela realizada que a mudança muda. */
export function comoMuda(m: AvisoDeRealizadas["parcelas"][number], parcelas: number): string {
  const valor = m.valor_novo_centavos != null && m.valor_novo_centavos !== m.valor_centavos ? `${formatarCentavos(m.valor_centavos)} → ${formatarCentavos(m.valor_novo_centavos)}` : formatarCentavos(m.valor_centavos);
  const data = m.data_nova && m.data_nova !== m.data ? `${dataPorExtenso(m.data)} → ${dataPorExtenso(m.data_nova)}` : dataPorExtenso(m.data);
  return [numeroDaParcela(m.parcela, parcelas), valor, data, m.sai ? "sai" : ""].filter(Boolean).join(" · ");
}
