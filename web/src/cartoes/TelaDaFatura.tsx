import { useMemo, useState, type FormEvent } from "react";
import { api } from "../api/cliente";
import { enderecoDaBusca, useCadastro, useConexao, useFaturas, useLancamentos, usePessoas, type Fatura } from "../dados";
import { eCredito, indiceDeEstornos, ligacaoDoEstorno, nomePorId, podeEstornar, tituloDoLancamento, ValorComSinal } from "../lancamentos/apresentacao";
import { mesEmQueConta } from "../dados/aviso";
import { dataPorExtenso, mesPorExtenso } from "../lancamentos/datas";
import { emCentavos, formatarCentavos } from "../lancamentos/dinheiro";
import { comSinal, SITUACAO } from "./apresentacao";

const TODAS = "";

type Modo = "real" | "diferenca";

/**
 * Acerta a fatura com o que o banco cobra: o valor real da fatura (o ajuste é o que falta para o total
 * do app chegar nele) ou a diferença para o total que o app mostra (soma ao ajuste que já existe).
 * Positivo ou negativo. Precisa de internet, como as datas da fatura.
 */
function FormularioDeAjuste({ cartaoId, fatura, aoFechar, aoSalvar }: { cartaoId: string; fatura: Fatura; aoFechar: () => void; aoSalvar: () => Promise<void> }) {
  const [modo, setModo] = useState<Modo>("real");
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const valor = emCentavos(texto);
  const ajuste = typeof valor === "number" ? (modo === "real" ? valor - fatura.compras_centavos : fatura.ajuste_centavos + valor) : undefined;

  async function salvar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (ajuste === undefined) return;
    setErro("");
    setEnviando(true);
    try {
      const { response, error } = await api.PATCH("/api/cartoes/{id}/faturas/{mes}", {
        params: { path: { id: cartaoId, mes: fatura.mes } },
        body: { ajuste_centavos: ajuste },
      });
      if (!response.ok) {
        const motivo = (error as { detail?: unknown } | undefined)?.detail;
        return setErro(`Não foi possível ajustar a fatura${typeof motivo === "string" ? `: ${motivo}` : ""}.`);
      }
      await aoSalvar();
      aoFechar();
    } catch {
      setErro("Sem internet: o ajuste da fatura precisa de internet.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form aria-label="Ajustar fatura" onSubmit={(e) => void salvar(e)}>
      <label>
        <input type="radio" name="modo-do-ajuste" checked={modo === "real"} onChange={() => setModo("real")} />
        Valor real da fatura
      </label>
      <label>
        <input type="radio" name="modo-do-ajuste" checked={modo === "diferenca"} onChange={() => setModo("diferenca")} />
        Diferença
      </label>
      <label>
        Valor
        <input inputMode="decimal" value={texto} placeholder={modo === "real" ? "o total no app do banco" : "ex.: 10,00 ou -5,00"} onChange={(e) => setTexto(e.target.value)} />
      </label>
      <p className="vazio">
        {modo === "real" ? "O ajuste é o que falta para o total chegar ao valor do banco." : "A diferença soma ao ajuste que a fatura já tem; negativa, a fatura do banco é menor que a do app."}
      </p>
      {ajuste !== undefined && <p>{ajuste === 0 ? "Sem ajuste" : `Ajuste de ${comSinal(ajuste)}`}</p>}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <button type="submit" disabled={ajuste === undefined || enviando}>
        Salvar ajuste
      </button>
      <button type="button" className="secundario" onClick={aoFechar}>
        Cancelar
      </button>
    </form>
  );
}

/** As compras da fatura agrupadas por dia, para conferir com o app do banco, com filtro por categoria e por tag. */
export function TelaDaFatura({ cartaoId, mes }: { cartaoId: string; mes: string }) {
  const { cartoes, contasECartoes, categorias } = useCadastro();
  const { dados: faturas, buscar } = useFaturas(cartaoId);
  const online = useConexao();
  const [ajustando, setAjustando] = useState(false);
  const { lancamentos } = useLancamentos();
  const { nomeDe } = usePessoas();
  const [categoria, setCategoria] = useState(TODAS);
  const [tag, setTag] = useState(TODAS);

  const cartao = cartoes.find((c) => c.id === cartaoId);
  const fatura = faturas?.find((f) => f.mes === mes);
  // As compras do adicional caem na fatura do titular.
  const doCartao = useMemo(() => new Set(cartoes.filter((c) => c.id === cartaoId || c.titular_id === cartaoId).map((c) => c.id)), [cartoes, cartaoId]);
  // A compra criada só no aparelho ainda não tem `mes`: vale a fatura escolhida ou a da data (ADR 0003).
  const compras = useMemo(
    () =>
      (lancamentos ?? []).filter((l) => {
        if (!doCartao.has(l.conta_id)) return false;
        const doMes = l.mes ?? (cartao && mesEmQueConta(l, undefined, { titular: cartao, faturas: faturas ?? [] }));
        return doMes === mes;
      }),
    [lancamentos, mes, doCartao, cartao, faturas],
  );
  const indice = useMemo(() => indiceDeEstornos(lancamentos ?? []), [lancamentos]);
  // Os estornos que o servidor já somou na fatura; o que só está na fila ainda não entra no total dela.
  const estornosCentavos = compras.filter((l) => l.estorno_de && !l.naoEnviado).reduce((soma, l) => soma + l.valor_centavos, 0);
  const ligacoes = useMemo(() => new Map(compras.map((l) => [l.id, ligacaoDoEstorno(l, indice, categorias)])), [compras, indice, categorias]);
  const tags = useMemo(() => [...new Set(compras.flatMap((l) => l.tags ?? []))].sort((a, b) => a.localeCompare(b, "pt-BR")), [compras]);

  const filtradas = compras.filter((l) => (categoria === TODAS || l.categoria_ids.includes(categoria)) && (tag === TODAS || !!l.tags?.includes(tag)));
  const dias = [...new Set(filtradas.map((l) => l.data))].sort((a, b) => b.localeCompare(a));
  const filtrando = categoria !== TODAS || tag !== TODAS;
  const somaFiltrada = filtradas.reduce((soma, l) => soma + (eCredito(l) ? -l.valor_centavos : l.valor_centavos), 0);

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
          <dt>Compras</dt>
          <dd>{formatarCentavos(fatura.compras_centavos + estornosCentavos)}</dd>
          <dt>Estornos</dt>
          <dd>{estornosCentavos > 0 ? `− ${formatarCentavos(estornosCentavos)}` : formatarCentavos(0)}</dd>
          <dt>Ajuste</dt>
          <dd>{comSinal(fatura.ajuste_centavos)}</dd>
          <dt>Total</dt>
          <dd>{formatarCentavos(fatura.total_centavos)}</dd>
          <dt>A pagar</dt>
          <dd>{formatarCentavos(fatura.a_pagar_centavos)}</dd>
        </dl>
      )}
      {fatura && !ajustando && (
        <button type="button" className="secundario" disabled={!online} onClick={() => setAjustando(true)}>
          Ajustar fatura
        </button>
      )}
      {fatura && !online && <p className="vazio">Ajustar a fatura precisa de internet.</p>}
      {fatura && ajustando && <FormularioDeAjuste cartaoId={cartaoId} fatura={fatura} aoFechar={() => setAjustando(false)} aoSalvar={buscar} />}
      {fatura && fatura.situacao !== "aberta" && <p className="aviso">Esta fatura já fechou: para cancelar uma compra, estorne-a.</p>}
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
      {/* A busca pelo filtro Fatura, com a categoria e a tag escolhidas aqui. */}
      <a href={enderecoDaBusca({ fatura: { mes, cartao_id: cartaoId }, categoria_ids: categoria === TODAS ? undefined : [categoria], tags: tag === TODAS ? undefined : [tag] })}>Ver os lançamentos</a>
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
                    {ligacoes.get(l.id) && ` · ${ligacoes.get(l.id)}`}
                  </p>
                  {podeEstornar(l, cartoes, indice) && (
                    <div className="acoes">
                      <a className="botao secundario" href={`#/estornar/${l.id}`} aria-label={`Estornar ${tituloDoLancamento(l, categorias)}`}>
                        Estornar
                      </a>
                    </div>
                  )}
                </li>
              ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
