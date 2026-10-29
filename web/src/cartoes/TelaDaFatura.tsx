import { useMemo, useState } from "react";
import { useCadastro, useFaturas, useLancamentos, usePessoas } from "../dados";
import { nomePorId, tituloDoLancamento, ValorComSinal } from "../lancamentos/apresentacao";
import { dataPorExtenso } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { mesPorExtenso, SITUACAO } from "./apresentacao";

const TODAS = "";

/** As compras da fatura agrupadas por dia, para conferir com o app do banco, com filtro por categoria e por tag. */
export function TelaDaFatura({ cartaoId, mes }: { cartaoId: string; mes: string }) {
  const { cartoes, contasECartoes, categorias } = useCadastro();
  const { dados: faturas } = useFaturas(cartaoId);
  const { lancamentos } = useLancamentos();
  const { nomeDe } = usePessoas();
  const [categoria, setCategoria] = useState(TODAS);
  const [tag, setTag] = useState(TODAS);

  const cartao = cartoes.find((c) => c.id === cartaoId);
  const fatura = faturas?.find((f) => f.mes === mes);
  // As compras do adicional caem na fatura do titular.
  const doCartao = useMemo(() => new Set(cartoes.filter((c) => c.id === cartaoId || c.titular_id === cartaoId).map((c) => c.id)), [cartoes, cartaoId]);
  const compras = useMemo(() => (lancamentos ?? []).filter((l) => l.mes === mes && doCartao.has(l.conta_id)), [lancamentos, mes, doCartao]);
  const tags = useMemo(() => [...new Set(compras.flatMap((l) => l.tags ?? []))].sort((a, b) => a.localeCompare(b, "pt-BR")), [compras]);

  const filtradas = compras.filter((l) => (categoria === TODAS || l.categoria_ids.includes(categoria)) && (tag === TODAS || !!l.tags?.includes(tag)));
  const dias = [...new Set(filtradas.map((l) => l.data))].sort((a, b) => b.localeCompare(a));
  const filtrando = categoria !== TODAS || tag !== TODAS;
  const somaFiltrada = filtradas.reduce((soma, l) => soma + (l.tipo === "despesa" ? l.valor_centavos : -l.valor_centavos), 0);

  return (
    <section>
      <a href="#/cartoes">Voltar aos cartões</a>
      <h2>Fatura de {mesPorExtenso(mes)}</h2>
      <p className="vazio">{cartao?.nome}</p>
      {fatura && (
        <dl className="informacoes" aria-label="Resumo da fatura">
          <dt>Situação</dt>
          <dd>{SITUACAO[fatura.situacao]}</dd>
          {fatura.fechamento && (
            <>
              <dt>Fechamento</dt>
              <dd>{dataPorExtenso(fatura.fechamento)}</dd>
            </>
          )}
          {fatura.vencimento && (
            <>
              <dt>Vencimento</dt>
              <dd>{dataPorExtenso(fatura.vencimento)}</dd>
            </>
          )}
          <dt>Total</dt>
          <dd>{formatarCentavos(fatura.total_centavos)}</dd>
          <dt>A pagar</dt>
          <dd>{formatarCentavos(fatura.a_pagar_centavos)}</dd>
        </dl>
      )}
      <label>
        Categoria
        <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value={TODAS}>Todas</option>
          {categorias.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </select>
      </label>
      <label>
        Tag
        <select value={tag} onChange={(e) => setTag(e.target.value)}>
          <option value={TODAS}>Todas</option>
          {tags.map((t) => (
            <option key={t} value={t}>
              #{t}
            </option>
          ))}
        </select>
      </label>
      {filtrando && <p className="vazio">Filtrado: {formatarCentavos(somaFiltrada)}</p>}
      {/* A busca de lançamentos ainda não existe: por ora o atalho leva ao histórico. */}
      <a href="#/historico">Ver os lançamentos</a>
      {lancamentos && filtradas.length === 0 && <p className="vazio">Nenhuma compra nesta fatura.</p>}
      {dias.map((dia) => (
        <div key={dia} role="group" aria-label={dataPorExtenso(dia)}>
          <h3>{dataPorExtenso(dia)}</h3>
          <ul className="lista">
            {filtradas
              .filter((l) => l.data === dia)
              .map((l) => (
                <li key={l.id}>
                  <div>
                    <strong>{tituloDoLancamento(l, categorias)}</strong>
                    <ValorComSinal l={l} />
                  </div>
                  <p className="vazio">
                    {nomePorId(contasECartoes, l.conta_id)} · {l.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ")}
                    {l.tags?.length ? ` · ${l.tags.map((t) => `#${t}`).join(" ")}` : ""}
                    {l.situacao === "previsto" && " · previsto"}
                    {l.pessoa ? ` · ${nomeDe(l.pessoa)}` : ""}
                  </p>
                </li>
              ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
