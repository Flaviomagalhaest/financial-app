import { useEffect, useRef, useState } from "react";
import {
  aplicarLote,
  chaveDaTag,
  useCadastro,
  useConexao,
  useTags,
  verPreviaDoLote,
  type EdicaoEmLote,
  type PedidoDeEdicaoEmLote,
  type PreviaDaEdicaoEmLote,
} from "../dados";
import { nomePorId, tituloDoLancamento } from "../lancamentos/apresentacao";

type Acao = "acrescentar" | "remover" | "trocar" | "substituir";

const ACOES: Record<Acao, string> = { acrescentar: "Acrescentar", remover: "Tirar", trocar: "Trocar", substituir: "Substituir" };

/** `1 compra`, `12 compras`. */
export const contagem = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

/** Fichas que se marcam: várias, ou uma só no "por" do trocar. */
function Fichas({ nome, opcoes, marcadas, onAlternar }: { nome: string; opcoes: { valor: string; rotulo: string }[]; marcadas: string[]; onAlternar: (valor: string) => void }) {
  return (
    <div className="fileira" role="group" aria-label={nome}>
      {opcoes.map((o) => {
        const marcada = marcadas.includes(o.valor);
        return (
          <button type="button" key={o.valor} className={`ficha${marcada ? " marcada" : ""}`} aria-pressed={marcada} onClick={() => onAlternar(o.valor)}>
            {o.rotulo}
          </button>
        );
      })}
    </div>
  );
}

/**
 * A edição em lote (ticket 61): acrescentar, tirar, trocar ou substituir categorias ou tags dos
 * marcados de uma vez. A prévia mostra o que muda antes de aplicar, e o servidor aplica tudo ou nada.
 * Só com internet: não entra na fila (ADR 0011).
 */
export function FolhaDaEdicaoEmLote({
  selecao,
  marcados,
  onAplicada,
  onFechar,
}: {
  selecao: PedidoDeEdicaoEmLote["selecao"];
  /** "3 marcados", "Todos do resultado". */
  marcados: string;
  onAplicada: (lote: EdicaoEmLote) => void;
  onFechar: () => void;
}) {
  const folha = useRef<HTMLDialogElement>(null);
  const { categorias } = useCadastro();
  const tagsExistentes = useTags();
  const online = useConexao();
  const [campo, setCampo] = useState<"categorias" | "tags">("categorias");
  const [acao, setAcao] = useState<Acao>("acrescentar");
  // Categorias pelo id, tags pelo nome.
  const [escolhidas, setEscolhidas] = useState<string[]>([]);
  const [por, setPor] = useState("");
  const [tagNova, setTagNova] = useState("");
  const [previa, setPrevia] = useState<PreviaDaEdicaoEmLote | null>(null);
  const [recusa, setRecusa] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  // O mesmo pedido reenviado (a resposta se perdeu) leva o mesmo id e não aplica de novo.
  const id = useRef(crypto.randomUUID());
  useEffect(() => folha.current?.showModal(), []);

  /** Mudar o pedido tira a prévia, que era de outro. */
  const mudar = (fazer: () => void) => {
    fazer();
    setPrevia(null);
    setRecusa(null);
    id.current = crypto.randomUUID();
  };
  const alternar = (valor: string) =>
    mudar(() => setEscolhidas((atuais) => (atuais.some((v) => chave(v) === chave(valor)) ? atuais.filter((v) => chave(v) !== chave(valor)) : [...atuais, valor])));
  const chave = (valor: string) => (campo === "tags" ? chaveDaTag(valor) : valor);

  const entram = acao === "acrescentar" || acao === "substituir";
  const tipoDasEscolhidas = categorias.find((c) => c.id === escolhidas[0])?.tipo;
  const opcoesDeCategoria = (tipo: string) =>
    categorias.filter((c) => c.tipo === tipo && (!c.arquivada || !entram)).map((c) => ({ valor: c.id, rotulo: c.arquivada ? `${c.nome} (arquivada)` : c.nome }));
  const opcoesDeTag = [...new Map([...tagsExistentes, ...escolhidas].map((t) => [chaveDaTag(t), t])).values()].map((t) => ({ valor: t, rotulo: `#${t}` }));

  const completo = (escolhidas.length > 0 || (campo === "tags" && acao === "substituir")) && (acao !== "trocar" || !!por.trim());
  const pedido: PedidoDeEdicaoEmLote =
    campo === "categorias"
      ? { selecao, categorias: { acao, categoria_ids: escolhidas, por: acao === "trocar" ? por : null } }
      : { selecao, tags: { acao, tags: escolhidas, por: acao === "trocar" ? por.trim() : null } };

  async function verPrevia() {
    setEnviando(true);
    const resposta = await verPreviaDoLote(pedido);
    setEnviando(false);
    if (typeof resposta === "string") return setRecusa(resposta);
    setPrevia(resposta);
    setRecusa(resposta.recusa ?? null);
  }

  async function aplicar() {
    setEnviando(true);
    const resposta = await aplicarLote(pedido, id.current);
    setEnviando(false);
    if (typeof resposta === "string") return setRecusa(resposta);
    onAplicada(resposta);
  }

  const classificacao = (categoriaIds: string[], tags: string[]) =>
    [categoriaIds.map((c) => nomePorId(categorias, c)).join(", "), tags.map((t) => `#${t}`).join(" ")].filter(Boolean).join(" · ");

  return (
    <dialog ref={folha} className="folha edicao-em-lote" aria-labelledby="titulo-da-edicao-em-lote" onClose={onFechar}>
      <h3 id="titulo-da-edicao-em-lote">Editar em lote</h3>
      <p className="vazio">{marcados}. Uma compra parcelada leva todas as parcelas.</p>

      <div className="alternancia" role="group" aria-label="O que muda">
        {(["categorias", "tags"] as const).map((c) => (
          <button key={c} type="button" className={campo === c ? undefined : "secundario"} aria-pressed={campo === c} onClick={() =>
              mudar(() => {
                setCampo(c);
                setEscolhidas([]);
                setPor("");
              })
            }>
            {c === "categorias" ? "Categorias" : "Tags"}
          </button>
        ))}
      </div>
      <Fichas
        nome="Como muda"
        opcoes={(Object.keys(ACOES) as Acao[]).map((a) => ({ valor: a, rotulo: ACOES[a] }))}
        marcadas={[acao]}
        onAlternar={(a) =>
          mudar(() => {
            setAcao(a as Acao);
            setPor("");
          })
        }
      />

      <h4>{acao === "trocar" ? "Trocar" : acao === "remover" ? "Tirar" : acao === "substituir" ? "Ficam só" : "Acrescentar"}</h4>
      {campo === "categorias" ? (
        <>
          <Fichas nome="Categorias de despesa" opcoes={opcoesDeCategoria("despesa")} marcadas={escolhidas} onAlternar={alternar} />
          <Fichas nome="Categorias de receita" opcoes={opcoesDeCategoria("receita")} marcadas={escolhidas} onAlternar={alternar} />
          {acao === "trocar" && (
            <>
              <h4>Por</h4>
              <Fichas
                nome="Trocar por"
                opcoes={categorias
                  .filter((c) => c.tipo === (tipoDasEscolhidas ?? "despesa") && !c.arquivada && !escolhidas.includes(c.id))
                  .map((c) => ({ valor: c.id, rotulo: c.nome }))}
                marcadas={[por]}
                onAlternar={(valor) => mudar(() => setPor(por === valor ? "" : valor))}
              />
            </>
          )}
        </>
      ) : (
        <>
          <Fichas nome="Tags" opcoes={opcoesDeTag} marcadas={escolhidas} onAlternar={alternar} />
          {entram && (
            <div className="linha">
              <label className="oculto" htmlFor="tag-nova-do-lote">
                Tag nova
              </label>
              <input id="tag-nova-do-lote" value={tagNova} placeholder="Tag nova" autoComplete="off" onChange={(e) => setTagNova(e.target.value)} />
              <button
                type="button"
                className="secundario"
                disabled={!tagNova.trim()}
                onClick={() => {
                  if (!escolhidas.some((t) => chaveDaTag(t) === chaveDaTag(tagNova.trim()))) alternar(tagNova.trim());
                  setTagNova("");
                }}
              >
                Pôr
              </button>
            </div>
          )}
          {acao === "substituir" && escolhidas.length === 0 && <p className="vazio">Sem nenhuma escolhida, as tags saem todas.</p>}
          {acao === "trocar" && (
            <label htmlFor="tag-do-trocar">
              Por
              <input id="tag-do-trocar" list="tags-do-lote" value={por} autoComplete="off" onChange={(e) => mudar(() => setPor(e.target.value))} />
              <datalist id="tags-do-lote">
                {tagsExistentes.map((t) => (
                  <option key={t} value={t} />
                ))}
              </datalist>
            </label>
          )}
        </>
      )}

      {previa && (
        <section className="previa-do-lote" aria-label="Prévia">
          <p>
            <strong>
              {contagem(previa.compras, "compra", "compras")} ({contagem(previa.lancamentos, "lançamento", "lançamentos")})
            </strong>
          </p>
          <p>
            {contagem(previa.mudam, "muda", "mudam")}, {previa.ja_estao_como_pedido} já {previa.ja_estao_como_pedido === 1 ? "está" : "estão"} como pedido.
          </p>
          {previa.de_outro_tipo > 0 && <p className="vazio">{contagem(previa.de_outro_tipo, "fica com as categorias que tem", "ficam com as categorias que têm")}: a categoria pedida é de outro tipo.</p>}
          {previa.trocam_de_item > 0 && <p className="vazio">{contagem(previa.trocam_de_item, "lançamento troca", "lançamentos trocam")} de item do planejamento.</p>}
          {previa.estornos_fora > 0 && <p className="vazio">{contagem(previa.estornos_fora, "estorno fica", "estornos ficam")} de fora: o estorno muda junto com a compra.</p>}
          {previa.amostra.length > 0 && (
            <ul className="lista" aria-label="Antes e depois">
              {previa.amostra.map(({ lancamento, categoria_ids, tags }) => (
                <li key={lancamento.id}>
                  <strong>{tituloDoLancamento(lancamento, categorias)}</strong>
                  <p className="vazio">Antes: {classificacao(lancamento.categoria_ids, lancamento.tags)}</p>
                  <p>Depois: {classificacao(categoria_ids, tags) || "sem categoria"}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {recusa && (
        <p role="alert" className="erro">
          {recusa}
        </p>
      )}
      {!online && <p className="erro">A edição em lote precisa de internet.</p>}
      <div className="acoes">
        {previa && !recusa && previa.mudam > 0 ? (
          <button type="button" disabled={enviando || !online} onClick={() => void aplicar()}>
            Aplicar em {contagem(previa.mudam, "lançamento", "lançamentos")}
          </button>
        ) : (
          <button type="button" disabled={enviando || !online || !completo} onClick={() => void verPrevia()}>
            Ver prévia
          </button>
        )}
        <button type="button" className="secundario" onClick={() => folha.current?.close()}>
          Cancelar
        </button>
      </div>
    </dialog>
  );
}
