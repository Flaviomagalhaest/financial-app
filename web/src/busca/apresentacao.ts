import type { Criterios } from "../dados";

type Tipo = NonNullable<Criterios["tipos"]>[number];
type Situacao = NonNullable<Criterios["situacoes"]>[number];

/** Os nomes dos filtros de tipo e de situação, na folha e nas fichas escolhidas. */
export const TIPOS: Record<Tipo, string> = { despesa: "Despesa", receita: "Receita", transferencia: "Transferência" };
export const SITUACOES: Record<Situacao, string> = { realizado: "Realizado", previsto: "Previsto" };

/** `1 compra`, `12 compras`. */
export const contagem = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;
