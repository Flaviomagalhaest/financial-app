import { useId, useState } from "react";
import { chaveDaTag } from "../dados";

const mesmaTag = (a: string, b: string) => chaveDaTag(a) === chaveDaTag(b);

type Props = {
  /** As tags marcadas. */
  tags: string[];
  /** As tags que se pode escolher; as marcadas aparecem mesmo fora dela. */
  opcoes: string[];
  onTags: (tags: string[]) => void;
  /** No estorno, as tags são as da compra e não mudam. */
  travadas?: boolean;
};

/** As tags para marcar e desmarcar e o campo "Nova tag". */
export function SeletorDeTags({ tags, opcoes, onTags, travadas }: Props) {
  const [novaTag, setNovaTag] = useState("");
  const idDoCampo = useId();
  const marcada = (tag: string) => tags.some((t) => mesmaTag(t, tag));
  // As marcadas vêm primeiro: a fileira rola de lado, e a tag recém-criada fica à vista.
  const todas = [...tags, ...(travadas ? [] : opcoes.filter((o) => !marcada(o)))];

  function alternar(tag: string) {
    onTags(marcada(tag) ? tags.filter((t) => !mesmaTag(t, tag)) : [...tags, tag]);
  }

  function criarTag() {
    const nome = novaTag.trim();
    if (!nome) return;
    // A tag que já existe com outra caixa é a mesma: marca a existente.
    const existente = todas.find((o) => mesmaTag(o, nome)) ?? nome;
    if (!marcada(existente)) onTags([...tags, existente]);
    setNovaTag("");
  }

  return (
    <>
      {todas.length > 0 && (
        <div className="fileira rolavel">
          {todas.map((tag) => (
            <button type="button" key={tag} className={`ficha${marcada(tag) ? " marcada" : ""}`} aria-pressed={marcada(tag)} disabled={travadas} onClick={() => alternar(tag)}>
              #{tag}
            </button>
          ))}
        </div>
      )}
      {!travadas && (
        <div className="linha">
          <label className="oculto" htmlFor={idDoCampo}>
            Nova tag
          </label>
          <input
            id={idDoCampo}
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
      )}
    </>
  );
}
