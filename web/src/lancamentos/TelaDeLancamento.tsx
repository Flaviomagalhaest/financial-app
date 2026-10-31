import { useEffect, useMemo, useState } from "react";
import {
  favoritar,
  identidadeDe,
  oferecerFavoritar,
  salvarLancamento,
  salvarParcelamento,
  salvarRecorrencia,
  useAvisoDePlanejamento,
  useCadastro,
  useConexao,
  useFaturas,
  useFavoritos,
  useLancamentos,
  usePessoas,
  useSugestao,
  useTags,
  type Favorito,
  type LancamentoNaTela,
  type Sugestao,
} from "../dados";
import { indiceDeEstornos, nomePorId, restanteDaCompra, tituloDoFavorito, tituloDoLancamento } from "./apresentacao";
import { pagaPeloPagamento } from "../cartoes/apresentacao";
import { AvisoDePlanejamento } from "./AvisoDePlanejamento";
import { hoje, mesDepois, rotuloDaData, rotuloDaFatura } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { EscolhaDoTipo } from "./EscolhaDoTipo";
import { FolhaDeDetalhes, type SugestaoNaFolha } from "./FolhaDeDetalhes";
import { divisao, pedidoDo, problemaDo, rotuloDasParcelas, type ParcelamentoNaFolha } from "./parcelamento";
import { problemaDa, regraDa, rotuloDaRecorrencia, type RecorrenciaNaFolha } from "./recorrencia";
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
  /** O favorito que preenche a tela ao abrir (a grade da Hoje). */
  favoritoId?: string;
  tipoInicial?: Tipo;
  /** O valor já digitado na tela de transferência, ao voltar dela. */
  centavosIniciais?: number;
  /** O estorno da compra `estornoDe`: abre com o que ela tem, e categorias e tags não mudam (ADR 0016). */
  estornoDe?: string;
  /** No lançamento novo, a troca para a tela de transferência, levando o valor digitado. */
  onTransferencia?: (centavos: number) => void;
};

/** Novo lançamento (sem `id`) ou edição (com `id`, preenchida pelo que o aparelho mostra). */
export function TelaDeLancamento({ id, favoritoId, estornoDe, tipoInicial = "despesa", centavosIniciais = 0, onTransferencia }: Props) {
  const { contas, cartoes, contasECartoes, categorias, carregado } = useCadastro();
  const { lancamentos, semDados } = useLancamentos();
  const { pessoas, nomeDe, euId } = usePessoas();
  const opcoesDeTags = useTags();
  const sugerir = useSugestao();
  const { favoritos, carregado: favoritosCarregados, semDados: semFavoritos } = useFavoritos();
  const online = useConexao();
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
  // "Repete? Recorrente": salvar cria a regra, e os previstos o servidor gera ao receber.
  const [recorrencia, setRecorrencia] = useState<RecorrenciaNaFolha | null>(null);
  // "Repete? Parcelado": salvar cria o parcelamento, e as parcelas o servidor gera ao receber.
  const [parcelamento, setParcelamento] = useState<ParcelamentoNaFolha | null>(null);
  // O item tocado em "Conta no planejamento em:"; sem toque, vale a escolha que o lançamento já tem
  // ou, no novo, a última para aquelas categorias.
  const [itemTocado, setItemTocado] = useState<string | null>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  // A ⭐ marcada: o lançamento vira favorito ao salvar.
  const [favoritarAoSalvar, setFavoritarAoSalvar] = useState(false);
  const [favoritoAplicado, setFavoritoAplicado] = useState(false);
  const [estornoAplicado, setEstornoAplicado] = useState(false);

  // Um lançamento novo começa sem a oferta "Favoritar" do anterior.
  useEffect(() => oferecerFavoritar(null), []);

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

  // O estorno novo (`estornoDe`) ou o que se edita (`existente.estorno_de`) é ligado a uma compra.
  const compraId = estornoDe ?? existente?.estorno_de ?? undefined;
  const estornando = !!compraId;
  const indice = useMemo(() => indiceDeEstornos(lancamentos ?? []), [lancamentos]);
  const compra = compraId ? indice.compras.get(compraId) : undefined;
  // O que ainda cabe: o valor da compra menos os outros estornos dela.
  const restante = compra ? restanteDaCompra(compra, indice, existente?.id ?? novoId) : 0;

  // O estorno novo começa com o que a compra tem; o valor, no máximo o que ainda cabe. Preenche uma vez só.
  useEffect(() => {
    if (!estornoDe || estornoAplicado) return;
    if (!compra) {
      if (lancamentos || semDados) setErro(semDados ? "Sem internet: esta compra não está no aparelho." : "Compra não encontrada.");
      return;
    }
    setErro("");
    setEstornoAplicado(true);
    setTipo("despesa");
    setCentavos(Math.min(compra.valor_centavos, restanteDaCompra(compra, indice, novoId)));
    setContaId(compra.conta_id);
    setCategoriaIds(compra.categoria_ids);
    setTags(compra.tags ?? []);
    setDescricao(compra.descricao ? `Estorno ${compra.descricao}` : "");
    setPessoa(compra.pessoa ?? null);
    setData(hoje());
  }, [estornoDe, estornoAplicado, compra, indice, lancamentos, semDados, novoId]);

  // Sem escolha, a primeira conta já vem marcada: lançar é um dedo só.
  const conta = contaId || contas[0]?.id || "";
  /** As categorias que ainda se pode escolher, das que um lançamento anterior traz. */
  const escolhiveis = (ids: string[]) => categorias.filter((c) => !c.arquivada && ids.includes(c.id));
  const categoriasDoTipo = categorias.filter((c) => c.tipo === tipo && (!estornando || categoriaIds.includes(c.id)) && (!c.arquivada || categoriaIds.includes(c.id) || !!existente?.categoria_ids.includes(c.id)));
  const situacao: Situacao =
    situacaoEscolhida ??
    (existente && data === existente.data ? existente.situacao : data > hoje() ? "previsto" : "realizado");
  const estornoPronto = estornando && (!estornoDe || estornoAplicado);
  const problemaDaRecorrencia = recorrencia && problemaDa(recorrencia, data);
  const problemaDoParcelamento = parcelamento && problemaDo(parcelamento, centavos);
  const podeSalvar =
    centavos > 0 &&
    categoriaIds.length > 0 &&
    conta !== "" &&
    !enviando &&
    (!id || existente !== null) &&
    !problemaDaRecorrencia &&
    !problemaDoParcelamento &&
    (!estornoDe || estornoAplicado) &&
    (!estornando || !compra || centavos <= restante);

  const noCartao = cartoes.some((c) => c.id === conta) || (!!existente && existente.conta_id === conta && !!existente.fatura_mes);
  const parcelas = parcelamento && !problemaDoParcelamento && centavos > 0 ? pedidoDo(parcelamento, centavos, noCartao) : null;
  const rotuloDoParcelamento = parcelamento && (parcelas ? rotuloDasParcelas(parcelas) : `${parcelamento.parcelas}x`);

  // O que a folha de detalhes preencheu, numa linha; a data de hoje e o realizado são o normal e não aparecem.
  const resumo = [
    descricao.trim(),
    ...tags.map((t) => `#${t}`),
    pessoa ? nomeDe(pessoa) : "",
    recorrencia || parcelamento ? "" : faturaMes ? rotuloDaFatura(faturaMes) : "",
    data === hoje() ? "" : recorrencia ? `desde ${rotuloDaData(data)}` : parcelamento && !noCartao ? `1ª parcela ${rotuloDaData(data)}` : rotuloDaData(data),
    recorrencia ? rotuloDaRecorrencia(regraDa(recorrencia, data)) : rotuloDoParcelamento ?? (situacao === "previsto" ? "previsto" : ""),
    parcelamento?.automatico && !noCartao ? "automático" : "",
  ]
    .filter(Boolean)
    .join(" · ");

  const identidadeAtual = identidadeDe({ descricao, tipo, conta_id: conta, categoria_ids: categoriaIds, tags, pessoa });
  const jaEFavorito = favoritos.some((f) => identidadeDe(f) === identidadeAtual);

  const ultimo = useMemo(() => (id ? undefined : ultimoCriado(lancamentos ?? [], euId)), [id, lancamentos, euId]);
  const vazio = centavos === 0 && categoriaIds.length === 0;
  const mostraRepetir = !!ultimo && vazio && !estornando;
  const mostraFavoritos = !id && vazio && favoritos.length > 0 && !estornando;

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

  /** Preenche com o favorito, com o valor padrão (só o ponto de partida: "Salvar" confirma) e a data de hoje. */
  function usarFavorito(f: Favorito) {
    setTipo(f.tipo);
    setData(hoje());
    setSituacaoEscolhida(null);
    setCentavos(f.valor_padrao_centavos);
    if (contasECartoes.some((c) => c.id === f.conta_id)) trocarConta(f.conta_id);
    setCategoriaIds(escolhiveis(f.categoria_ids).map((c) => c.id));
    setDescricao(f.descricao);
    setTags(f.tags);
    setPessoa(f.pessoa ?? null);
  }

  // O favorito que a grade da Hoje abriu preenche uma vez só, quando a lista e o cadastro já chegaram.
  useEffect(() => {
    if (!favoritoId || favoritoAplicado || !carregado) return;
    const achado = favoritos.find((f) => f.id === favoritoId);
    if (!achado || !favoritosCarregados) {
      if (semFavoritos || (favoritosCarregados && !achado)) setErro("Favorito não encontrado.");
      return;
    }
    setFavoritoAplicado(true);
    usarFavorito(achado);
  });

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

  const sugestoes: SugestaoNaFolha[] = sugerindo && !estornando
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

  // O titular das faturas da compra no cartão, para avisar da fatura paga.
  const cartaoDaCompra = cartoes.find((c) => c.id === conta);
  const titularDaCompra = cartaoDaCompra ? (cartaoDaCompra.titular_id ?? cartaoDaCompra.id) : "";
  const cartaoDoEstorno = estornando ? (cartoes.find((c) => c.id === conta)?.titular_id ?? conta) : "";
  // A da data, as duas seguintes (a compra que o banco lança com atraso, história 73) e a já escolhida.
  const opcoesDeFatura = [...new Set([0, 1, 2].map((n) => mesDepois(data, n)).concat(faturaMes ?? []))].sort();

  // No parcelado, o aviso mostra a 1ª parcela, na fatura que a data dá.
  const planejamento = useAvisoDePlanejamento(
    {
      id: existente?.id ?? novoId,
      valor_centavos: parcelas ? divisao(parcelas).primeira : centavos,
      categoria_ids: categoriaIds,
      conta_id: conta,
      data,
      fatura_mes: noCartao && !parcelamento ? faturaMes : null,
      situacao,
    },
    itemTocado,
  );
  // Sem duas categorias com item, a escolha que o lançamento já tem fica, se a categoria dela ficou.
  // O estorno diminui o item em que a compra conta (o servidor o escolhe): a tela não pergunta nem troca.
  const itemEscolhido = estornando
    ? (existente?.item_categoria_id ?? null)
    : (planejamento.escolha ?? (existente?.item_categoria_id && categoriaIds.includes(existente.item_categoria_id) ? existente.item_categoria_id : null));

  /** Outro cartão ou uma conta desfaz a fatura escolhida à mão, como no servidor. */
  function trocarConta(nova: string) {
    if (nova !== conta) setFaturaMes(null);
    setContaId(nova);
  }

  function trocarTipo(novo: Tipo) {
    setTipo(novo);
    setCategoriaIds([]);
    // Só a despesa se parcela.
    if (novo !== "despesa") setParcelamento(null);
  }

  /** "Repete?" é uma coisa só: recorrente ou parcelado, nunca os dois. */
  function repetir(mudanca: { recorrencia?: RecorrenciaNaFolha | null; parcelamento?: ParcelamentoNaFolha | null }) {
    if (mudanca.recorrencia !== undefined) setRecorrencia(mudanca.recorrencia);
    if (mudanca.parcelamento !== undefined) setParcelamento(mudanca.parcelamento);
    if (mudanca.recorrencia) setParcelamento(null);
    if (mudanca.parcelamento) setRecorrencia(null);
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
      const eFavorito = jaEFavorito;
      // Vai para a fila, que sobe na hora se houver internet; sem ela, fica como não enviado.
      if (parcelamento)
        await salvarParcelamento({
          id: novoId,
          tipo: "despesa",
          data,
          descricao,
          conta_id: conta,
          categoria_ids: categoriaIds,
          item_categoria_id: itemEscolhido,
          tags,
          pessoa,
          ...pedidoDo(parcelamento, centavos, noCartao),
        });
      else if (recorrencia)
        await salvarRecorrencia({
          id: novoId,
          tipo,
          valor_centavos: centavos,
          descricao,
          conta_id: conta,
          categoria_ids: categoriaIds,
          item_categoria_id: itemEscolhido,
          tags,
          pessoa,
          ...regraDa(recorrencia, data),
        });
      else
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
            ...(compraId && { estorno_de: compraId }),
            item_categoria_id: itemEscolhido,
            ...(situacaoEscolhida && { situacao: situacaoEscolhida }),
            tags,
          },
          !existente,
          existente ?? undefined,
        );
      if (!existente && !estornando) {
        // Favoritar precisa de internet (ADR 0011): sem ela, nem a ⭐ vale nem se oferece.
        const modelo = { id: crypto.randomUUID(), descricao: descricao.trim(), tipo, conta_id: conta, categoria_ids: categoriaIds, tags, pessoa, valor_centavos: centavos };
        if (favoritarAoSalvar && !eFavorito) void favoritar(modelo).then((motivo) => motivo && oferecerFavoritar(modelo));
        else oferecerFavoritar(online && !eFavorito ? modelo : null);
      }
      window.location.hash = "#/historico";
    } catch {
      setErro(`Não foi possível guardar ${parcelamento ? "o parcelamento" : recorrencia ? "a recorrência" : "o lançamento"} no aparelho.`);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="lancamento">
      <h2>{estornando ? (id ? "Editar estorno" : "Estornar compra") : id ? "Editar lançamento" : "Novo lançamento"}</h2>
      {!estornando && <EscolhaDoTipo tipo={tipo} comTransferencia={!!onTransferencia} onMudar={(t) => (t === "transferencia" ? onTransferencia?.(centavos) : trocarTipo(t))} />}
      <p className="valor" data-testid="valor" aria-live="polite">
        {formatarCentavos(centavos)}
      </p>
      {estornando && compra && (
        <p className="vazio">
          Compra “{tituloDoLancamento(compra, categorias)}” de {formatarCentavos(compra.valor_centavos)}: ainda dá para estornar até {formatarCentavos(restante)}.
        </p>
      )}
      {estornoPronto && cartaoDoEstorno && <FaturaDoEstorno cartaoId={cartaoDoEstorno} data={data} faturaMes={faturaMes} />}
      <button type="button" className="resumo" onClick={() => setDetalhesAbertos(true)}>
        Detalhes: {resumo || "+ descrição, tags, pessoa, data"}
      </button>
      {mostraRepetir && (
        <button type="button" className="repetir" onClick={() => repetirUltimo(ultimo)}>
          Repetir último: {tituloDoLancamento(ultimo, categorias)},{" "}
          {formatarCentavos(ultimo.valor_centavos)} · {ultimo.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ")} · {nomePorId(contasECartoes, ultimo.conta_id)}
        </button>
      )}
      {mostraFavoritos && (
        <div className="fileira rolavel" role="group" aria-label="Favoritos">
          {favoritos.map((f) => (
            <button type="button" key={f.id} className="repetir favorito" onClick={() => usarFavorito(f)}>
              <span aria-hidden="true">⭐ </span>
              {tituloDoFavorito(f, categorias)} · {formatarCentavos(f.valor_padrao_centavos)}
            </button>
          ))}
        </div>
      )}
      {!id && !estornando && categoriaIds.length > 0 && (
        <button
          type="button"
          className="estrela"
          aria-pressed={jaEFavorito || favoritarAoSalvar}
          disabled={jaEFavorito || !online}
          onClick={() => setFavoritarAoSalvar((marcada) => !marcada)}
        >
          {jaEFavorito ? "⭐ É favorito" : favoritarAoSalvar ? "⭐ Será favorito" : "☆ Marcar como favorito"}
        </button>
      )}
      {!id && !estornando && !online && categoriaIds.length > 0 && <p className="vazio">Favoritar precisa de internet.</p>}
      <h3>{estornando ? "Cartão" : "Conta ou cartão"}</h3>
      <div className="fileira rolavel">
        {!estornando && contas.map((c) => (
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
        {carregado && !estornando && contas.length === 0 && (
          <p className="vazio">
            Nenhuma conta. <a href="#/contas-e-categorias">Cadastrar</a>
          </p>
        )}
      </div>
      <h3>Categorias</h3>
      <div className="fileira rolavel">
        {categoriasDoTipo.map((c) => (
          <button type="button" key={c.id} className={`ficha${categoriaIds.includes(c.id) ? " marcada" : ""}`} aria-pressed={categoriaIds.includes(c.id)} disabled={estornando} onClick={() => alternar(c.id)}>
            {c.nome}
          </button>
        ))}
        {carregado && categoriasDoTipo.length === 0 && (
          <p className="vazio">
            Nenhuma categoria de {tipo}. <a href="#/contas-e-categorias">Cadastrar</a>
          </p>
        )}
      </div>
      {categoriaIds.length > 0 && !estornando && (
        <AvisoDePlanejamento
          {...planejamento}
          tipo={tipo}
          nomeDaCategoria={(c) => nomePorId(categorias, c)}
          onEscolher={setItemTocado}
        />
      )}
      {titularDaCompra && planejamento.mes && (!existente || existente.mes !== planejamento.mes || existente.valor_centavos !== centavos) && (
        <AvisoDaFaturaPaga cartaoId={titularDaCompra} mes={planejamento.mes} />
      )}
      {/* Editando, o valor só vale depois de o lançamento carregar: a hidratação apagaria o toque. */}
      <Teclado centavos={centavos} onMudar={setCentavos} desativado={!!id && !existente} />
      {detalhesAbertos && (
        <FolhaDeDetalhes
          descricao={descricao}
          onDescricao={(d) => {
            setDescricao(d);
            setSugerindo(true);
          }}
          sugestoes={sugestoes}
          tags={tags}
          tagsTravadas={estornando}
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
          recorrencia={id || estornando ? undefined : { valor: recorrencia, problema: problemaDaRecorrencia, onMudar: (r) => repetir({ recorrencia: r }) }}
          parcelamento={
            id || estornando || tipo !== "despesa"
              ? undefined
              : { valor: parcelamento, noCartao, rotulo: parcelas ? rotuloDasParcelas(parcelas) : "", problema: problemaDoParcelamento, onMudar: (p) => repetir({ parcelamento: p }) }
          }
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

/** A fatura em que o estorno vai cair: a escolhida à mão ou a primeira que fecha depois da data (ADR 0015). */
function FaturaDoEstorno({ cartaoId, data, faturaMes }: { cartaoId: string; data: string; faturaMes: string | null }) {
  const { dados: faturas } = useFaturas(cartaoId);
  const mes = faturaMes ?? faturas?.find((f) => f.fechamento && f.fechamento > data)?.mes;
  return mes ? <p>Entra na {rotuloDaFatura(mes)}</p> : null;
}

/** A compra que cai numa fatura paga é recusada (ADR 0021): a tela avisa antes de salvar e leva à correção da fatura. */
function AvisoDaFaturaPaga({ cartaoId, mes }: { cartaoId: string; mes: string }) {
  const { dados: faturas } = useFaturas(cartaoId);
  const fatura = faturas?.find((f) => f.mes === mes);
  if (!fatura || !pagaPeloPagamento(fatura)) return null;
  return (
    <p role="alert" className="erro">
      A {rotuloDaFatura(mes)} está paga e não recebe mais compras nem estornos. <a href={`#/cartoes/${cartaoId}/${mes}`}>Corrigir a fatura</a>
    </p>
  );
}
