import { useState, type FormEvent } from "react";
import { api } from "../api/cliente";
import { useCadastro, type Categoria } from "../lancamentos/useCadastro";

const TIPOS_DE_CONTA = { corrente: "Corrente", poupanca: "Poupança", carteira: "Carteira" } as const;
const TIPOS_DE_CATEGORIA = { despesa: "Despesa", receita: "Receita", transferencia: "Transferência" } as const;

/** Contas (só criar, até o ticket 36) e categorias (criar, renomear, arquivar). Tudo exige internet. */
export function TelaDeConfiguracao() {
  const { contas, categorias, recarregar } = useCadastro();
  const [erro, setErro] = useState("");

  async function cadastrar(
    e: FormEvent<HTMLFormElement>,
    enviar: (nome: string, tipo: string) => Promise<{ ok: boolean }>,
  ) {
    e.preventDefault();
    const form = e.currentTarget;
    const dados = new FormData(form);
    setErro("");
    try {
      const { ok } = await enviar(String(dados.get("nome")), String(dados.get("tipo")));
      if (!ok) return setErro("Não foi possível cadastrar.");
      form.reset();
      await recarregar();
    } catch {
      setErro("Sem internet: a configuração precisa de internet.");
    }
  }

  async function alterar(id: string, mudanca: { nome?: string; arquivada?: boolean }): Promise<boolean> {
    setErro("");
    try {
      const { data } = await api.PATCH("/api/categorias/{id}", { params: { path: { id } }, body: mudanca });
      if (!data) {
        setErro("Não foi possível alterar a categoria.");
        return false;
      }
      await recarregar();
      return true;
    } catch {
      setErro("Sem internet: a configuração precisa de internet.");
      return false;
    }
  }

  return (
    <section>
      <h2>Configuração</h2>
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <h3>Contas</h3>
      <ul className="lista">
        {contas.map((c) => (
          <li key={c.id}>{c.nome}</li>
        ))}
      </ul>
      <form
        aria-label="Nova conta"
        onSubmit={(e) =>
          void cadastrar(e, (nome, tipo) =>
            api.POST("/api/contas", { body: { nome, tipo: tipo as keyof typeof TIPOS_DE_CONTA } }).then((r) => ({ ok: !!r.data })),
          )
        }
      >
        <label htmlFor="conta-nome">Nome</label>
        <input id="conta-nome" name="nome" required />
        <label htmlFor="conta-tipo">Tipo</label>
        <select id="conta-tipo" name="tipo">
          {Object.entries(TIPOS_DE_CONTA).map(([valor, nome]) => (
            <option key={valor} value={valor}>
              {nome}
            </option>
          ))}
        </select>
        <button type="submit">Cadastrar</button>
      </form>
      <h3>Categorias</h3>
      {(Object.keys(TIPOS_DE_CATEGORIA) as (keyof typeof TIPOS_DE_CATEGORIA)[]).map((tipo) => (
        <div key={tipo}>
          <h4>{TIPOS_DE_CATEGORIA[tipo]}</h4>
          <ul className="lista">
            {categorias
              .filter((c) => c.tipo === tipo)
              .map((c) => (
                <LinhaDeCategoria key={c.id} categoria={c} aoAlterar={alterar} />
              ))}
          </ul>
        </div>
      ))}
      <form
        aria-label="Nova categoria"
        onSubmit={(e) =>
          void cadastrar(e, (nome, tipo) =>
            api
              .POST("/api/categorias", { body: { nome, tipo: tipo as keyof typeof TIPOS_DE_CATEGORIA } })
              .then((r) => ({ ok: !!r.data })),
          )
        }
      >
        <label htmlFor="categoria-nome">Nome</label>
        <input id="categoria-nome" name="nome" required />
        <label htmlFor="categoria-tipo">Tipo</label>
        <select id="categoria-tipo" name="tipo">
          {Object.entries(TIPOS_DE_CATEGORIA).map(([valor, nome]) => (
            <option key={valor} value={valor}>
              {nome}
            </option>
          ))}
        </select>
        <button type="submit">Cadastrar</button>
      </form>
      <a href="#/hoje">Voltar</a>
    </section>
  );
}

function LinhaDeCategoria({
  categoria,
  aoAlterar,
}: {
  categoria: Categoria;
  aoAlterar: (id: string, mudanca: { nome?: string; arquivada?: boolean }) => Promise<boolean>;
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(categoria.nome);

  if (editando) {
    return (
      <li>
        <form
          aria-label={`Renomear ${categoria.nome}`}
          onSubmit={(e) => {
            e.preventDefault();
            void aoAlterar(categoria.id, { nome: nome.trim() }).then((ok) => ok && setEditando(false));
          }}
        >
          <label htmlFor={`nome-${categoria.id}`}>Novo nome de {categoria.nome}</label>
          <input id={`nome-${categoria.id}`} value={nome} onChange={(e) => setNome(e.target.value)} pattern=".*\S.*" required />
          <button type="submit">Salvar nome</button>
          <button type="button" className="secundario" onClick={() => setEditando(false)}>
            Cancelar
          </button>
        </form>
      </li>
    );
  }
  return (
    <li className={categoria.arquivada ? "arquivada" : undefined}>
      <div>
        {categoria.nome}
        {categoria.arquivada && " (arquivada)"}
      </div>
      <div className="acoes">
        <button
          type="button"
          className="secundario"
          onClick={() => {
            setNome(categoria.nome);
            setEditando(true);
          }}
        >
          Renomear {categoria.nome}
        </button>
        <button type="button" className="secundario" onClick={() => void aoAlterar(categoria.id, { arquivada: !categoria.arquivada })}>
          {categoria.arquivada ? "Desarquivar" : "Arquivar"} {categoria.nome}
        </button>
      </div>
    </li>
  );
}
