import { useEffect, useMemo, useState } from "react";
import { salvarLancamento, useAvisoDePlanejamento, useCadastro, useLancamentos, usePessoas, useSugestao, useTags, type LancamentoNaTela, type Sugestao } from "../dados";
import { nomePorId, tituloDoLancamento } from "./apresentacao";
import { AvisoDePlanejamento } from "./AvisoDePlanejamento";
import { hoje, mesDepois, rotuloDaData, rotuloDaFatura } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { EscolhaDoTipo } from "./EscolhaDoTipo";
import { FolhaDeDetalhes, type SugestaoNaFolha } from "./FolhaDeDetalhes";
import { Teclado } from "./Teclado";

type Tipo = "despesa" | "receita";
type Situacao = LancamentoNaTela["situacao"];

/** O último lançamento que quem está com o aparelho criou à mão (o que a recorrência gerou fica de fora). */
function ultimoCriado(lancamentos: LancamentoNaTela[], euId?: string): LancamentoNaTela | undefined {
  // O criado só no aparelho ainda não tem autor nem hora do servidor: é deste aparelho, e o mais novo.
  const criadoEm = (l: LancamentoNaTela) => (l.criado_em ? Date.parse(l.criado_em) : (l.feitoEm ?? Infinity));
  const meus = lancamentos.filter(
    (l) => !l.conflito && !l.exclusao && !l.recorrencia_id && (l.criado_por ? !euId || l.criado_por === euId : l.naoEnviado),
  );
  return meus.reduce<LancamentoNaTela | undefined>((ultimo, l) => (!ultimo || criadoEm(l) > criadoEm(ultimo) ? l : ultimo), undefined);
}

type Props = {
  id?: string;
  tipoInicial?: Tipo;
  /** O valor já digitado na tela de transferência, ao voltar dela. */
  centavosIniciais?: number;
  /** No lançamento novo, a troca para a tela de transferência, levando o valor digitado. */
  onTransferencia?: (centavos: number) => void;
};

/** Novo lançamento (sem `id`) ou edição (com `id`, preenchida pelo que o aparelho mostra). */
export function TelaDeLancamento({ id, tipoInicial = "despesa", centavosIniciais = 0, onTransferencia }: Props) {
  const { contas, cartoes, contasECartoes, categorias, carregado } = useCadastro();
  const { lancamentos, semDados } = useLancamentos();
  const { pessoas, nomeDe, euId } = usePessoas();
  const opcoesDeTags = useTags();
  const sugerir = useSugestao();
  // A identidade nasce no aparelho: reenviar o mesmo pedido nunca duplica.
  const [novoId] = useState(() => crypto.randomUUID());
  const [existente, setExistente] = useState<LancamentoNaTela | null>(null);
  const [tipo, setTipo] = useState<Tipo>(tipoInicial);
  const [centavos, setCentavos] = useState(centavosIniciais);
  const [contaId, setContaId] = useState("");
  const [categoriaIds, setCategoriaIds] = useState<string[]>([]);
  const [data, setData] = useState(hoje);
  const [descricao, setDescricao] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  // A fatura escolhida à mão (o mês, `AAAA-MM-01`); sem ela, o servidor escolhe pela data (ADR 0015).
  const [faturaMes, setFaturaMes] = useState<string | null>(null);
  const [detalhesAbertos, setDetalhesAbertos] = useState(false);
  // A sugestão aparece quando se digita a descrição e some ao escolher uma.
  const [sugerindo, setSugerindo] = useState(false);
  // Sem pessoa, o lançamento é do conjunto (do casal).
  const [pessoa, setPessoa] = useState<string | null>(null);
  // Só a escolha à mão vai ao servidor; sem ela, ele decide pela data (futura nasce prevista).
  const [situacaoEscolhida, setSituacaoEscolhida] = useState<Situacao | null>(null);
  // O item tocado em "Conta no planejamento em:"; sem toque, vale a escolha que o lançamento já tem
  // ou, no novo, a última para aquelas categorias.
  const [itemTocado, setItemTocado] = useState<string | null>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  // Preenche uma vez só, quando o lançamento aparece; o envio da fila não apaga o que se digita.
  useEffect(() => {
    if (!id || existente) return;
    const achado = lancamentos?.find((l) => l.id === id);
    if (!achado) {
      if (lancamentos || semDados) setErro(semDados ? "Sem internet: este lançamento não está no aparelho." : "Lançamento não encontrado.");
      return;
    }
    setErro("");
    setExistente(achado);
    setTipo(achado.tipo);
    setCentavos(achado.valor_centavos);
    setContaId(achado.conta_id);
    setCategoriaIds(achado.categoria_ids);
    setData(achado.data);
    setDescricao(achado.descricao ?? "");
    setTags(achado.tags ?? []);
    setPessoa(achado.pessoa ?? null);
    setFaturaMes(achado.fatura_mes ?? null);
  }, [id, existente, lancamentos, semDados]);

  // Sem escolha, a primeira conta já vem marcada: lançar é um dedo só.
  const conta = contaId || contas[0]?.id || "";
  /** As categorias que ainda se pode escolher, das que um lançamento anterior traz. */
  const escolhiveis = (ids: string[]) => categorias.filter((c) => !c.arquivada && ids.includes(c.id));
  const categoriasDoTipo = categorias.filter((c) => c.tipo === tipo && (!c.arquivada || categoriaIds.includes(c.id) || !!existente?.categoria_ids.includes(c.id)));
  const situacao: Situacao =
    situacaoEscolhida ??
    (existente && data === existente.data ? existente.situacao : data > hoje() ? "previsto" : "realizado");
  const podeSalvar = centavos > 0 && categoriaIds.length > 0 && conta !== "" && !enviando && (!id || existente !== null);

  // O que a folha de detalhes preencheu, numa linha; a data de hoje e o realizado são o normal e não aparecem.
  const resumo = [
    descricao.trim(),
    ...tags.map((t) => `#${t}`),
    pessoa ? nomeDe(pessoa) : "",
    faturaMes ? rotuloDaFatura(faturaMes) : "",
    data === hoje() ? "" : rotuloDaData(data),
    situacao === "previsto" ? "previsto" : "",
  ]
    .filter(Boolean)
    .join(" · ");

  const ultimo = useMemo(() => (id ? undefined : ultimoCriado(lancamentos ?? [], euId)), [id, lancamentos, euId]);
  const mostraRepetir = !!ultimo && centavos === 0 && categoriaIds.length === 0;

  /** Preenche com o último lançamento, com a data de hoje e a situação que ela dá. */
  function repetirUltimo(u: LancamentoNaTela) {
    setTipo(u.tipo);
    setData(hoje());
    setSituacaoEscolhida(null);
    setCentavos(u.valor_centavos);
    if (contasECartoes.some((c) => c.id === u.conta_id)) trocarConta(u.conta_id);
    setCategoriaIds(escolhiveis(u.categoria_ids).map((c) => c.id));
    setDescricao(u.descricao ?? "");
    setTags(u.tags ?? []);
    setPessoa(u.pessoa ?? null);
  }

  /**
   * Preenche conta, categorias, tags e pessoa da sugestão, e o tipo que as categorias têm; o valor,
   * a data e a descrição ficam como estão.
   */
  function escolher(s: Sugestao) {
    setTipo(s.tipo);
    if (contasECartoes.some((c) => c.id === s.conta_id)) trocarConta(s.conta_id);
    setCategoriaIds(escolhiveis(s.categoria_ids).map((c) => c.id));
    setTags(s.tags);
    setPessoa(s.pessoa ?? null);
    setSugerindo(false);
  }

  const sugestoes: SugestaoNaFolha[] = sugerindo
    ? sugerir(descricao, { tipo, valor_centavos: centavos, conta_id: conta, data }).map((s) => ({
        descricao: s.descricao.trim(),
        // A conta ou categoria que não se pode mais escolher fica de fora, como ao escolher.
        resumo: [
          escolhiveis(s.categoria_ids).map((c) => c.nome).join(", "),
          ...s.tags.map((t) => `#${t}`),
          contasECartoes.find((c) => c.id === s.conta_id)?.nome ?? "",
          s.pessoa ? nomeDe(s.pessoa) : "Conjunto",
        ]
          .filter(Boolean)
          .join(" · "),
        onEscolher: () => escolher(s),
      }))
    : [];

  const noCartao = cartoes.some((c) => c.id === conta) || (!!existente && existente.conta_id === conta && !!existente.fatura_mes);
  // A da data, as duas seguintes (a compra que o banco lança com atraso, história 73) e a já escolhida.
  const opcoesDeFatura = [...new Set([0, 1, 2].map((n) => mesDepois(data, n)).concat(faturaMes ?? []))].sort();

  const planejamento = useAvisoDePlanejamento(
    { id: existente?.id ?? novoId, valor_centavos: centavos, categoria_ids: categoriaIds, conta_id: conta, data, fatura_mes: noCartao ? faturaMes : null, situacao },
    itemTocado,
  );
  // Sem duas categorias com item, a escolha que o lançamento já tem fica, se a categoria dela ficou.
  const itemEscolhido = planejamento.escolha ?? (existente?.item_categoria_id && categoriaIds.includes(existente.item_categoria_id) ? existente.item_categoria_id : null);

  /** Outro cartão ou uma conta desfaz a fatura escolhida à mão, como no servidor. */
  function trocarConta(nova: string) {
    if (nova !== conta) setFaturaMes(null);
    setContaId(nova);
  }

  function trocarTipo(novo: Tipo) {
    setTipo(novo);
    setCategoriaIds([]);
  }

  function alternar(categoria: string) {
    setCategoriaIds((atuais) =>
      atuais.includes(categoria) ? atuais.filter((c) => c !== categoria) : [...atuais, categoria],
    );
  }

  async function salvar() {
    setErro("");
    setEnviando(true);
    try {
      // Vai para a fila, que sobe na hora se houver internet; sem ela, fica como não enviado.
      await salvarLancamento(
        {
          id: existente?.id ?? novoId,
          tipo,
          valor_centavos: centavos,
          data,
          descricao,
          conta_id: conta,
          categoria_ids: categoriaIds,
          pessoa,
          fatura_mes: noCartao ? faturaMes : null,
          item_categoria_id: itemEscolhido,
          ...(situacaoEscolhida && { situacao: situacaoEscolhida }),
          tags,
        },
        !existente,
        existente ?? undefined,
      );
      window.location.hash = "#/historico";
    } catch {
      setErro("Não foi possível guardar o lançamento no aparelho.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="lancamento">
      <h2>{id ? "Editar lançamento" : "Novo lançamento"}</h2>
      <EscolhaDoTipo tipo={tipo} comTransferencia={!!onTransferencia} onMudar={(t) => (t === "transferencia" ? onTransferencia?.(centavos) : trocarTipo(t))} />
      <p className="valor" data-testid="valor" aria-live="polite">
        {formatarCentavos(centavos)}
      </p>
      <button type="button" className="resumo" onClick={() => setDetalhesAbertos(true)}>
        Detalhes: {resumo || "+ descrição, tags, pessoa, data"}
      </button>
      {mostraRepetir && (
        <button type="button" className="repetir" onClick={() => repetirUltimo(ultimo)}>
          Repetir último: {tituloDoLancamento(ultimo, categorias)},{" "}
          {formatarCentavos(ultimo.valor_centavos)} · {ultimo.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ")} · {nomePorId(contasECartoes, ultimo.conta_id)}
        </button>
      )}
      <h3>Conta ou cartão</h3>
      <div className="fileira rolavel">
        {contas.map((c) => (
          <button type="button" key={c.id} className={`ficha${c.id === conta ? " marcada" : ""}`} aria-pressed={c.id === conta} onClick={() => trocarConta(c.id)}>
            {c.nome}
          </button>
        ))}
        {cartoes.map((c) => (
          <button type="button" key={c.id} className={`ficha${c.id === conta ? " marcada" : ""}`} aria-pressed={c.id === conta} onClick={() => trocarConta(c.id)}>
            <span aria-hidden="true">💳 </span>
            {c.nome}
          </button>
        ))}
        {carregado && contas.length === 0 && (
          <p className="vazio">
            Nenhuma conta. <a href="#/contas-e-categorias">Cadastrar</a>
          </p>
        )}
      </div>
      <h3>Categorias</h3>
      <div className="fileira rolavel">
        {categoriasDoTipo.map((c) => (
          <button type="button" key={c.id} className={`ficha${categoriaIds.includes(c.id) ? " marcada" : ""}`} aria-pressed={categoriaIds.includes(c.id)} onClick={() => alternar(c.id)}>
            {c.nome}
          </button>
        ))}
        {carregado && categoriasDoTipo.length === 0 && (
          <p className="vazio">
            Nenhuma categoria de {tipo}. <a href="#/contas-e-categorias">Cadastrar</a>
          </p>
        )}
      </div>
      {categoriaIds.length > 0 && (
        <AvisoDePlanejamento
          {...planejamento}
          tipo={tipo}
          nomeDaCategoria={(c) => nomePorId(categorias, c)}
          onEscolher={setItemTocado}
        />
      )}
      <Teclado centavos={centavos} onMudar={setCentavos} />
      {detalhesAbertos && (
        <FolhaDeDetalhes
          descricao={descricao}
          onDescricao={(d) => {
            setDescricao(d);
            setSugerindo(true);
          }}
          sugestoes={sugestoes}
          tags={tags}
          opcoesDeTags={opcoesDeTags}
          onTags={setTags}
          pessoas={pessoas}
          pessoa={pessoa}
          onPessoa={setPessoa}
          data={data}
          onData={setData}
          situacao={situacao}
          onSituacao={setSituacaoEscolhida}
          fatura={noCartao ? { mes: faturaMes, opcoes: opcoesDeFatura, onMudar: setFaturaMes } : undefined}
          onFechar={() => setDetalhesAbertos(false)}
        />
      )}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <button type="button" disabled={!podeSalvar} onClick={() => void salvar()}>
        Salvar
      </button>
      <a href="#/historico">Cancelar</a>
    </section>
  );
}
