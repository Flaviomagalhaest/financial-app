import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import { formatarCentavos } from "./dinheiro";
import { Teclado } from "./Teclado";
import { useCadastro, type Lancamento } from "./useCadastro";

type Tipo = "despesa" | "receita";

function hoje(): string {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Novo lançamento (sem `id`) ou edição (com `id`, preenchida pelo servidor). */
export function TelaDeLancamento({ id }: { id?: string }) {
  const { contas, categorias, carregado } = useCadastro();
  // A identidade nasce no aparelho: reenviar o mesmo pedido nunca duplica.
  const [novoId] = useState(() => crypto.randomUUID());
  const [existente, setExistente] = useState<Lancamento | null>(null);
  const [tipo, setTipo] = useState<Tipo>("despesa");
  const [centavos, setCentavos] = useState(0);
  const [contaId, setContaId] = useState("");
  const [categoriaIds, setCategoriaIds] = useState<string[]>([]);
  const [data, setData] = useState(hoje);
  const [descricao, setDescricao] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!id) return;
    void api
      .GET("/api/lancamentos")
      .then(({ data: lista }) => {
      const achado = lista?.find((l) => l.id === id);
      if (!achado) return setErro("Lançamento não encontrado.");
      setExistente(achado);
      setTipo(achado.tipo);
      setCentavos(achado.valor_centavos);
      setContaId(achado.conta_id);
      setCategoriaIds(achado.categoria_ids);
      setData(achado.data);
      setDescricao(achado.descricao);
      })
      .catch(() => setErro("Sem internet: não foi possível abrir o lançamento."));
  }, [id]);

  // Sem escolha, a primeira conta já vem marcada: lançar é um dedo só.
  const conta = contaId || contas[0]?.id || "";
  const categoriasDoTipo = categorias.filter((c) => c.tipo === tipo && (!c.arquivada || categoriaIds.includes(c.id) || !!existente?.categoria_ids.includes(c.id)));
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
    const corpo = {
      id: existente?.id ?? novoId,
      tipo,
      valor_centavos: centavos,
      data,
      descricao,
      conta_id: conta,
      categoria_ids: categoriaIds,
    };
    try {
      const resposta = existente
        ? await api.PUT("/api/lancamentos/{id}", { params: { path: { id: existente.id } }, body: corpo })
        : await api.POST("/api/lancamentos", { body: corpo });
      if (resposta.error) return setErro("O servidor recusou o lançamento.");
      window.location.hash = "#/historico";
    } catch {
      setErro("Sem internet: o envio sem internet chega na próxima etapa.");
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
