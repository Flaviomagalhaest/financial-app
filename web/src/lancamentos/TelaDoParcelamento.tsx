import { useCallback, useMemo, useState } from "react";
import { api } from "../api/cliente";
import {
  anteciparParcelas,
  corrigirParcelamento,
  descartarNaoEnviado,
  excluirParcelamento,
  quitarParcelamento,
  useAntecipacoesNaoEnviadas,
  useCadastro,
  useConexao,
  useAvisoDePlanejamento,
  leituraDoParcelamento,
  useLancamentosDaTela,
  useParcelamentos,
  usePessoas,
  useTags,
  type AlteracaoDeParcelamento,
  type AvisoDeExclusao,
  type AvisoDeRealizadas,
  type LancamentoNaTela,
  type Parcelamento,
} from "../dados";
import { AvisoDeLeituraDoServidor } from "./AvisoDeLeituraDoServidor";
import { AvisoDePlanejamento } from "./AvisoDePlanejamento";
import { SeletorDeTags } from "./SeletorDeTags";
import { nomePorId, numeroDaParcela, ValorComSinal } from "./apresentacao";
import { dataPorExtenso, hoje, rotuloDaFatura } from "./datas";
import { comoDigitado, dividirNaProporcao, emCentavos, formatarCentavos } from "./dinheiro";
import { avisoDasMantidas, comoMuda, divisao, type ValorDigitado } from "./parcelamento";
import { dividirEmPartes, EditorDePartes, emEdicao, juntarPartes, mesmasPartes, partesParaSalvar, proporcaoAposMudar, redividirNaProporcao, problemaDasPartes, PartesDaCompra, valoresDasPartes, type Parte, type ParteEmEdicao } from "./partes";

const mesmos = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

/** O formulário da correção, que começa com o que o parcelamento tem. */
type Formulario = {
  descricao: string;
  valorDigitado: ValorDigitado;
  valor: string;
  parcelas: string;
  data: string;
  categoriaIds: string[];
  tags: string[];
  pessoa: string | null;
  // As partes (ADR 0022, ticket 158), que somam o valor digitado: o total ou o da parcela. Sem
  // elas, o parcelamento tem a classificação acima.
  partes: ParteEmEdicao[] | null;
  // Enquanto a pessoa não mexe no valor de uma parte, as partes acompanham o valor digitado nesta
  // proporção; mexer a solta.
  proporcao: number[] | null;
};

/**
 * O valor do campo ao trocar de modo (ticket 195): o digitado se converte com o número de parcelas do
 * formulário (o total vira o da parcela, sem os centavos que sobram, e o contrário). Sem valor ou
 * parcelas válidos, ou com o valor ainda igual ao gravado, vale o gravado naquele modo (sem perder centavos).
 */
const valorAoTrocarDeModo = (p: Parcelamento, f: Formulario, novo: ValorDigitado): string => {
  const centavos = emCentavos(f.valor);
  const n = Number(f.parcelas);
  if (novo === f.valorDigitado || !centavos || !Number.isInteger(n) || n < 1) return comoDigitado(valorDoModo(p, novo));
  if (n === p.parcelas && centavos === valorDoModo(p, f.valorDigitado)) return comoDigitado(valorDoModo(p, novo));
  return comoDigitado(novo === "parcela" ? Math.floor(centavos / n) : centavos * n);
};

/** O valor que o campo mostra ao abrir ou ao trocar de modo; o da parcela, sem os centavos que sobram na 1ª. */
const valorDoModo = (p: Parcelamento, modo: ValorDigitado) => (modo === "total" ? p.valor_total_centavos : Math.floor(p.valor_total_centavos / p.parcelas));

function formularioDo(p: Parcelamento): Formulario {
  return {
    descricao: p.descricao,
    valorDigitado: "total",
    valor: comoDigitado(valorDoModo(p, "total")),
    parcelas: String(p.parcelas),
    data: p.data,
    categoriaIds: p.categoria_ids,
    tags: p.tags,
    pessoa: p.pessoa ?? null,
    // A leitura traz as partes divididas pelo total, que é o valor com que o formulário abre.
    partes: p.partes.length ? p.partes.map(emEdicao) : null,
    proporcao: p.partes.length ? p.partes.map((x) => x.valor_centavos) : null,
  };
}

/** Só o que mudou: o servidor deixa como está o campo que não vem. `null` quando o valor não é número. */
function alteracaoDo(f: Formulario, p: Parcelamento, item: string | null): Omit<AlteracaoDeParcelamento, "confirmar_realizadas"> | null {
  const centavos = emCentavos(f.valor);
  const parcelas = Number(f.parcelas);
  if (!centavos || !Number.isInteger(parcelas)) return null;
  const mudou: Omit<AlteracaoDeParcelamento, "confirmar_realizadas"> = {};
  if (f.descricao.trim() !== p.descricao) mudou.descricao = f.descricao.trim();
  const partes = partesDoFormulario(f, p, centavos, item);
  if (partes) mudou.partes = partes;
  if (!mesmos(f.categoriaIds, p.categoria_ids)) mudou.categoria_ids = f.categoriaIds;
  if (!mesmos(f.tags, p.tags)) mudou.tags = f.tags;
  if (f.pessoa !== (p.pessoa ?? null)) mudou.pessoa = f.pessoa;
  if (item !== (p.item_categoria_id ?? null)) mudou.item_categoria_id = item;
  if (parcelas !== p.parcelas) mudou.parcelas = parcelas;
  if (f.data !== p.data) mudou.data = f.data;
  // O valor vai só se a pessoa o mudou: sem ele, o total fica (mesmo com outro número de parcelas).
  if (centavos !== valorDoModo(p, f.valorDigitado)) mudou[f.valorDigitado === "total" ? "valor_total_centavos" : "valor_da_parcela_centavos"] = centavos;
  return mudou;
}

/** A parte sem o valor (zerado), para saber se só a classificação dela mudou. */
const soAClassificacao = (x: Parte): Parte => ({ ...x, valor_centavos: 0 });

/** A proporção que o banco guarda, na ordem das partes; sem ela (leitura antiga), a dos valores. */
const proporcaoGuardada = (p: Parcelamento): number[] => (p.proporcao_das_partes?.length === p.partes.length ? p.proporcao_das_partes : p.partes.map((x) => x.valor_centavos));

/**
 * As partes que vão ao servidor, só se mudaram: duas ou mais dividem o parcelamento, e uma só, a
 * que ficou ao juntar com a classificação e o item do formulário, as junta. Com a proporção
 * intocada, vai a que o banco guarda, para a mudança só de classificação não mexer na divisão.
 */
function partesDoFormulario(f: Formulario, p: Parcelamento, centavos: number, item: string | null): Parte[] | null {
  if (!f.partes) {
    if (!p.partes.length) return null;
    return [{ ...p.partes[0], categoria_ids: f.categoriaIds, tags: f.tags, pessoa: f.pessoa, item_categoria_id: item, valor_centavos: p.valor_total_centavos }];
  }
  const intocada = !!f.proporcao && f.partes.length === p.partes.length;
  const guardada = proporcaoGuardada(p);
  const novas = intocada ? f.partes.map(({ valor: _, ...x }, i) => ({ ...x, valor_centavos: guardada[i] })) : partesParaSalvar(f.partes, centavos);
  if (!p.partes.length) return novas;
  const mesmaClassificacao = mesmasPartes(novas.map(soAClassificacao), p.partes.map(soAClassificacao));
  const mesmosValores = intocada || mesmasPartes(novas, p.partes);
  return mesmaClassificacao && mesmosValores ? null : novas;
}

/** "1 de fatura paga", "2 realizadas de fatura ainda não paga", "1 alterada à mão": só os tipos que saem. */
function tiposQueSaem(a: AvisoDeExclusao, noCartao: boolean): string[] {
  const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;
  return [
    a.de_fatura_paga ? plural(a.de_fatura_paga, "de fatura paga", "de fatura paga") : "",
    a.realizadas ? plural(a.realizadas, noCartao ? "realizada de fatura ainda não paga" : "realizada", noCartao ? "realizadas de fatura ainda não paga" : "realizadas") : "",
    a.alteradas_a_mao ? plural(a.alteradas_a_mao, "alterada à mão", "alteradas à mão") : "",
  ].filter(Boolean);
}

/** As parcelas da fatura paga pelo pagamento não saem: o parcelamento fica com elas (ticket 170). */
function ficamDeFaturaPaga(n: number): string {
  return n === 1
    ? "Fica 1 parcela de fatura paga, e o parcelamento continua só com ela. Para tirá-la, corrija a fatura."
    : `Ficam ${n} parcelas de fatura paga, e o parcelamento continua só com elas. Para tirá-las, corrija a fatura.`;
}

/** Corrige ou exclui o parcelamento; as duas mudam a regra e precisam de internet (ADR 0011). */
export function TelaDoParcelamento({ id }: { id: string }) {
  const { dados: parcelamentos, semDados } = useParcelamentos();
  const parcelamento = parcelamentos?.find((p) => p.id === id);
  if (parcelamento) return <Correcao parcelamento={parcelamento} />;
  return (
    <section>
      <h2>Parcelamento</h2>
      {(parcelamentos || semDados) && <p className="vazio">{semDados ? "Sem internet: este parcelamento não está no aparelho." : "Parcelamento não encontrado."}</p>}
      <a href="#/historico">Voltar ao Histórico</a>
    </section>
  );
}

/**
 * Antecipar as últimas K parcelas (vale sem internet, pela fila, com o id da antecipação como chave)
 * ou quitar tudo o que falta (precisa de internet: sem chave, o reenvio daria 422). O valor é o total
 * pago, e a diferença para o das parcelas é o desconto (ticket 155).
 */
function AnteciparOuQuitar({ parcelamento, previstas }: { parcelamento: Parcelamento; previstas: { valor_centavos: number }[] }) {
  const online = useConexao();
  const naFila = useAntecipacoesNaoEnviadas().filter((a) => a.parcelamentoId === parcelamento.id);
  const [modo, setModo] = useState<"antecipar" | "quitar">("antecipar");
  const [parcelas, setParcelas] = useState("1");
  const [data, setData] = useState(hoje);
  const [valor, setValor] = useState("");
  const [erro, setErro] = useState("");
  const [feito, setFeito] = useState("");
  const [enviando, setEnviando] = useState(false);
  const quantas = modo === "quitar" ? previstas.length : Number(parcelas);
  // As últimas K, que são as que a antecipação paga.
  const devido = previstas.slice(previstas.length - quantas).reduce((soma, l) => soma + l.valor_centavos, 0);

  async function confirmar() {
    if (modo === "antecipar" && (!Number.isInteger(quantas) || quantas < 1 || quantas > previstas.length)) return setErro(`Digite de 1 a ${previstas.length} parcelas.`);
    const centavos = valor.trim() ? emCentavos(valor) : undefined;
    if (valor.trim() && !centavos) return setErro("Digite o valor pago.");
    setErro("");
    setFeito("");
    const corpo = { data, valor_total_centavos: centavos ?? null };
    if (modo === "antecipar") {
      await anteciparParcelas(parcelamento, { parcelas: quantas, ...corpo });
      return setFeito(`${quantas === 1 ? "1 parcela" : `${quantas} parcelas`} na fila para antecipar.`);
    }
    setEnviando(true);
    const { motivo } = await quitarParcelamento(parcelamento.id, corpo);
    setEnviando(false);
    if (motivo) return setErro(`Não foi possível quitar: ${motivo}.`);
    setFeito("Parcelamento quitado.");
  }

  return (
    <section aria-label="Antecipar ou quitar">
      <h3>Antecipar ou quitar</h3>
      {naFila.length > 0 && (
        <ul className="lista" aria-label="Antecipações não enviadas">
          {naFila.map((a) => (
            <li key={a.id}>
              <div>
                <span>
                  Antecipar {a.parcelas === 1 ? "1 parcela" : `${a.parcelas} parcelas`}, não enviado
                </span>
              </div>
              {a.recusa && <p className="erro">Recusado: {a.recusa}.</p>}
              {a.podeDescartar && (
                <button type="button" className="secundario" onClick={() => void descartarNaoEnviado(a.id)}>
                  Descartar antecipação
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {feito && <p role="status">{feito}</p>}
      {previstas.length === 0 ? (
        <p className="vazio">Não há parcelas por pagar.</p>
      ) : (
        <>
          <div className="alternancia" role="group" aria-label="Pagar adiantado">
            {(
              [
                ["antecipar", "Antecipar"],
                ["quitar", "Quitar tudo"],
              ] as const
            ).map(([v, nome]) => (
              <button type="button" key={v} className={modo === v ? "" : "secundario"} aria-pressed={modo === v} onClick={() => setModo(v)}>
                {nome}
              </button>
            ))}
          </div>
          {modo === "antecipar" ? (
            <div className="linha">
              <label htmlFor="parcelas-a-antecipar">Parcelas a antecipar (as últimas, de {previstas.length} por pagar)</label>
              <input id="parcelas-a-antecipar" type="number" inputMode="numeric" min={1} max={previstas.length} value={parcelas} onChange={(e) => setParcelas(e.target.value)} />
            </div>
          ) : (
            <p className="vazio">Paga as {previstas.length} parcelas que faltam. Precisa de internet.</p>
          )}
          <div className="linha">
            <label htmlFor="data-do-pagamento">Data do pagamento</label>
            <input id="data-do-pagamento" type="date" max={hoje()} value={data} onChange={(e) => e.target.value && setData(e.target.value)} />
          </div>
          <div className="linha">
            <label htmlFor="valor-pago">Total pago</label>
            <input id="valor-pago" inputMode="decimal" placeholder={Number.isInteger(quantas) && quantas > 0 ? comoDigitado(devido) : ""} value={valor} onChange={(e) => setValor(e.target.value)} />
          </div>
          <p className="vazio">Sem valor, paga o das parcelas ({formatarCentavos(devido)}); com menos, a diferença é o desconto.</p>
          {erro && (
            <p role="alert" className="erro">
              {erro}
            </p>
          )}
          <button type="button" disabled={enviando || (modo === "quitar" && !online)} onClick={() => void confirmar()}>
            {modo === "antecipar" ? "Antecipar parcelas" : "Quitar parcelamento"}
          </button>
        </>
      )}
    </section>
  );
}

/** O formulário nasce com o parcelamento que a primeira leitura trouxe; a releitura não apaga o que se digita. */
function Correcao({ parcelamento }: { parcelamento: Parcelamento }) {
  const id = parcelamento.id;
  // As parcelas vêm do servidor: as antigas de um parcelamento longo saem da janela do aparelho (ADR 0025).
  const leitura = useMemo(() => leituraDoParcelamento(id), [id]);
  const dele = useCallback((l: LancamentoNaTela) => l.parcelamento_id === id, [id]);
  const { lancamentos, semDados: semParcelas, atualizadoEm: parcelasDaUltimaLeitura } = useLancamentosDaTela(leitura, dele);
  const { contasECartoes, categorias } = useCadastro();
  const { pessoas, nomeDe } = usePessoas();
  const opcoesDeTags = useTags();
  const online = useConexao();
  const [form, setForm] = useState<Formulario>(() => formularioDo(parcelamento));
  const [aviso, setAviso] = useState<AvisoDeRealizadas | null>(null);
  const [avisoDeExclusao, setAvisoDeExclusao] = useState<AvisoDeExclusao | null>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [itemTocado, setItemTocado] = useState<string | null>(null);
  // Gravada a correção, as parcelas que ficaram como estavam porque alguém as mudou à mão ou
  // porque estão numa fatura paga (ticket 171).
  const [mantidas, setMantidas] = useState("");
  const doParcelamento = (lancamentos ?? []).slice().sort((a, b) => (a.parcela ?? 0) - (b.parcela ?? 0));
  // A 1ª parcela é a de número 1, não a primeira da lista: sem internet, a lista pode vir sem ela
  // (resposta guardada velha, ou só os não enviados) e `[0]` seria uma parcela do meio.
  const primeira = doParcelamento.find((l) => l.parcela === 1);
  const noCartao = !!primeira?.fatura_mes;
  const saem = avisoDeExclusao ? tiposQueSaem(avisoDeExclusao, noCartao) : [];
  // O aviso mostra a 1ª parcela com o que o formulário tem; sem ela no aparelho, fica sem aviso.
  const centavosDoForm = emCentavos(form.valor) ?? 0;
  const parcelasDoForm = Number(form.parcelas);
  // As parcelas com o que o formulário tem; sem valor ou número de parcelas válidos, nenhuma.
  const divisaoDoForm =
    parcelasDoForm >= 2 && Number.isInteger(parcelasDoForm) && centavosDoForm > 0
      ? divisao(form.valorDigitado === "total" ? { parcelas: parcelasDoForm, valor_total_centavos: centavosDoForm } : { parcelas: parcelasDoForm, valor_da_parcela_centavos: centavosDoForm })
      : null;
  const valorDaPrimeira = divisaoDoForm?.primeira ?? primeira?.valor_centavos ?? 0;
  const planejamento = useAvisoDePlanejamento(
    {
      id: primeira?.id ?? id,
      valor_centavos: valorDaPrimeira,
      categoria_ids: form.categoriaIds,
      conta_id: parcelamento.conta_id,
      // No cartão a data é a da compra e a fatura é a da parcela; fora dele, a da 1ª parcela.
      data: noCartao ? (primeira?.data ?? form.data) : form.data,
      fatura_mes: noCartao ? (primeira?.fatura_mes ?? null) : null,
      situacao: primeira?.situacao ?? "previsto",
    },
    itemTocado,
  );
  // Sem duas categorias com item, a escolha que o parcelamento já tem fica, se a categoria dela ficou.
  const itemEscolhido = planejamento.escolha ?? (parcelamento.item_categoria_id && form.categoriaIds.includes(parcelamento.item_categoria_id) ? parcelamento.item_categoria_id : null);

  const mudar = (mudanca: Partial<Formulario>) => {
    const novo = { ...form, ...mudanca };
    // As partes acompanham o valor digitado: sempre ao trocar entre o total e o da parcela, e ao
    // mudar o valor enquanto ninguém mexeu nelas (ticket 158).
    const centavos = emCentavos(novo.valor) ?? 0;
    const trocouOModo = novo.valorDigitado !== form.valorDigitado;
    const pesos = novo.proporcao ?? (trocouOModo && form.partes ? valoresDasPartes(form.partes, centavosDoForm) : null);
    if (novo.partes && (trocouOModo || novo.proporcao)) novo.partes = redividirNaProporcao(novo.partes, pesos, centavos) ?? novo.partes;
    setForm(novo);
    setAviso(null);
  };
  /** O editor mudou as partes: só a classificação mantém a proporção; valor tocado ou parte posta ou tirada a solta. */
  const mudarPartes = (novas: ParteEmEdicao[]) => {
    setForm({ ...form, partes: novas, proporcao: proporcaoAposMudar(form.proporcao, form.partes, novas) });
    setAviso(null);
  };
  /** O parcelamento se divide em duas partes: a primeira com a classificação que ele tinha, a segunda vazia, com o resto do valor. */
  const dividir = () => {
    setForm({ ...form, partes: dividirEmPartes({ categoria_ids: form.categoriaIds, tags: form.tags, pessoa: form.pessoa }), proporcao: null, categoriaIds: [], tags: [], pessoa: null });
    setItemTocado(null);
    setAviso(null);
  };
  /** Tirar a penúltima parte: o parcelamento volta a ser um, com a classificação da parte que ficou. */
  const juntar = (fica: ParteEmEdicao) => {
    const junta = juntarPartes(fica, form.descricao);
    setForm({ ...form, partes: null, proporcao: null, categoriaIds: junta.classificacao.categoria_ids, tags: junta.classificacao.tags, pessoa: junta.classificacao.pessoa, descricao: junta.descricao });
    setItemTocado(junta.item);
    setAviso(null);
  };
  const alternar = (lista: string[], item: string) => (lista.includes(item) ? lista.filter((i) => i !== item) : [...lista, item]);
  // A compra parcelada com partes (ADR 0022) não tem categoria, tag nem pessoa próprias: as partes
  // mudam aqui (ticket 158) ou numa parcela, com "Todas" ou "Esta e as próximas".
  const comPartes = !!form.partes;
  // A menor parcela também se divide pelas partes, e cada uma precisa de um centavo dela.
  const menorParcela = divisaoDoForm?.outras;
  const problemaNasPartes = form.partes ? problemaDasPartes(form.partes, centavosDoForm, menorParcela) : "";
  const categoriasDeDespesa = categorias.filter((c) => c.tipo === "despesa" && (!c.arquivada || form.categoriaIds.includes(c.id)));
  async function salvar(confirmarRealizadas: boolean) {
    const alteracao = alteracaoDo(form, parcelamento, itemEscolhido);
    if (!alteracao) return setErro("Digite o valor e o número de parcelas.");
    if (Object.keys(alteracao).length === 0) return setErro("Nada mudou.");
    setErro("");
    setEnviando(true);
    const { aviso: novoAviso, motivo, mantidas: quantas } = await corrigirParcelamento(id, { ...alteracao, confirmar_realizadas: confirmarRealizadas });
    setEnviando(false);
    if (novoAviso) return setAviso(novoAviso);
    if (motivo) return setErro(`Não foi possível corrigir: ${motivo}.`);
    if (quantas) return setMantidas(avisoDasMantidas(quantas));
    window.location.hash = "#/historico";
  }

  /** Sem `confirmarRealizadas`, pergunta antes; se o servidor achar parcela paga ou alterada à mão, nada sai e a tela mostra o aviso forte. */
  async function excluir(confirmarRealizadas: boolean) {
    if (!confirmarRealizadas && !window.confirm(`Excluir "${parcelamento.descricao || "este parcelamento"}" inteiro? As ${parcelamento.parcelas} parcelas saem.`)) return;
    setErro("");
    setEnviando(true);
    const { aviso: novoAviso, motivo } = await excluirParcelamento(id, confirmarRealizadas);
    setEnviando(false);
    if (novoAviso) return setAvisoDeExclusao(novoAviso);
    if (motivo) return setErro(`Não foi possível excluir: ${motivo}.`);
    window.location.hash = "#/historico";
  }

  if (mantidas)
    return (
      <section className="lancamento">
        <h2>Parcelamento</h2>
        <p role="status">Correção gravada. {mantidas}</p>
        <a href="#/historico">Voltar ao Histórico</a>
      </section>
    );

  return (
    <section className="lancamento">
      <h2>Parcelamento</h2>
      <p className="vazio">
        {parcelamento.parcelas}x · {nomePorId(contasECartoes, parcelamento.conta_id)}
        {parcelamento.automatico ? " · automático" : ""}
      </p>
      {parcelamento.parcelas_anteriores > 0 && (
        <p className="aviso">
          {parcelamento.parcelas_anteriores === 1 ? "1 parcela não foi lançada: vencia" : `${parcelamento.parcelas_anteriores} parcelas não foram lançadas: venciam`} antes de hoje, na criação (a numeração segue a do total).
        </p>
      )}
      {parcelamento.mudanca_recusada && (
        <p className="aviso">Uma mudança nas parcelas parou no meio: {parcelamento.mudanca_recusada}. Para terminar, mude de novo uma das parcelas que faltaram, em “Esta e as próximas” ou “Todas”, ou, se a correção do parcelamento parou, corrija-o de novo.</p>
      )}
      {!online && <p className="aviso">Sem internet: corrigir e excluir o parcelamento precisam de internet.</p>}

      <label htmlFor="descricao-do-parcelamento">Descrição</label>
      <input id="descricao-do-parcelamento" value={form.descricao} onChange={(e) => mudar({ descricao: e.target.value })} autoComplete="off" />

      <div className="alternancia" role="group" aria-label="O valor é">
        {(
          [
            ["total", "O total"],
            ["parcela", "O da parcela"],
          ] as const
        ).map(([v, nome]) => (
          <button
            type="button"
            key={v}
            className={form.valorDigitado === v ? "" : "secundario"}
            aria-pressed={form.valorDigitado === v}
            onClick={() => mudar({ valorDigitado: v, valor: valorAoTrocarDeModo(parcelamento, form, v) })}
          >
            {nome}
          </button>
        ))}
      </div>
      <div className="linha">
        <label htmlFor="valor-do-parcelamento">{form.valorDigitado === "total" ? "Valor total" : "Valor da parcela"}</label>
        <input id="valor-do-parcelamento" inputMode="decimal" value={form.valor} onChange={(e) => mudar({ valor: e.target.value })} />
      </div>
      <div className="linha">
        <input id="parcelas-do-parcelamento" type="number" inputMode="numeric" min={2} value={form.parcelas} onChange={(e) => mudar({ parcelas: e.target.value })} />
        <label htmlFor="parcelas-do-parcelamento">parcelas</label>
      </div>
      <div className="linha">
        <label htmlFor="data-do-parcelamento">{noCartao ? "Data da compra" : "Primeira parcela"}</label>
        <input id="data-do-parcelamento" type="date" value={form.data} onChange={(e) => e.target.value && mudar({ data: e.target.value })} />
      </div>
      <p className="vazio">Valor, parcelas e data refazem as parcelas, menos as que alguém mudou à mão e as de fatura paga.</p>

      {form.partes ? (
        <>
          <EditorDePartes partes={form.partes} total={centavosDoForm} menorParcela={menorParcela} categorias={categoriasDeDespesa} pessoas={pessoas} opcoesDeTags={opcoesDeTags} onMudar={mudarPartes} onJuntar={juntar} />
          <p className="vazio">As partes somam {form.valorDigitado === "total" ? "o total" : "o valor da parcela"}, e cada parcela se divide por elas nessa proporção. Valem para todas as parcelas, também as realizadas, menos as que têm partes próprias.</p>
        </>
      ) : (
        <>
      <h3>Categorias</h3>
      <div className="fileira rolavel">
        {categoriasDeDespesa.map((c) => (
          <button type="button" key={c.id} className={`ficha${form.categoriaIds.includes(c.id) ? " marcada" : ""}`} aria-pressed={form.categoriaIds.includes(c.id)} onClick={() => mudar({ categoriaIds: alternar(form.categoriaIds, c.id) })}>
            {c.nome}
          </button>
        ))}
      </div>
      {form.categoriaIds.length > 0 && primeira && (
        <AvisoDePlanejamento {...planejamento} tipo="despesa" nomeDaCategoria={(c) => nomePorId(categorias, c)} onEscolher={setItemTocado} />
      )}
      <h3>Tags</h3>
      <SeletorDeTags tags={form.tags} opcoes={opcoesDeTags} onTags={(t) => mudar({ tags: t })} />
      <h3>Pessoa</h3>
      <div className={`alternancia${pessoas.length === 2 ? " tres" : ""}`} role="group" aria-label="Pessoa">
        {[{ id: null, nome: "Conjunto" }, ...pessoas].map((p) => (
          <button type="button" key={p.id ?? "conjunto"} className={form.pessoa === p.id ? "" : "secundario"} aria-pressed={form.pessoa === p.id} onClick={() => mudar({ pessoa: p.id })}>
            {p.nome}
          </button>
        ))}
      </div>
      <p className="vazio">Descrição, categorias, tags e pessoa valem para todas as parcelas, também as realizadas, menos onde alguém mudou à mão.</p>
      {centavosDoForm > 0 && (
        <button type="button" className="secundario" onClick={dividir}>
          Dividir em partes
        </button>
      )}
        </>
      )}

      {aviso && (
        <div className="aviso" role="group" aria-label="Parcelas realizadas que mudam">
          <p>Estas parcelas já foram realizadas e mudam com a correção; nada foi gravado ainda.</p>
          <ul>
            {aviso.parcelas.map((m) => (
              <li key={m.id}>{comoMuda(m, Number(form.parcelas) || parcelamento.parcelas)}</li>
            ))}
          </ul>
          <div className="acoes">
            <button type="button" disabled={enviando || !online} onClick={() => void salvar(true)}>
              Corrigir mesmo assim
            </button>
            <button type="button" className="secundario" onClick={() => setAviso(null)}>
              Voltar
            </button>
          </div>
        </div>
      )}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <button type="button" disabled={enviando || !online || (comPartes ? !!problemaNasPartes : form.categoriaIds.length === 0)} onClick={() => void salvar(false)}>
        Salvar correção
      </button>

      <AnteciparOuQuitar parcelamento={parcelamento} previstas={doParcelamento.filter((l) => l.situacao === "previsto")} />

      <h3>Parcelas</h3>
      <AvisoDeLeituraDoServidor daUltimaLeitura={parcelasDaUltimaLeitura} semDados={semParcelas} oQue="as parcelas" precisam="as parcelas precisam de internet." />
      <ul className="lista parcelas" aria-label={`Parcelas de ${parcelamento.descricao}`}>
        {doParcelamento.map((l) => (
          <li key={l.id}>
            <div>
              <span>{l.parcela && numeroDaParcela(l.parcela, parcelamento.parcelas)}</span>
              <ValorComSinal l={l} />
            </div>
            <p className="vazio">
              {dataPorExtenso(l.data)}
              {l.fatura_mes ? ` · ${rotuloDaFatura(l.fatura_mes)}` : ""} · {l.situacao}
              {l.alterada_a_mao && " · alterada à mão"}
              {l.naoEnviado && " · ⏳ não enviado"}
            </p>
            {!!l.partes?.length && <PartesDaCompra partes={l.partes} categorias={categorias} nomeDe={nomeDe} titulo={`${parcelamento.descricao} ${l.parcela}`} />}
          </li>
        ))}
      </ul>

      {avisoDeExclusao ? (
        <div className="aviso" role="alertdialog" aria-label="Excluir parcelas já pagas">
          <p>
            <strong>Isto apaga lançamentos já pagos e pode desconfigurar o histórico. Confirma?</strong>
          </p>
          <p>
            {avisoDeExclusao.parcelas === 1 ? "Sai 1 parcela" : `Saem as ${avisoDeExclusao.parcelas} parcelas`}
            {saem.length ? "; entre elas:" : "."}
          </p>
          {!!saem.length && (
            <ul>
              {saem.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          )}
          {!!avisoDeExclusao.ficam_de_fatura_paga && <p>{ficamDeFaturaPaga(avisoDeExclusao.ficam_de_fatura_paga)}</p>}
          <div className="acoes">
            <button type="button" disabled={enviando || !online} onClick={() => void excluir(true)}>
              Excluir mesmo assim
            </button>
            <button type="button" className="secundario" onClick={() => setAvisoDeExclusao(null)}>
              Voltar
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="secundario" disabled={enviando || !online} onClick={() => void excluir(false)}>
          Excluir parcelamento
        </button>
      )}
      <a href="#/historico">Voltar ao Histórico</a>
    </section>
  );
}
