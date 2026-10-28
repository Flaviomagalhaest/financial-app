import { useEffect, useState } from "react";
import { salvarLancamento, useCadastro, useLancamentos, type LancamentoNaTela } from "../dados";
import { hoje } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { Teclado } from "./Teclado";

type Tipo = "despesa" | "receita";
type Situacao = LancamentoNaTela["situacao"];

/** Novo lançamento (sem `id`) ou edição (com `id`, preenchida pelo que o aparelho mostra). */
export function TelaDeLancamento({ id }: { id?: string }) {
  const { contas, categorias, carregado } = useCadastro();
  const { lancamentos, semDados } = useLancamentos();
  // A identidade nasce no aparelho: reenviar o mesmo pedido nunca duplica.
  const [novoId] = useState(() => crypto.randomUUID());
  const [existente, setExistente] = useState<LancamentoNaTela | null>(null);
  const [tipo, setTipo] = useState<Tipo>("despesa");
  const [centavos, setCentavos] = useState(0);
  const [contaId, setContaId] = useState("");
  const [categoriaIds, setCategoriaIds] = useState<string[]>([]);
  const [data, setData] = useState(hoje);
  const [descricao, setDescricao] = useState("");
  // Só a escolha à mão vai ao servidor; sem ela, ele decide pela data (futura nasce prevista).
  const [situacaoEscolhida, setSituacaoEscolhida] = useState<Situacao | null>(null);
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
  }, [id, existente, lancamentos, semDados]);

  // Sem escolha, a primeira conta já vem marcada: lançar é um dedo só.
  const conta = contaId || contas[0]?.id || "";
  const categoriasDoTipo = categorias.filter((c) => c.tipo === tipo && (!c.arquivada || categoriaIds.includes(c.id) || !!existente?.categoria_ids.includes(c.id)));
  const situacao: Situacao =
    situacaoEscolhida ??
    (existente && data === existente.data ? existente.situacao : data > hoje() ? "previsto" : "realizado");
  const podeSalvar = centavos > 0 && categoriaIds.length > 0 && conta !== "" && !enviando && (!id || existente !== null);

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
          ...(situacaoEscolhida && { situacao: situacaoEscolhida }),
          // A tela ainda não edita tags (ticket 78): devolve as que o lançamento já tem.
          tags: existente?.tags ?? [],
        },
        !existente,
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
      <div className="alternancia" role="group" aria-label="Tipo">
        <button type="button" className={tipo === "despesa" ? "" : "secundario"} aria-pressed={tipo === "despesa"} onClick={() => trocarTipo("despesa")}>
          Despesa
        </button>
        <button type="button" className={tipo === "receita" ? "" : "secundario"} aria-pressed={tipo === "receita"} onClick={() => trocarTipo("receita")}>
          Receita
        </button>
      </div>
      <p className="valor" data-testid="valor" aria-live="polite">
        {formatarCentavos(centavos)}
      </p>
      <Teclado centavos={centavos} onMudar={setCentavos} />
      <h3>Conta</h3>
      <div className="fileira">
        {contas.map((c) => (
          <button type="button" key={c.id} className={`ficha${c.id === conta ? " marcada" : ""}`} aria-pressed={c.id === conta} onClick={() => setContaId(c.id)}>
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
      <div className="fileira">
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
      <details>
        <summary>Detalhes</summary>
        <label htmlFor="descricao">Descrição</label>
        <input id="descricao" value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        <label htmlFor="data">Data</label>
        <input id="data" type="date" value={data} onChange={(e) => setData(e.target.value)} required />
        <div className="alternancia" role="group" aria-label="Situação">
          {(["realizado", "previsto"] as const).map((s) => (
            <button type="button" key={s} className={situacao === s ? "" : "secundario"} aria-pressed={situacao === s} onClick={() => setSituacaoEscolhida(s)}>
              {s === "realizado" ? "Realizado" : "Previsto"}
            </button>
          ))}
        </div>
      </details>
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
