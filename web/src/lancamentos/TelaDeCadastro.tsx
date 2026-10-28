import { useState, type FormEvent } from "react";
import { api } from "../api/cliente";
import { formatarCentavos } from "./dinheiro";
import { useCadastro } from "./useCadastro";

const TIPOS_DE_CONTA = { corrente: "Corrente", poupanca: "Poupança", carteira: "Carteira" } as const;
const TIPOS_DE_CATEGORIA = { despesa: "Despesa", receita: "Receita" } as const;

/** Cadastro provisório de contas e categorias, até as telas de configuração. */
export function TelaDeCadastro() {
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
      setErro("Sem internet: o cadastro precisa de internet.");
    }
  }

  return (
    <section>
      <h2>Cadastro</h2>
      <p className="vazio">Tela provisória de contas e categorias.</p>
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <h3>Contas</h3>
      <ul className="lista">
        {contas.map((c) => (
          <li key={c.id}>
            {c.nome} · saldo {formatarCentavos(c.saldo_centavos)}
          </li>
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
      <ul className="lista">
        {categorias.map((c) => (
          <li key={c.id}>
            {c.nome} ({c.tipo})
          </li>
        ))}
      </ul>
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
