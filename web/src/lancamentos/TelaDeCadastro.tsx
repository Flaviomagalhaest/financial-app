import { useState, type FormEvent } from "react";
import { atualizadoAs, criarCategoria, criarConta, useCadastro, useConexao, type Categoria, type Conta } from "../dados";

const TIPOS_DE_CONTA = { corrente: "Corrente", poupanca: "Poupança", carteira: "Carteira" } as const;
const TIPOS_DE_CATEGORIA = { despesa: "Despesa", receita: "Receita" } as const;

/** Cadastro provisório de contas e categorias, até as telas de configuração. */
export function TelaDeCadastro() {
  const { contas, categorias, atualizadoEm, recarregar } = useCadastro();
  const online = useConexao();
  const [erro, setErro] = useState("");

  async function cadastrar(e: FormEvent<HTMLFormElement>, enviar: (nome: string, tipo: string) => Promise<boolean>) {
    e.preventDefault();
    const form = e.currentTarget;
    const dados = new FormData(form);
    setErro("");
    try {
      if (!(await enviar(String(dados.get("nome")), String(dados.get("tipo"))))) return setErro("Não foi possível cadastrar.");
      form.reset();
      await recarregar();
    } catch {
      setErro("Sem internet: o cadastro precisa de internet.");
    }
  }

  // Sem internet, a lista guardada continua à vista, mas cadastrar fica desativado (ADR 0011).
  const botao = (
    <>
      <button type="submit" disabled={!online}>
        Cadastrar
      </button>
      {!online && <p className="vazio">precisa de internet</p>}
    </>
  );

  return (
    <section>
      <h2>Cadastro</h2>
      <p className="vazio">Tela provisória de contas e categorias.</p>
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
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
      <form aria-label="Nova conta" onSubmit={(e) => void cadastrar(e, (nome, tipo) => criarConta(nome, tipo as Conta["tipo"]))}>
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
        {botao}
      </form>
      <h3>Categorias</h3>
      <ul className="lista">
        {categorias.map((c) => (
          <li key={c.id}>
            {c.nome} ({c.tipo})
          </li>
        ))}
      </ul>
      <form aria-label="Nova categoria" onSubmit={(e) => void cadastrar(e, (nome, tipo) => criarCategoria(nome, tipo as Categoria["tipo"]))}>
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
        {botao}
      </form>
      <a href="#/hoje">Voltar</a>
    </section>
  );
}
