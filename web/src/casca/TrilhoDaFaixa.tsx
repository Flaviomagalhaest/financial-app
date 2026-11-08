/** A barra branca da faixa verde (ticket 204): a parte `usado` de `total`, entre 0 e 100%. Só enfeita; o texto ao lado diz o número. */
export function TrilhoDaFaixa({ usado, total }: { usado: number; total: number }) {
  const parte = total > 0 ? Math.min(100, Math.max(0, (usado / total) * 100)) : 0;
  return (
    <div className="trilho-da-faixa" aria-hidden="true">
      <span style={{ width: `${parte}%` }} />
    </div>
  );
}
