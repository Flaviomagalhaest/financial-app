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
import { comoDigitado, emCentavos, formatarCentavos } from "./dinheiro";
import { avisoDasMantidas, comoMuda, divisao, type ValorDigitado } from "./parcelamento";
import { PartesDaCompra, resumoDaParte } from "./partes";

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
  };
}

/** Só o que mudou: o servidor deixa como está o campo que não vem. `null` quando o valor não é número. */
function alteracaoDo(f: Formulario, p: Parcelamento, item: string | null): Omit<AlteracaoDeParcelamento, "confirmar_realizadas"> | null {
  const centavos = emCentavos(f.valor);
  const parcelas = Number(f.parcelas);
  if (!centavos || !Number.isInteger(parcelas)) return null;
  const mudou: Omit<AlteracaoDeParcelamento, "confirmar_realizadas"> = {};
  if (f.descricao.trim() !== p.descricao) mudou.descricao = f.descricao.trim();
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
  const valorDaPrimeira =
    parcelasDoForm >= 2 && Number.isInteger(parcelasDoForm) && centavosDoForm > 0
      ? divisao(form.valorDigitado === "total" ? { parcelas: parcelasDoForm, valor_total_centavos: centavosDoForm } : { parcelas: parcelasDoForm, valor_da_parcela_centavos: centavosDoForm }).primeira
      : (primeira?.valor_centavos ?? 0);
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
    setForm({ ...form, ...mudanca });
    setAviso(null);
  };
  const alternar = (lista: string[], item: string) => (lista.includes(item) ? lista.filter((i) => i !== item) : [...lista, item]);
  // A compra parcelada com partes (ADR 0022) não tem categoria, tag nem pessoa próprias: as partes
  // mudam numa parcela, com "Todas" ou "Esta e as próximas".
  const comPartes = parcelamento.partes.length > 0;
  // As partes do parcelamento são uma proporção, não um valor: "66,7%".
  const somaDasPartes = parcelamento.partes.reduce((soma, p) => soma + p.valor_centavos, 0);
  const percentual = (v: number) => `${((v * 100) / somaDasPartes).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
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
        <p className="aviso">Uma mudança nas parcelas parou no meio: {parcelamento.mudanca_recusada}. Para terminar, mude de novo uma das parcelas que faltaram, em “Esta e as próximas” ou “Todas”.</p>
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
            onClick={() => mudar({ valorDigitado: v, valor: comoDigitado(valorDoModo(parcelamento, v)) })}
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

      {comPartes ? (
        <>
          <h3>Partes</h3>
          <ul className="lista" aria-label="Partes do parcelamento">
            {parcelamento.partes.map((p) => (
              <li key={p.id}>
                <div>
                  <span>{p.descricao || "Parte"}</span>
                  <span>{percentual(p.valor_centavos)}</span>
                </div>
                <p className="vazio">{resumoDaParte(p, categorias, nomeDe)}</p>
              </li>
            ))}
          </ul>
          <p className="vazio">Cada parcela se divide pelas partes nessa proporção. Para mudá-las, mude uma parcela e escolha &ldquo;Todas&rdquo; ou &ldquo;Esta e as próximas&rdquo;.</p>
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
      <button type="button" disabled={enviando || !online || (!comPartes && form.categoriaIds.length === 0)} onClick={() => void salvar(false)}>
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
