import { useEffect, useState } from "react";
import {
  corrigirParcelamento,
  excluirParcelamento,
  useCadastro,
  useConexao,
  useLancamentos,
  useParcelamentos,
  usePessoas,
  useTags,
  type AlteracaoDeParcelamento,
  type AvisoDeRealizadas,
  type Parcelamento,
} from "../dados";
import { nomePorId, numeroDaParcela, ValorComSinal } from "./apresentacao";
import { dataPorExtenso, rotuloDaFatura } from "./datas";
import { comoDigitado, emCentavos, formatarCentavos } from "./dinheiro";
import type { ValorDigitado } from "./parcelamento";

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
function alteracaoDo(f: Formulario, p: Parcelamento): Omit<AlteracaoDeParcelamento, "confirmar_realizadas"> | null {
  const centavos = emCentavos(f.valor);
  const parcelas = Number(f.parcelas);
  if (!centavos || !Number.isInteger(parcelas)) return null;
  const mudou: Omit<AlteracaoDeParcelamento, "confirmar_realizadas"> = {};
  if (f.descricao.trim() !== p.descricao) mudou.descricao = f.descricao.trim();
  if (!mesmos(f.categoriaIds, p.categoria_ids)) mudou.categoria_ids = f.categoriaIds;
  if (!mesmos(f.tags, p.tags)) mudou.tags = f.tags;
  if (f.pessoa !== (p.pessoa ?? null)) mudou.pessoa = f.pessoa;
  if (parcelas !== p.parcelas) mudou.parcelas = parcelas;
  if (f.data !== p.data) mudou.data = f.data;
  // O valor vai só se a pessoa o mudou: sem ele, o total fica (mesmo com outro número de parcelas).
  if (centavos !== valorDoModo(p, f.valorDigitado)) mudou[f.valorDigitado === "total" ? "valor_total_centavos" : "valor_da_parcela_centavos"] = centavos;
  return mudou;
}

/** "01/06 · R$ 100,00 → R$ 200,00 · 01/08/2026", ou "· sai". */
function comoMuda(m: AvisoDeRealizadas["parcelas"][number], parcelas: number): string {
  const valor = m.valor_novo_centavos != null && m.valor_novo_centavos !== m.valor_centavos ? `${formatarCentavos(m.valor_centavos)} → ${formatarCentavos(m.valor_novo_centavos)}` : formatarCentavos(m.valor_centavos);
  const data = m.data_nova && m.data_nova !== m.data ? `${dataPorExtenso(m.data)} → ${dataPorExtenso(m.data_nova)}` : dataPorExtenso(m.data);
  return [numeroDaParcela(m.parcela, parcelas), valor, data, m.sai ? "sai" : ""].filter(Boolean).join(" · ");
}

/** Corrige ou exclui o parcelamento; as duas mudam a regra e precisam de internet (ADR 0011). */
export function TelaDoParcelamento({ id }: { id: string }) {
  const { dados: parcelamentos, semDados } = useParcelamentos();
  const { lancamentos } = useLancamentos();
  const { contasECartoes, categorias } = useCadastro();
  const { pessoas } = usePessoas();
  const opcoesDeTags = useTags();
  const online = useConexao();
  const parcelamento = parcelamentos?.find((p) => p.id === id);
  const [form, setForm] = useState<Formulario | null>(null);
  const [aviso, setAviso] = useState<AvisoDeRealizadas | null>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  // Preenche uma vez só, quando o parcelamento chega; a releitura não apaga o que se digita.
  useEffect(() => {
    if (parcelamento && !form) setForm(formularioDo(parcelamento));
  }, [parcelamento, form]);

  if (!parcelamento || !form) {
    return (
      <section>
        <h2>Parcelamento</h2>
        {(parcelamentos || semDados) && <p className="vazio">{semDados ? "Sem internet: este parcelamento não está no aparelho." : "Parcelamento não encontrado."}</p>}
        <a href="#/historico">Voltar ao Histórico</a>
      </section>
    );
  }

  const mudar = (mudanca: Partial<Formulario>) => {
    setForm({ ...form, ...mudanca });
    setAviso(null);
  };
  const alternar = (lista: string[], item: string) => (lista.includes(item) ? lista.filter((i) => i !== item) : [...lista, item]);
  const doParcelamento = (lancamentos ?? []).filter((l) => l.parcelamento_id === id).sort((a, b) => (a.parcela ?? 0) - (b.parcela ?? 0));
  const noCartao = !!doParcelamento[0]?.fatura_mes;
  const categoriasDeDespesa = categorias.filter((c) => c.tipo === "despesa" && (!c.arquivada || form.categoriaIds.includes(c.id)));
  const tags = [...form.tags, ...opcoesDeTags.filter((t) => !form.tags.includes(t))];

  async function salvar(confirmarRealizadas: boolean) {
    const alteracao = alteracaoDo(form!, parcelamento!);
    if (!alteracao) return setErro("Digite o valor e o número de parcelas.");
    if (Object.keys(alteracao).length === 0) return setErro("Nada mudou.");
    setErro("");
    setEnviando(true);
    const { aviso: novoAviso, motivo } = await corrigirParcelamento(id, { ...alteracao, confirmar_realizadas: confirmarRealizadas });
    setEnviando(false);
    if (novoAviso) return setAviso(novoAviso);
    if (motivo) return setErro(`Não foi possível corrigir: ${motivo}.`);
    window.location.hash = "#/historico";
  }

  async function excluir() {
    if (!window.confirm(`Excluir "${parcelamento!.descricao || "este parcelamento"}" inteiro? As ${parcelamento!.parcelas} parcelas saem, também as realizadas.`)) return;
    setErro("");
    setEnviando(true);
    const motivo = await excluirParcelamento(id);
    setEnviando(false);
    if (motivo) return setErro(`Não foi possível excluir: ${motivo}.`);
    window.location.hash = "#/historico";
  }

  return (
    <section className="lancamento">
      <h2>Parcelamento</h2>
      <p className="vazio">
        {parcelamento.parcelas}x · {nomePorId(contasECartoes, parcelamento.conta_id)}
        {parcelamento.automatico ? " · automático" : ""}
      </p>
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
      <p className="vazio">Valor, parcelas e data refazem as parcelas, menos as que alguém mudou à mão.</p>

      <h3>Categorias</h3>
      <div className="fileira rolavel">
        {categoriasDeDespesa.map((c) => (
          <button type="button" key={c.id} className={`ficha${form.categoriaIds.includes(c.id) ? " marcada" : ""}`} aria-pressed={form.categoriaIds.includes(c.id)} onClick={() => mudar({ categoriaIds: alternar(form.categoriaIds, c.id) })}>
            {c.nome}
          </button>
        ))}
      </div>
      {tags.length > 0 && (
        <>
          <h3>Tags</h3>
          <div className="fileira rolavel">
            {tags.map((t) => (
              <button type="button" key={t} className={`ficha${form.tags.includes(t) ? " marcada" : ""}`} aria-pressed={form.tags.includes(t)} onClick={() => mudar({ tags: alternar(form.tags, t) })}>
                #{t}
              </button>
            ))}
          </div>
        </>
      )}
      <h3>Pessoa</h3>
      <div className={`alternancia${pessoas.length === 2 ? " tres" : ""}`} role="group" aria-label="Pessoa">
        {[{ id: null, nome: "Conjunto" }, ...pessoas].map((p) => (
          <button type="button" key={p.id ?? "conjunto"} className={form.pessoa === p.id ? "" : "secundario"} aria-pressed={form.pessoa === p.id} onClick={() => mudar({ pessoa: p.id })}>
            {p.nome}
          </button>
        ))}
      </div>
      <p className="vazio">Descrição, categorias, tags e pessoa valem para todas as parcelas, também as realizadas.</p>

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
      <button type="button" disabled={enviando || !online || form.categoriaIds.length === 0} onClick={() => void salvar(false)}>
        Salvar correção
      </button>

      <h3>Parcelas</h3>
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
          </li>
        ))}
      </ul>

      <button type="button" className="secundario" disabled={enviando || !online} onClick={() => void excluir()}>
        Excluir parcelamento
      </button>
      <a href="#/historico">Voltar ao Histórico</a>
    </section>
  );
}
