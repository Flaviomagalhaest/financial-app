import { useEffect, useState } from "react";
import {
  chaveDaTag,
  descartarNaoEnviado,
  excluirLancamento,
  excluirRecorrencia,
  mudarRecorrencia,
  useAvisoDePlanejamento,
  useCadastro,
  useLancamentos,
  useMudancasDaRecorrenciaNaoEnviadas,
  usePessoas,
  useRecorrencias,
  useTags,
  type AlteracaoDeRecorrencia,
  type RecorrenciaNaTela,
} from "../dados";
import { AvisoDePlanejamento } from "./AvisoDePlanejamento";
import { nomePorId, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { dataPorExtenso, hoje } from "./datas";
import { comoDigitado, emCentavos } from "./dinheiro";
import { oQueMuda, rotuloDaRecorrencia } from "./recorrencia";

const mesmaTag = (a: string, b: string) => chaveDaTag(a) === chaveDaTag(b);
const mesmos = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

/** O formulário do "daqui para frente", que começa com o que a regra tem e a data deste previsto. */
type Formulario = {
  descricao: string;
  valor: string;
  tipoDoValor: RecorrenciaNaTela["tipo_do_valor"];
  automatico: boolean;
  contaId: string;
  categoriaIds: string[];
  tags: string[];
  pessoa: string | null;
  aCada: string;
  unidade: RecorrenciaNaTela["unidade"];
  data: string;
  /** A última data, para "Encerrar numa data". */
  ate: string;
};

function formularioDa(r: RecorrenciaNaTela, data: string): Formulario {
  return {
    descricao: r.descricao,
    valor: comoDigitado(r.valor_centavos),
    tipoDoValor: r.tipo_do_valor,
    automatico: r.automatico ?? false,
    contaId: r.conta_id,
    categoriaIds: r.categoria_ids,
    tags: r.tags ?? [],
    pessoa: r.pessoa ?? null,
    aCada: String(r.a_cada),
    unidade: r.unidade,
    data,
    ate: r.ate ?? data,
  };
}

/** Só o que mudou, a partir desta ocorrência: o servidor deixa como está o campo que não vem. Devolve o problema, se houver. */
function alteracaoDo(f: Formulario, r: RecorrenciaNaTela, ocorrencia: number, data: string, item: string | null): AlteracaoDeRecorrencia | string {
  const centavos = emCentavos(f.valor);
  const aCada = Number(f.aCada);
  if (!centavos) return "Digite o valor.";
  if (!Number.isInteger(aCada) || aCada < 1) return "Diga a cada quantas semanas ou meses.";
  if (f.categoriaIds.length === 0) return "Escolha ao menos uma categoria.";
  const mudou: AlteracaoDeRecorrencia = { a_partir_da_ocorrencia: ocorrencia };
  if (f.descricao.trim() !== r.descricao) mudou.descricao = f.descricao.trim();
  if (centavos !== r.valor_centavos) mudou.valor_centavos = centavos;
  if (f.tipoDoValor !== r.tipo_do_valor) mudou.tipo_do_valor = f.tipoDoValor;
  const automatico = f.tipoDoValor === "fixo" && f.automatico;
  if (automatico !== (r.automatico ?? false)) mudou.automatico = automatico;
  if (f.contaId !== r.conta_id) mudou.conta_id = f.contaId;
  if (!mesmos(f.categoriaIds, r.categoria_ids)) mudou.categoria_ids = f.categoriaIds;
  if (!mesmos(f.tags, r.tags ?? [])) mudou.tags = f.tags;
  // O item do planejamento só vai quando a tela pergunta (duas categorias com item) e a escolha é outra.
  if (item && item !== r.item_categoria_id) mudou.item_categoria_id = item;
  // O servidor lê a pessoa vazia como "do conjunto".
  if (f.pessoa !== (r.pessoa ?? null)) mudou.pessoa = f.pessoa ?? "";
  if (aCada !== r.a_cada) mudou.a_cada = aCada;
  if (f.unidade !== r.unidade) mudou.unidade = f.unidade;
  // O calendário novo vai sempre com a data desta vez que a tela mostra, para a regra que o aparelho
  // mostra até o envio ser a mesma que o servidor grava.
  if (f.data !== data || "a_cada" in mudou || "unidade" in mudou) mudou.inicio = f.data;
  return Object.keys(mudou).length > 1 ? mudou : "Nada mudou.";
}

/**
 * A recorrência a partir de um lançamento dela: mudar só este mês (a edição comum), daqui para
 * frente, pular este mês, encerrar ou excluir a regra. Tudo vai pela fila e vale sem internet
 * (ADR 0020); o servidor refaz os previstos quando a mudança sobe.
 */
export function TelaDaRecorrencia({ id }: { id: string }) {
  const { lancamentos } = useLancamentos();
  const { recorrencias, semDados } = useRecorrencias();
  const mudancas = useMudancasDaRecorrenciaNaoEnviadas();
  const { contasECartoes, categorias } = useCadastro();
  const { pessoas } = usePessoas();
  const opcoesDeTags = useTags();
  const lancamento = lancamentos?.find((l) => l.id === id);
  const regra = recorrencias?.find((r) => r.id === lancamento?.recorrencia_id);
  const [form, setForm] = useState<Formulario | null>(null);
  const [erro, setErro] = useState("");
  const [itemTocado, setItemTocado] = useState<string | null>(null);
  const [novaTag, setNovaTag] = useState("");
  // O aviso é do previsto desta vez, como ele ficaria com o que o formulário tem.
  const planejamento = useAvisoDePlanejamento(
    {
      id,
      valor_centavos: (form && emCentavos(form.valor)) || 0,
      categoria_ids: form?.categoriaIds ?? [],
      conta_id: form?.contaId ?? "",
      data: form?.data ?? lancamento?.data ?? hoje(),
      fatura_mes: lancamento?.fatura_mes ?? null,
      situacao: lancamento?.situacao ?? "previsto",
    },
    itemTocado,
  );

  // Preenche uma vez só, quando a regra chega; a releitura não apaga o que se digita.
  useEffect(() => {
    if (regra && lancamento && !form) setForm(formularioDa(regra, lancamento.data));
  }, [regra, lancamento, form]);

  if (!lancamento || !regra || !form || !lancamento.ocorrencia) {
    const carregou = lancamentos && (recorrencias || semDados);
    return (
      <section>
        <h2>Recorrência</h2>
        {carregou && <p className="vazio">{semDados ? "Sem internet: esta recorrência não está no aparelho." : "Recorrência não encontrada."}</p>}
        <a href="#/historico">Voltar ao Histórico</a>
      </section>
    );
  }

  const ocorrencia = lancamento.ocorrencia;
  const titulo = tituloDoLancamento(regra, categorias);
  const previsto = lancamento.situacao === "previsto";
  const naoEnviadas = mudancas.filter((m) => m.recorrencia.id === regra.id);
  const mudar = (mudanca: Partial<Formulario>) => setForm({ ...form, ...mudanca });
  const alternar = (lista: string[], item: string) => (lista.includes(item) ? lista.filter((i) => i !== item) : [...lista, item]);
  const categoriasDoTipo = categorias.filter((c) => c.tipo === regra.tipo && (!c.arquivada || form.categoriaIds.includes(c.id)));
  const tags = [...form.tags, ...opcoesDeTags.filter((t) => !form.tags.includes(t))];
  // A conta arquivada não está entre as do cadastro, mas segue sendo a da regra até alguém trocar.
  const contas = contasECartoes.some((c) => c.id === regra.conta_id) ? contasECartoes : [{ id: regra.conta_id, nome: "conta arquivada" }, ...contasECartoes];

  function criarTag() {
    const nome = novaTag.trim();
    if (!nome) return;
    // A tag que já existe com outra caixa é a mesma: marca a existente.
    const existente = tags.find((t) => mesmaTag(t, nome)) ?? nome;
    if (!form!.tags.some((t) => mesmaTag(t, existente))) mudar({ tags: [...form!.tags, existente] });
    setNovaTag("");
  }

  async function enviar(alteracao: AlteracaoDeRecorrencia) {
    setErro("");
    await mudarRecorrencia(regra!, alteracao).catch(() => setErro("Não foi possível guardar no aparelho."));
    window.location.hash = "#/historico";
  }

  function salvar() {
    const alteracao = alteracaoDo(form!, regra!, ocorrencia, lancamento!.data, planejamento.escolha);
    if (typeof alteracao === "string") return setErro(alteracao);
    void enviar(alteracao);
  }

  function encerrar(fim: "aqui" | "data") {
    if (fim === "data" && (!form!.ate || form!.ate < regra!.inicio)) return setErro("A última data vem antes do início da recorrência.");
    void enviar(fim === "aqui" ? { a_partir_da_ocorrencia: ocorrencia, vezes: ocorrencia } : { a_partir_da_ocorrencia: ocorrencia, ate: form!.ate });
  }

  async function pular() {
    if (!window.confirm(`Pular ${titulo} de ${dataPorExtenso(lancamento!.data)}? Este previsto sai e a recorrência segue nas outras vezes.`)) return;
    await excluirLancamento(lancamento!).catch(() => setErro("Não foi possível guardar no aparelho."));
    window.location.hash = "#/historico";
  }

  async function excluir() {
    if (!window.confirm(`Excluir a recorrência ${titulo}? Os previstos de hoje em diante saem; o atrasado e o realizado ficam.`)) return;
    await excluirRecorrencia(regra!).catch(() => setErro("Não foi possível guardar no aparelho."));
    window.location.hash = "#/historico";
  }

  return (
    <section className="lancamento">
      <h2>Recorrência</h2>
      <p>
        <strong>{titulo}</strong> <ValorComSinal l={regra} />
      </p>
      <p className="vazio">
        {rotuloDaRecorrencia(regra)} · {nomePorId(contasECartoes, regra.conta_id)}
        {regra.tipo_do_valor === "estimado" ? " · estimado" : ""}
      </p>
      <p className="vazio">
        Esta vez: {dataPorExtenso(lancamento.data)}, {lancamento.situacao}
      </p>
      {naoEnviadas.length > 0 && (
        <ul className="lista" aria-label="Mudanças não enviadas">
          {naoEnviadas.map((m) => (
            <li key={m.id}>
              <p className={m.recusa ? "erro" : "vazio"}>
                ⏳ {m.alteracao ? oQueMuda(m.alteracao) : "excluir"}, não enviado{m.recusa ? `: ${m.recusa}` : ""}
              </p>
              {m.podeDescartar && (
                <button type="button" className="secundario" onClick={() => void descartarNaoEnviado(m.id)}>
                  Descartar
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <h3>Só este mês</h3>
      <p className="vazio">Muda só este lançamento; as mudanças daqui para frente não o alcançam depois.</p>
      <div className="acoes">
        <a className="botao secundario" href={`#/novo/${lancamento.id}`}>
          Mudar só este mês
        </a>
        {previsto && (
          <button type="button" className="secundario" onClick={() => void pular()}>
            Pular este mês
          </button>
        )}
      </div>

      <h3>Daqui para frente</h3>
      <p className="vazio">Vale desta vez em diante. O realizado e os previstos que alguém mudou à mão ficam como estão.</p>
      <label htmlFor="descricao-da-recorrencia">Descrição</label>
      <input id="descricao-da-recorrencia" value={form.descricao} onChange={(e) => mudar({ descricao: e.target.value })} autoComplete="off" />
      <div className="linha">
        <label htmlFor="valor-da-recorrencia">Valor</label>
        <input id="valor-da-recorrencia" inputMode="decimal" value={form.valor} onChange={(e) => mudar({ valor: e.target.value })} />
      </div>
      <div className="alternancia" role="group" aria-label="Valor">
        {(["fixo", "estimado"] as const).map((t) => (
          <button type="button" key={t} className={form.tipoDoValor === t ? "" : "secundario"} aria-pressed={form.tipoDoValor === t} onClick={() => mudar({ tipoDoValor: t })}>
            {t === "fixo" ? "Fixo" : "Estimado"}
          </button>
        ))}
      </div>
      {form.tipoDoValor === "fixo" ? (
        <label className="caixa" htmlFor="automatico-da-recorrencia">
          <input id="automatico-da-recorrencia" type="checkbox" checked={form.automatico} onChange={(e) => mudar({ automatico: e.target.checked })} />
          Automático: vira realizado sozinho na data, sem confirmar
        </label>
      ) : (
        <p className="vazio">O estimado sempre pede confirmação.</p>
      )}
      <div className="linha">
        <label htmlFor="conta-da-recorrencia">Conta ou cartão</label>
        <select id="conta-da-recorrencia" value={form.contaId} onChange={(e) => mudar({ contaId: e.target.value })}>
          {contas.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </select>
      </div>
      <h4>Categorias</h4>
      <div className="fileira rolavel">
        {categoriasDoTipo.map((c) => (
          <button type="button" key={c.id} className={`ficha${form.categoriaIds.includes(c.id) ? " marcada" : ""}`} aria-pressed={form.categoriaIds.includes(c.id)} onClick={() => mudar({ categoriaIds: alternar(form.categoriaIds, c.id) })}>
            {c.nome}
          </button>
        ))}
      </div>
      {form.categoriaIds.length > 0 && <AvisoDePlanejamento {...planejamento} tipo={regra.tipo} nomeDaCategoria={(c) => nomePorId(categorias, c)} onEscolher={setItemTocado} />}
      <h4>Tags</h4>
      {tags.length > 0 && (
        <div className="fileira rolavel">
          {tags.map((t) => (
            <button type="button" key={t} className={`ficha${form.tags.includes(t) ? " marcada" : ""}`} aria-pressed={form.tags.includes(t)} onClick={() => mudar({ tags: alternar(form.tags, t) })}>
              #{t}
            </button>
          ))}
        </div>
      )}
      <div className="linha">
        <label className="oculto" htmlFor="nova-tag-da-recorrencia">
          Nova tag
        </label>
        <input
          id="nova-tag-da-recorrencia"
          value={novaTag}
          placeholder="Nova tag"
          onChange={(e) => setNovaTag(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            criarTag();
          }}
        />
        <button type="button" className="secundario" onClick={criarTag}>
          Criar tag
        </button>
      </div>
      <h4>Pessoa</h4>
      <div className={`alternancia${pessoas.length === 2 ? " tres" : ""}`} role="group" aria-label="Pessoa">
        {[{ id: null, nome: "Conjunto" }, ...pessoas].map((p) => (
          <button type="button" key={p.id ?? "conjunto"} className={form.pessoa === p.id ? "" : "secundario"} aria-pressed={form.pessoa === p.id} onClick={() => mudar({ pessoa: p.id })}>
            {p.nome}
          </button>
        ))}
      </div>
      <div className="linha">
        <label htmlFor="a-cada-da-recorrencia">A cada</label>
        <input id="a-cada-da-recorrencia" type="number" inputMode="numeric" min={1} value={form.aCada} onChange={(e) => mudar({ aCada: e.target.value })} />
      </div>
      <div className="alternancia" role="group" aria-label="Unidade">
        {(["semanas", "meses"] as const).map((u) => (
          <button type="button" key={u} className={form.unidade === u ? "" : "secundario"} aria-pressed={form.unidade === u} onClick={() => mudar({ unidade: u })}>
            {u === "semanas" ? "Semanas" : "Meses"}
          </button>
        ))}
      </div>
      <div className="linha">
        <label htmlFor="data-da-recorrencia">Esta vez em</label>
        <input id="data-da-recorrencia" type="date" value={form.data} onChange={(e) => e.target.value && mudar({ data: e.target.value })} />
      </div>
      <p className="vazio">Mudar a data ou o calendário remarca as próximas vezes a partir desta.</p>
      <button type="button" onClick={salvar}>
        Salvar daqui para frente
      </button>

      <h3>Encerrar</h3>
      <div className="acoes">
        <button type="button" className="secundario" onClick={() => encerrar("aqui")}>
          Encerrar depois desta vez
        </button>
      </div>
      <div className="linha">
        <label htmlFor="ate-da-recorrencia">Última data</label>
        <input id="ate-da-recorrencia" type="date" min={regra.inicio} value={form.ate} onChange={(e) => mudar({ ate: e.target.value })} />
        <button type="button" className="secundario" onClick={() => encerrar("data")}>
          Encerrar nessa data
        </button>
      </div>
      <p className="vazio">Os previstos depois do fim saem, também os que alguém mudou à mão.</p>

      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}

      <h3>Excluir</h3>
      <p className="vazio">Tira a regra e os previstos de hoje em diante; o atrasado e o realizado ficam.</p>
      <button type="button" className="secundario" onClick={() => void excluir()}>
        Excluir a recorrência
      </button>
      <a href="#/historico">Voltar ao Histórico</a>
    </section>
  );
}
