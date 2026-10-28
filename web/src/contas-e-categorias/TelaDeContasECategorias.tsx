import { useState, type FormEvent } from "react";
import { api } from "../api/cliente";
import { atualizadoAs, useCadastro, useConexao, useContasComArquivadas, type Categoria, type Conta } from "../dados";
import { formatarCentavos } from "../lancamentos/dinheiro";

const TIPOS_DE_CONTA = { corrente: "Corrente", poupanca: "Poupança", carteira: "Carteira" } as const;
const TIPOS_DE_CATEGORIA = { despesa: "Despesa", receita: "Receita", transferencia: "Transferência" } as const;

/** Contas e categorias: criar, renomear e arquivar (a conta também leva o saldo de abertura). Tudo exige internet. */
export function TelaDeContasECategorias() {
  const { categorias, atualizadoEm, recarregar: recarregarCadastro } = useCadastro();
  // Aqui as arquivadas aparecem também, para poderem voltar.
  const { contas, recarregar: recarregarContas } = useContasComArquivadas();
  const online = useConexao();
  const [erro, setErro] = useState("");
  const recarregar = async () => {
    await Promise.all([recarregarCadastro(), recarregarContas()]);
  };

  async function cadastrar(
    e: FormEvent<HTMLFormElement>,
    enviar: (nome: string, tipo: string, dados: FormData) => Promise<{ ok: boolean; mostrouErro?: boolean }>,
  ) {
    e.preventDefault();
    const form = e.currentTarget;
    const dados = new FormData(form);
    setErro("");
    try {
      const { ok, mostrouErro } = await enviar(String(dados.get("nome")), String(dados.get("tipo")), dados);
      if (!ok) return mostrouErro ? undefined : setErro("Não foi possível cadastrar.");
      form.reset();
      await recarregar();
    } catch {
      setErro("Sem internet: a alteração precisa de internet.");
    }
  }

  async function salvarConta(conta: Conta, mudanca: Partial<Conta>): Promise<boolean> {
    setErro("");
    try {
      const { data } = await api.PUT("/api/contas/{id}", {
        params: { path: { id: conta.id } },
        body: {
          nome: mudanca.nome ?? conta.nome,
          tipo: mudanca.tipo ?? conta.tipo,
          saldo_abertura_centavos: "saldo_abertura_centavos" in mudanca ? mudanca.saldo_abertura_centavos : conta.saldo_abertura_centavos,
          data_abertura: "data_abertura" in mudanca ? mudanca.data_abertura : conta.data_abertura,
          arquivada: mudanca.arquivada ?? conta.arquivada,
        },
      });
      if (!data) {
        setErro("Não foi possível alterar a conta.");
        return false;
      }
      await recarregar();
      return true;
    } catch {
      setErro("Sem internet: a alteração precisa de internet.");
      return false;
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
      setErro("Sem internet: a alteração precisa de internet.");
      return false;
    }
  }

  return (
    <section>
      <h2>Contas e categorias</h2>
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      {/* Sem internet, a lista guardada continua à vista, mas mudar fica desativado (ADR 0011). */}
      {!online && <p className="aviso">Mudar contas e categorias precisa de internet.</p>}
      <fieldset className="sem-moldura" disabled={!online}>
      <h3>Contas</h3>
      <ul className="lista">
        {contas.map((c) => (
          <LinhaDeConta key={c.id} conta={c} aoSalvar={salvarConta} />
        ))}
      </ul>
      <form
        aria-label="Nova conta"
        onSubmit={(e) =>
          void cadastrar(e, (nome, tipo, dados) => {
            const saldo = emCentavos(String(dados.get("saldo") ?? ""));
            const data = String(dados.get("data_abertura") ?? "");
            if (saldo === undefined || (saldo === null) !== (data === "")) {
              setErro("Informe o saldo de abertura e a data juntos, com o saldo em reais (ex.: 1234,56).");
              return Promise.resolve({ ok: false, mostrouErro: true });
            }
            return api
              .POST("/api/contas", { body: { nome, tipo: tipo as keyof typeof TIPOS_DE_CONTA, saldo_abertura_centavos: saldo, data_abertura: data || null } })
              .then((r) => ({ ok: !!r.data }));
          })
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
        <label htmlFor="conta-saldo">Saldo de abertura (opcional)</label>
        <input id="conta-saldo" name="saldo" inputMode="decimal" placeholder="0,00" />
        <label htmlFor="conta-data">Data de abertura (com o saldo)</label>
        <input id="conta-data" name="data_abertura" type="date" />
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
      </fieldset>
      <a href="#/hoje">Voltar</a>
    </section>
  );
}

/** "1.234,56" ou "1234.56" em centavos; vazio é `null` e o que não for número é `undefined`. */
function emCentavos(texto: string): number | null | undefined {
  const limpo = texto.trim().replace(/\./g, texto.includes(",") ? "" : ".").replace(",", ".");
  if (limpo === "") return null;
  const reais = Number(limpo);
  return Number.isFinite(reais) ? Math.round(reais * 100) : undefined;
}

function LinhaDeConta({
  conta,
  aoSalvar,
}: {
  conta: Conta;
  aoSalvar: (conta: Conta, mudanca: Partial<Conta>) => Promise<boolean>;
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(conta.nome);
  const [tipo, setTipo] = useState(conta.tipo);
  const [saldo, setSaldo] = useState("");
  const [data, setData] = useState(conta.data_abertura ?? "");

  if (editando) {
    return (
      <li>
        <form
          aria-label={`Editar ${conta.nome}`}
          onSubmit={(e) => {
            e.preventDefault();
            const centavos = emCentavos(saldo);
            if (centavos === undefined || (centavos === null) !== (data === "")) return;
            void aoSalvar(conta, { nome: nome.trim(), tipo, saldo_abertura_centavos: centavos, data_abertura: data || null }).then(
              (ok) => ok && setEditando(false),
            );
          }}
        >
          <label htmlFor={`nome-conta-${conta.id}`}>Novo nome de {conta.nome}</label>
          <input id={`nome-conta-${conta.id}`} value={nome} onChange={(e) => setNome(e.target.value)} pattern=".*\S.*" required />
          <label htmlFor={`tipo-conta-${conta.id}`}>Tipo de {conta.nome}</label>
          <select id={`tipo-conta-${conta.id}`} value={tipo} onChange={(e) => setTipo(e.target.value as Conta["tipo"])}>
            {Object.entries(TIPOS_DE_CONTA).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
          <label htmlFor={`saldo-conta-${conta.id}`}>Saldo de abertura de {conta.nome}</label>
          <input id={`saldo-conta-${conta.id}`} value={saldo} onChange={(e) => setSaldo(e.target.value)} inputMode="decimal" placeholder="0,00" />
          <label htmlFor={`data-conta-${conta.id}`}>Data de abertura de {conta.nome}</label>
          <input id={`data-conta-${conta.id}`} type="date" value={data} onChange={(e) => setData(e.target.value)} />
          <button type="submit">Salvar conta</button>
          <button type="button" className="secundario" onClick={() => setEditando(false)}>
            Cancelar
          </button>
        </form>
      </li>
    );
  }
  return (
    <li className={conta.arquivada ? "arquivada" : undefined}>
      <div>
        <span>
          {conta.nome}
          {conta.arquivada && " (arquivada)"}
        </span>
        <span>{formatarCentavos(conta.saldo_centavos)}</span>
      </div>
      <div className="acoes">
        <button
          type="button"
          className="secundario"
          onClick={() => {
            setNome(conta.nome);
            setTipo(conta.tipo);
            setSaldo(conta.saldo_abertura_centavos == null ? "" : String(conta.saldo_abertura_centavos / 100).replace(".", ","));
            setData(conta.data_abertura ?? "");
            setEditando(true);
          }}
        >
          Editar {conta.nome}
        </button>
        <button type="button" className="secundario" onClick={() => void aoSalvar(conta, { arquivada: !conta.arquivada })}>
          {conta.arquivada ? "Desarquivar" : "Arquivar"} conta {conta.nome}
        </button>
      </div>
    </li>
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
