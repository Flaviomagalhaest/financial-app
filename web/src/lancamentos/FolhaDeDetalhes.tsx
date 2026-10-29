import { useEffect, useRef, useState } from "react";
import { chaveDaTag, type LancamentoNaTela, type Pessoa } from "../dados";
import { EscolhaDaData } from "./EscolhaDaData";

type Situacao = LancamentoNaTela["situacao"];

type Props = {
  descricao: string;
  onDescricao: (descricao: string) => void;
  tags: string[];
  /** As tags que se pode escolher; as marcadas aparecem mesmo fora dela. */
  opcoesDeTags: string[];
  onTags: (tags: string[]) => void;
  pessoas: Pessoa[];
  pessoa: string | null;
  onPessoa: (pessoa: string | null) => void;
  data: string;
  onData: (data: string) => void;
  situacao: Situacao;
  onSituacao: (situacao: Situacao) => void;
  onFechar: () => void;
};

const mesmaTag = (a: string, b: string) => chaveDaTag(a) === chaveDaTag(b);

/** Folha de baixo com o que é opcional no lançamento: descrição, tags, pessoa, data e "Repete?". */
export function FolhaDeDetalhes(props: Props) {
  const folha = useRef<HTMLDialogElement>(null);
  const [novaTag, setNovaTag] = useState("");

  useEffect(() => {
    folha.current?.showModal();
  }, []);

  const marcada = (tag: string) => props.tags.some((t) => mesmaTag(t, tag));
  // As marcadas vêm primeiro: a fileira rola de lado, e a tag recém-criada fica à vista.
  const opcoes = [...props.tags, ...props.opcoesDeTags.filter((o) => !marcada(o))];

  function alternar(tag: string) {
    props.onTags(marcada(tag) ? props.tags.filter((t) => !mesmaTag(t, tag)) : [...props.tags, tag]);
  }

  function criarTag() {
    const nome = novaTag.trim();
    if (!nome) return;
    // A tag que já existe com outra caixa é a mesma: marca a existente.
    const existente = opcoes.find((o) => mesmaTag(o, nome)) ?? nome;
    if (!marcada(existente)) props.onTags([...props.tags, existente]);
    setNovaTag("");
  }

  return (
    <dialog
      ref={folha}
      className="folha"
      aria-labelledby="titulo-dos-detalhes"
      onClose={props.onFechar}
      // Tocar no fundo escurecido, fora da folha, fecha como "Pronto".
      onClick={(e) => {
        // O fundo entrega o clique ao próprio diálogo; o lado de dentro dele, não.
        if (e.target !== e.currentTarget) return;
        const r = e.currentTarget.getBoundingClientRect();
        if (e.clientY < r.top || e.clientY > r.bottom || e.clientX < r.left || e.clientX > r.right) folha.current?.close();
      }}
    >
      <h3 id="titulo-dos-detalhes">Detalhes</h3>
      <label htmlFor="descricao">Descrição</label>
      <input id="descricao" value={props.descricao} onChange={(e) => props.onDescricao(e.target.value)} autoComplete="off" />

      <h4>Tags</h4>
      {opcoes.length > 0 && (
        <div className="fileira rolavel">
          {opcoes.map((tag) => (
            <button type="button" key={tag} className={`ficha${marcada(tag) ? " marcada" : ""}`} aria-pressed={marcada(tag)} onClick={() => alternar(tag)}>
              #{tag}
            </button>
          ))}
        </div>
      )}
      <div className="linha">
        <label className="oculto" htmlFor="nova-tag">
          Nova tag
        </label>
        <input
          id="nova-tag"
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
      <div className={`alternancia${props.pessoas.length === 2 ? " tres" : ""}`} role="group" aria-label="Pessoa">
        {[{ id: null, nome: "Conjunto" }, ...props.pessoas].map((pessoa) => (
          <button type="button" key={pessoa.id ?? "conjunto"} className={props.pessoa === pessoa.id ? "" : "secundario"} aria-pressed={props.pessoa === pessoa.id} onClick={() => props.onPessoa(pessoa.id)}>
            {pessoa.nome}
          </button>
        ))}
      </div>

      <h4>Data</h4>
      <EscolhaDaData data={props.data} onMudar={props.onData} />
      <div className="alternancia" role="group" aria-label="Situação">
        {(["realizado", "previsto"] as const).map((s) => (
          <button type="button" key={s} className={props.situacao === s ? "" : "secundario"} aria-pressed={props.situacao === s} onClick={() => props.onSituacao(s)}>
            {s === "realizado" ? "Realizado" : "Previsto"}
          </button>
        ))}
      </div>

      <h4>Repete?</h4>
      <div className="alternancia tres" role="group" aria-label="Repete?">
        <button type="button" aria-pressed="true">
          Uma vez
        </button>
        <button type="button" className="secundario" aria-pressed="false" disabled>
          Parcelado
        </button>
        <button type="button" className="secundario" aria-pressed="false" disabled>
          Recorrente
        </button>
      </div>
      <p className="vazio">Parcelado e recorrente ainda não estão disponíveis.</p>

      <button type="button" onClick={() => folha.current?.close()}>
        Pronto
      </button>
    </dialog>
  );
}
