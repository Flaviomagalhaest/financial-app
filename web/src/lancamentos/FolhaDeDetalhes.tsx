import { useEffect, useRef, useState } from "react";
import { chaveDaTag, type LancamentoNaTela, type Pessoa } from "../dados";
import { EscolhaDaData } from "./EscolhaDaData";
import { RECORRENCIA_PADRAO, type RecorrenciaNaFolha } from "./recorrencia";

type Situacao = LancamentoNaTela["situacao"];

/** Uma sugestão pela descrição, já com o texto que a tela mostra. */
export type SugestaoNaFolha = { descricao: string; resumo: string; onEscolher: () => void };

type Props = {
  descricao: string;
  onDescricao: (descricao: string) => void;
  /** As sugestões para o que se digitou na descrição, da mais provável para a menos. */
  sugestoes: SugestaoNaFolha[];
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
  /** Só na compra no cartão: a fatura escolhida à mão (`null` é a da data) e as que se pode escolher. */
  fatura?: { mes: string | null; opcoes: string[]; onMudar: (mes: string | null) => void };
  /**
   * Só no lançamento novo: "Repete?". Sem repetição (`null`) é uma vez só; com ela, salvar cria a
   * recorrência que começa na data, e situação e fatura ficam por conta da regra.
   */
  recorrencia?: { valor: RecorrenciaNaFolha | null; problema: string | null; onMudar: (recorrencia: RecorrenciaNaFolha | null) => void };
  onFechar: () => void;
};

/** O número digitado; vazio vira 0, que a validação recusa. */
const numero = (texto: string) => (texto === "" ? 0 : Number(texto));

const mesmaTag = (a: string, b: string) => chaveDaTag(a) === chaveDaTag(b);

/** Folha de baixo com o que é opcional no lançamento: descrição, tags, pessoa, data e "Repete?". */
export function FolhaDeDetalhes(props: Props) {
  const folha = useRef<HTMLDialogElement>(null);
  const [novaTag, setNovaTag] = useState("");

  useEffect(() => {
    folha.current?.showModal();
  }, []);

  const marcada = (tag: string) => props.tags.some((t) => mesmaTag(t, tag));
  const recorrencia = props.recorrencia?.valor ?? null;
  const mudarRecorrencia = (mudanca: Partial<RecorrenciaNaFolha>) => recorrencia && props.recorrencia?.onMudar({ ...recorrencia, ...mudanca });
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
      {props.sugestoes.length > 0 && (
        <ul className="sugestoes" aria-label="Sugestões">
          {props.sugestoes.map((s, i) => (
            <li key={i}>
              <button type="button" className="sugestao" onClick={s.onEscolher}>
                <span>{s.descricao}</span>
                <span className="resumo-da-sugestao">{s.resumo}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

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

      <h4>{recorrencia ? "Primeira vez" : "Data"}</h4>
      <EscolhaDaData data={props.data} onMudar={props.onData} />
      {!recorrencia && (
        <div className="alternancia" role="group" aria-label="Situação">
          {(["realizado", "previsto"] as const).map((s) => (
            <button type="button" key={s} className={props.situacao === s ? "" : "secundario"} aria-pressed={props.situacao === s} onClick={() => props.onSituacao(s)}>
              {s === "realizado" ? "Realizado" : "Previsto"}
            </button>
          ))}
        </div>
      )}

      {props.fatura && !recorrencia && (
        <>
          <h4>Fatura</h4>
          <div className="alternancia quatro" role="group" aria-label="Fatura">
            {[null, ...props.fatura.opcoes].map((mes) => (
              <button
                type="button"
                key={mes ?? "pela-data"}
                className={props.fatura?.mes === mes ? "" : "secundario"}
                aria-pressed={props.fatura?.mes === mes}
                onClick={() => props.fatura?.onMudar(mes)}
              >
                {mes ? `${mes.slice(5, 7)}/${mes.slice(0, 4)}` : "Pela data"}
              </button>
            ))}
          </div>
        </>
      )}

      {props.recorrencia && (
        <>
          <h4>Repete?</h4>
          <div className="alternancia tres" role="group" aria-label="Repete?">
            <button type="button" className={recorrencia ? "secundario" : ""} aria-pressed={!recorrencia} onClick={() => props.recorrencia?.onMudar(null)}>
              Uma vez
            </button>
            <button type="button" className="secundario" aria-pressed="false" disabled>
              Parcelado
            </button>
            <button type="button" className={recorrencia ? "" : "secundario"} aria-pressed={!!recorrencia} onClick={() => props.recorrencia?.onMudar(recorrencia ?? RECORRENCIA_PADRAO)}>
              Recorrente
            </button>
          </div>
          {!recorrencia && <p className="vazio">Parcelado ainda não está disponível.</p>}
        </>
      )}
      {recorrencia && (
        <>
          <div className="linha">
            <label htmlFor="a-cada">A cada</label>
            <input id="a-cada" type="number" inputMode="numeric" min={1} value={recorrencia.aCada || ""} onChange={(e) => mudarRecorrencia({ aCada: numero(e.target.value) })} />
          </div>
          <div className="alternancia" role="group" aria-label="Unidade">
            {(["semanas", "meses"] as const).map((u) => (
              <button type="button" key={u} className={recorrencia.unidade === u ? "" : "secundario"} aria-pressed={recorrencia.unidade === u} onClick={() => mudarRecorrencia({ unidade: u })}>
                {u === "semanas" ? "Semanas" : "Meses"}
              </button>
            ))}
          </div>
          <p className="vazio">Anual é a cada 12 meses.</p>

          <h4>Termina</h4>
          <div className="alternancia tres" role="group" aria-label="Termina">
            {(
              [
                ["nunca", "Nunca"],
                ["data", "Numa data"],
                ["vezes", "Depois de"],
              ] as const
            ).map(([fim, nome]) => (
              <button type="button" key={fim} className={recorrencia.fim === fim ? "" : "secundario"} aria-pressed={recorrencia.fim === fim} onClick={() => mudarRecorrencia({ fim })}>
                {nome}
              </button>
            ))}
          </div>
          {recorrencia.fim === "data" && (
            <div className="linha">
              <label htmlFor="ate">Última data</label>
              <input id="ate" type="date" min={props.data} value={recorrencia.ate} onChange={(e) => mudarRecorrencia({ ate: e.target.value })} />
            </div>
          )}
          {recorrencia.fim === "vezes" && (
            <div className="linha">
              <input id="vezes" type="number" inputMode="numeric" min={1} value={recorrencia.vezes || ""} onChange={(e) => mudarRecorrencia({ vezes: numero(e.target.value) })} />
              <label htmlFor="vezes">vezes</label>
            </div>
          )}

          <h4>Valor</h4>
          <div className="alternancia" role="group" aria-label="Valor">
            {(["fixo", "estimado"] as const).map((t) => (
              <button type="button" key={t} className={recorrencia.tipoDoValor === t ? "" : "secundario"} aria-pressed={recorrencia.tipoDoValor === t} onClick={() => mudarRecorrencia({ tipoDoValor: t })}>
                {t === "fixo" ? "Fixo" : "Estimado"}
              </button>
            ))}
          </div>
          {recorrencia.tipoDoValor === "fixo" ? (
            <label className="caixa" htmlFor="automatico">
              <input id="automatico" type="checkbox" checked={recorrencia.automatico} onChange={(e) => mudarRecorrencia({ automatico: e.target.checked })} />
              Automático: vira realizado sozinho na data, sem confirmar
            </label>
          ) : (
            <p className="vazio">O estimado (a luz, o salário) sempre pede confirmação.</p>
          )}
          {props.recorrencia?.problema && <p className="erro">{props.recorrencia.problema}</p>}
        </>
      )}

      <button type="button" onClick={() => folha.current?.close()}>
        Pronto
      </button>
    </dialog>
  );
}
