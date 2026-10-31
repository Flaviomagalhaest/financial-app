import { config } from "../config";
import type { NovoParcelamento } from "../dados";
import { formatarCentavos } from "./dinheiro";

/** O "Repete? Parcelado" da folha de detalhes, como a tela o edita; o valor do teclado é o total ou o da parcela. */
export type ParcelamentoNaFolha = {
  parcelas: number;
  /** Sem juros, o total se divide pelas parcelas; com juros, cada parcela vale o digitado. */
  valorDigitado: "total" | "parcela";
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

/** O total e as parcelas como o servidor divide (`valor_da_parcela`): os centavos que sobram vão na 1ª. */
export function divisao({ parcelas, valor_total_centavos, valor_da_parcela_centavos }: Valores) {
  const total = valor_total_centavos ?? (valor_da_parcela_centavos ?? 0) * parcelas;
  const outras = Math.floor(total / parcelas);
  return { total, primeira: outras + (total % parcelas), outras };
}

/** "10x de R$ 99,90", "3x: R$ 33,34 na 1ª e R$ 33,33 nas outras", com o total quando ele não foi o digitado. */
export function rotuloDasParcelas(valores: Valores): string {
  const { total, primeira, outras } = divisao(valores);
  const parcelas = primeira === outras ? `${valores.parcelas}x de ${formatarCentavos(outras)}` : `${valores.parcelas}x: ${formatarCentavos(primeira)} na 1ª e ${formatarCentavos(outras)} nas outras`;
  return valores.valor_total_centavos == null ? `${parcelas}, total ${formatarCentavos(total)}` : parcelas;
}
