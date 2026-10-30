import { useState, type FormEvent } from "react";
import { api } from "../api/cliente";
import { atualizadoAs, useCadastro, useConexao, useContasComArquivadas, useTagsComArquivadas, type Categoria, type Conta, type ContaNaTela } from "../dados";
import { emCentavos, formatarCentavos } from "../lancamentos/dinheiro";
import { SecaoDeCartoes } from "./SecaoDeCartoes";

const TIPOS_DE_CONTA = { corrente: "Corrente", poupanca: "Poupança", carteira: "Carteira" } as const;
const TIPOS_DE_CATEGORIA = { despesa: "Despesa", receita: "Receita", transferencia: "Transferência" } as const;

/** Contas e categorias: criar, renomear e arquivar (a conta também leva o saldo de abertura). Tudo exige internet. */
export function TelaDeContasECategorias() {
  const { categorias, atualizadoEm, recarregar: recarregarCadastro } = useCadastro();
  // Aqui as arquivadas aparecem também, para poderem voltar.
  const { contas, recarregar: recarregarContas } = useContasComArquivadas();
  const { tags, recarregar: recarregarTags } = useTagsComArquivadas();
  const online = useConexao();
  const [erro, setErro] = useState("");
  const recarregar = async () => {
    await Promise.all([recarregarCadastro(), recarregarContas(), recarregarTags()]);
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

  /** Roda uma chamada de manutenção e recarrega; `false` com a mensagem na tela quando não deu. */
  async function executar(
    acao: string,
    chamar: () => Promise<{ data?: unknown; response: Response; error?: unknown }>,
  ): Promise<boolean> {
    setErro("");
    try {
      const { response, error } = await chamar();
      if (!response.ok) {
        const motivo = (error as { detail?: unknown } | undefined)?.detail;
        setErro(`Não foi possível ${acao}${typeof motivo === "string" ? `: ${motivo}` : ""}.`);
        return false;
      }
      await recarregar();
      return true;
    } catch {
      setErro("Sem internet: a alteração precisa de internet.");
      return false;
    }
  }

  const manutencaoDe = (rota: "categorias" | "tags"): Manutencao => {
    const id = (i: string) => ({ params: { path: { id: i } } });
    const singular = rota === "tags" ? "tag" : "categoria";
    return rota === "tags"
      ? {
          alterar: (i, corpo) => executar(`alterar a ${singular}`, () => api.PATCH("/api/tags/{id}", { ...id(i), body: corpo })),
          juntar: (i, destino) => executar(`juntar a ${singular}`, () => api.POST("/api/tags/{id}/juntar", { ...id(i), body: { destino_id: destino } })),
          excluir: (i) => executar(`excluir a ${singular}`, () => api.DELETE("/api/tags/{id}", id(i))),
        }
      : {
          alterar: (i, corpo) => executar(`alterar a ${singular}`, () => api.PATCH("/api/categorias/{id}", { ...id(i), body: corpo })),
          juntar: (i, destino) => executar(`juntar a ${singular}`, () => api.POST("/api/categorias/{id}/juntar", { ...id(i), body: { destino_id: destino } })),
          excluir: (i) => executar(`excluir a ${singular}`, () => api.DELETE("/api/categorias/{id}", id(i))),
        };
  };
  const dasCategorias = manutencaoDe("categorias");
  const dasTags = manutencaoDe("tags");

  async function criarTag(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const nome = String(new FormData(form).get("nome")).trim();
    if (await executar("criar a tag", () => api.POST("/api/tags", { body: { nome } }))) form.reset();
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
      <SecaoDeCartoes executar={executar} setErro={setErro} />
      <h3>Categorias</h3>
      {(Object.keys(TIPOS_DE_CATEGORIA) as (keyof typeof TIPOS_DE_CATEGORIA)[]).map((tipo) => (
        <div key={tipo}>
          <h4>{TIPOS_DE_CATEGORIA[tipo]}</h4>
          <ul className="lista">
            {categorias
              .filter((c) => c.tipo === tipo)
              .map((c) => (
                <LinhaDeItem
                    key={c.id}
                    item={c}
                    manutencao={dasCategorias}
                    destinos={categorias.filter((d) => d.tipo === c.tipo && d.id !== c.id && !d.arquivada)}
                  />
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
      <section aria-labelledby="titulo-tags">
        <h3 id="titulo-tags">Tags</h3>
        <ul className="lista">
          {tags.map((t) => (
            <LinhaDeItem key={t.id} item={t} manutencao={dasTags} destinos={tags.filter((d) => d.id !== t.id && !d.arquivada)} />
          ))}
        </ul>
        <form aria-label="Nova tag" onSubmit={(e) => void criarTag(e)}>
          <label htmlFor="tag-nome">Nome da nova tag</label>
          <input id="tag-nome" name="nome" required pattern=".*\S.*" />
          <button type="submit">Criar tag</button>
        </form>
      </section>
      </fieldset>
      <a href="#/hoje">Voltar</a>
    </section>
  );
}

function LinhaDeConta({
  conta,
  aoSalvar,
}: {
  conta: ContaNaTela;
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
        <span>
          {formatarCentavos(conta.saldo_centavos)}
          {conta.saldoNaoEnviado && " ⏳"}
        </span>
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

type Manutencao = {
  alterar: (id: string, mudanca: { nome?: string; arquivada?: boolean }) => Promise<boolean>;
  juntar: (id: string, destinoId: string) => Promise<boolean>;
  excluir: (id: string) => Promise<boolean>;
};

/** Uma categoria ou tag: renomear, arquivar, juntar em outra e excluir. */
function LinhaDeItem({
  item,
  manutencao,
  destinos,
}: {
  item: { id: string; nome: string; arquivada: boolean };
  manutencao: Manutencao;
  destinos: { id: string; nome: string }[];
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(item.nome);
  const [juntando, setJuntando] = useState(false);
  const [destino, setDestino] = useState("");

  if (editando) {
    return (
      <li>
        <form
          aria-label={`Renomear ${item.nome}`}
          onSubmit={(e) => {
            e.preventDefault();
            void manutencao.alterar(item.id, { nome: nome.trim() }).then((ok) => ok && setEditando(false));
          }}
        >
          <label htmlFor={`nome-${item.id}`}>Novo nome de {item.nome}</label>
          <input id={`nome-${item.id}`} value={nome} onChange={(e) => setNome(e.target.value)} pattern=".*\S.*" required />
          <button type="submit">Salvar nome</button>
          <button type="button" className="secundario" onClick={() => setEditando(false)}>
            Cancelar
          </button>
        </form>
      </li>
    );
  }
  return (
    <li className={item.arquivada ? "arquivada" : undefined}>
      <div>
        {item.nome}
        {item.arquivada && " (arquivada)"}
      </div>
      <div className="acoes">
        <button
          type="button"
          className="secundario"
          onClick={() => {
            setNome(item.nome);
            setEditando(true);
          }}
        >
          Renomear {item.nome}
        </button>
        <button type="button" className="secundario" onClick={() => void manutencao.alterar(item.id, { arquivada: !item.arquivada })}>
          {item.arquivada ? "Desarquivar" : "Arquivar"} {item.nome}
        </button>
        <button type="button" className="secundario" onClick={() => void manutencao.excluir(item.id)}>
          Excluir {item.nome}
        </button>
        {destinos.length > 0 && !juntando && (
          <button type="button" className="secundario" onClick={() => setJuntando(true)}>
            Juntar {item.nome}
          </button>
        )}
      </div>
      {juntando && (
        <form
          aria-label={`Juntar ${item.nome}`}
          className="acoes"
          onSubmit={(e) => {
            e.preventDefault();
            if (destino) void manutencao.juntar(item.id, destino).then((ok) => ok && setJuntando(false));
          }}
        >
          <label htmlFor={`juntar-${item.id}`} className="oculto">
            Juntar {item.nome} em
          </label>
          <select id={`juntar-${item.id}`} value={destino} onChange={(e) => setDestino(e.target.value)}>
            <option value="">Juntar em…</option>
            {destinos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </select>
          <button type="submit" disabled={!destino}>
            Confirmar junção
          </button>
          <button type="button" className="secundario" onClick={() => setJuntando(false)}>
            Cancelar
          </button>
        </form>
      )}
    </li>
  );
}
