import { useEffect, useState, type FormEvent } from "react";
import { corrigirFatura, pagamentosDaFatura, useCadastro, type CorrecaoDeFatura, type Fatura, type LancamentoNaTela } from "../dados";
import { eCredito, tituloDoLancamento } from "../lancamentos/apresentacao";
import { diaAnterior, hoje } from "../lancamentos/datas";
import { comoDigitado, emCentavos, formatarCentavos } from "../lancamentos/dinheiro";

type PagamentoNaTela = { id: string; conta_origem_id: string; valor: string; data: string; descricao: string };
type CompraNaTela = { id: string; versao: number; titulo: string; original: number; valor: string; excluir: boolean };
type CompraNova = { id: string; descricao: string; valor: string; data: string; categoria_id: string };

const valorOuNada = (texto: string) => {
  const centavos = emCentavos(texto);
  return typeof centavos === "number" && centavos > 0 ? centavos : undefined;
};

/**
 * A correção da fatura paga (ADR 0021): datas, ajuste, compras e pagamentos mudam juntos e só valem ao
 * salvar; a fatura continua paga e o que faltou pagar passa de novo para a seguinte. Precisa de internet.
 */
export function FormularioDeCorrecao({
  cartaoId,
  doCartao,
  fatura,
  compras,
  aoFechar,
  aoSalvar,
}: {
  cartaoId: string;
  /** O titular e os adicionais dele: os pagamentos de qualquer um entram na fatura. */
  doCartao: Set<string>;
  fatura: Fatura;
  compras: LancamentoNaTela[];
  aoFechar: () => void;
  aoSalvar: () => Promise<void>;
}) {
  const { contas, categorias } = useCadastro();
  const [fechamento, setFechamento] = useState(fatura.fechamento ?? "");
  const [vencimento, setVencimento] = useState(fatura.vencimento ?? "");
  const [ajuste, setAjuste] = useState(comoDigitado(fatura.ajuste_centavos));
  const [pagamentos, setPagamentos] = useState<PagamentoNaTela[] | null>(null);
  const [daFatura, setDaFatura] = useState<CompraNaTela[]>(() =>
    compras
      .filter((l) => !l.naoEnviado && l.versao !== undefined)
      .map((l) => ({ id: l.id, versao: l.versao ?? 0, titulo: tituloDoLancamento(l, categorias), original: l.valor_centavos, valor: comoDigitado(l.valor_centavos), excluir: false })),
  );
  const [novas, setNovas] = useState<CompraNova[]>([]);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    void pagamentosDaFatura(doCartao, fatura.mes).then((lidos) => {
      if (!lidos) return setErro("Sem internet: a correção da fatura precisa de internet.");
      setPagamentos(lidos.map((t) => ({ id: t.id, conta_origem_id: t.conta_origem_id, valor: comoDigitado(t.valor_centavos), data: t.data, descricao: t.descricao })));
    });
    // Lê uma vez, ao abrir: o que a pessoa já mudou no formulário não se perde.
  }, []);

  const mudarPagamento = (id: string, campos: Partial<PagamentoNaTela>) => setPagamentos((lista) => lista && lista.map((p) => (p.id === id ? { ...p, ...campos } : p)));
  const mudarCompra = (id: string, campos: Partial<CompraNaTela>) => setDaFatura((lista) => lista.map((c) => (c.id === id ? { ...c, ...campos } : c)));
  const mudarNova = (id: string, campos: Partial<CompraNova>) => setNovas((lista) => lista.map((c) => (c.id === id ? { ...c, ...campos } : c)));
  const categoriasDeDespesa = categorias.filter((c) => c.tipo === "despesa");

  const ajusteCentavos = emCentavos(ajuste);
  // O devido depois da correção: o do servidor com as mudanças do formulário.
  const sinal = (id: string) => (compras.some((l) => l.id === id && eCredito(l)) ? -1 : 1);
  const devido =
    fatura.saldo_anterior_centavos +
    fatura.total_centavos +
    ((ajusteCentavos ?? 0) - fatura.ajuste_centavos) +
    daFatura.reduce((soma, c) => soma + sinal(c.id) * ((c.excluir ? 0 : (valorOuNada(c.valor) ?? c.original)) - c.original), 0) +
    novas.reduce((soma, c) => soma + (valorOuNada(c.valor) ?? 0), 0);
  const pago = (pagamentos ?? []).reduce((soma, p) => soma + (valorOuNada(p.valor) ?? 0), 0);

  const problema =
    pagamentos === null
      ? "carregando os pagamentos"
      : pagamentos.length === 0
        ? "a fatura paga precisa de pelo menos um pagamento"
        : pagamentos.some((p) => !valorOuNada(p.valor) || !p.data || !p.conta_origem_id)
          ? "confira o valor, a data e a conta de cada pagamento"
          : daFatura.some((c) => !c.excluir && !valorOuNada(c.valor))
            ? "confira o valor das compras"
            : novas.some((c) => !valorOuNada(c.valor) || !c.data || !c.categoria_id)
              ? "confira o valor, a data e a categoria das compras novas"
              : typeof ajusteCentavos !== "number" && ajusteCentavos !== null
                ? "confira o ajuste"
                : pago > Math.max(devido, 0)
                  ? "o pagamento passa do valor da fatura"
                  : "";

  async function salvar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (problema || !pagamentos) return;
    const correcao: CorrecaoDeFatura = {
      pagamentos: pagamentos.map((p) => ({ id: p.id, conta_origem_id: p.conta_origem_id, valor_centavos: valorOuNada(p.valor) ?? 0, data: p.data, descricao: p.descricao })),
      compras_excluidas: daFatura.filter((c) => c.excluir).map((c) => ({ id: c.id, versao: c.versao })),
      compras_editadas: daFatura.filter((c) => !c.excluir && valorOuNada(c.valor) !== c.original).map((c) => ({ id: c.id, versao: c.versao, valor_centavos: valorOuNada(c.valor) })),
      compras_novas: novas.map((c) => ({
        id: c.id,
        tipo: "despesa",
        valor_centavos: valorOuNada(c.valor) ?? 0,
        data: c.data,
        descricao: c.descricao,
        conta_id: cartaoId,
        categoria_ids: [c.categoria_id],
        tags: [],
        fatura_mes: fatura.mes,
      })),
    };
    if (fechamento && fechamento !== fatura.fechamento) correcao.fechamento = fechamento;
    if (vencimento && vencimento !== fatura.vencimento) correcao.vencimento = vencimento;
    if ((ajusteCentavos ?? 0) !== fatura.ajuste_centavos) correcao.ajuste_centavos = ajusteCentavos ?? 0;
    setErro("");
    setEnviando(true);
    const motivo = await corrigirFatura(cartaoId, fatura.mes, correcao);
    setEnviando(false);
    if (motivo) return setErro(`Não foi possível corrigir a fatura: ${motivo}.`);
    await aoSalvar();
    aoFechar();
  }

  return (
    <form aria-label="Corrigir fatura" onSubmit={(e) => void salvar(e)}>
      <p className="vazio">A correção vale toda de uma vez ao salvar: a fatura continua paga e o que faltou pagar passa de novo para a fatura seguinte.</p>
      <fieldset>
        <legend>Datas e ajuste</legend>
        <label>
          Fechamento
          <input type="date" value={fechamento} onChange={(e) => setFechamento(e.target.value)} />
        </label>
        <label>
          Vencimento
          <input type="date" value={vencimento} onChange={(e) => setVencimento(e.target.value)} />
        </label>
        <label>
          Ajuste
          <input inputMode="decimal" value={ajuste} placeholder="ex.: 10,00 ou -5,00" onChange={(e) => setAjuste(e.target.value)} />
        </label>
      </fieldset>
      <fieldset>
        <legend>Pagamentos</legend>
        {pagamentos?.map((p, n) => (
          <div key={p.id} role="group" aria-label={`Pagamento ${n + 1}`}>
            <label>
              Conta
              <select value={p.conta_origem_id} onChange={(e) => mudarPagamento(p.id, { conta_origem_id: e.target.value })}>
                <option value="">Escolha</option>
                {contas.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Valor
              <input inputMode="decimal" value={p.valor} onChange={(e) => mudarPagamento(p.id, { valor: e.target.value })} />
            </label>
            <label>
              Data
              <input type="date" value={p.data} onChange={(e) => mudarPagamento(p.id, { data: e.target.value })} />
            </label>
            <button type="button" className="secundario" onClick={() => setPagamentos((lista) => lista && lista.filter((x) => x.id !== p.id))}>
              Tirar pagamento
            </button>
          </div>
        ))}
        <button
          type="button"
          className="secundario"
          disabled={pagamentos === null}
          onClick={() => setPagamentos((lista) => lista && [...lista, { id: crypto.randomUUID(), conta_origem_id: contas[0]?.id ?? "", valor: "", data: hoje(), descricao: "" }])}
        >
          Adicionar pagamento
        </button>
      </fieldset>
      <fieldset>
        <legend>Compras</legend>
        {daFatura.map((c) => (
          <div key={c.id} role="group" aria-label={c.titulo}>
            <label>
              {c.titulo}
              <input inputMode="decimal" value={c.valor} disabled={c.excluir} onChange={(e) => mudarCompra(c.id, { valor: e.target.value })} />
            </label>
            <label>
              <input type="checkbox" checked={c.excluir} onChange={(e) => mudarCompra(c.id, { excluir: e.target.checked })} />
              Excluir
            </label>
          </div>
        ))}
        {novas.map((c, n) => (
          <div key={c.id} role="group" aria-label={`Compra esquecida ${n + 1}`}>
            <label>
              Descrição
              <input value={c.descricao} onChange={(e) => mudarNova(c.id, { descricao: e.target.value })} />
            </label>
            <label>
              Valor
              <input inputMode="decimal" value={c.valor} onChange={(e) => mudarNova(c.id, { valor: e.target.value })} />
            </label>
            <label>
              Data
              <input type="date" value={c.data} onChange={(e) => mudarNova(c.id, { data: e.target.value })} />
            </label>
            <label>
              Categoria
              <select value={c.categoria_id} onChange={(e) => mudarNova(c.id, { categoria_id: e.target.value })}>
                <option value="">Escolha</option>
                {categoriasDeDespesa.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.nome}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="secundario" onClick={() => setNovas((lista) => lista.filter((x) => x.id !== c.id))}>
              Tirar compra
            </button>
          </div>
        ))}
        <button
          type="button"
          className="secundario"
          onClick={() => setNovas((lista) => [...lista, { id: crypto.randomUUID(), descricao: "", valor: "", data: fatura.fechamento ? diaAnterior(fatura.fechamento) : hoje(), categoria_id: "" }])}
        >
          Adicionar compra esquecida
        </button>
      </fieldset>
      <p>
        Pago {formatarCentavos(pago)} de {formatarCentavos(devido)}
      </p>
      {problema && pagamentos !== null && <p className="vazio">Falta: {problema}.</p>}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <button type="submit" disabled={!!problema || enviando}>
        Salvar correção
      </button>
      <button type="button" className="secundario" onClick={aoFechar}>
        Cancelar
      </button>
    </form>
  );
}
