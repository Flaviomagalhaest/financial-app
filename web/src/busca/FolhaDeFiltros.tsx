import { useEffect, useRef, useState } from "react";
import { useCadastro, usePessoas, useTags, type Criterios } from "../dados";
import { emCentavos } from "../lancamentos/dinheiro";
import { SITUACOES, TIPOS } from "./apresentacao";

type Lista = "categoria_ids" | "tags" | "conta_ids" | "pessoas" | "situacoes" | "tipos";

/** Liga ou desliga um valor num filtro de lista; a lista vazia não filtra. */
function alternado(criterios: Criterios, campo: Lista, valor: string): Criterios {
  const atual = (criterios[campo] ?? []) as string[];
  return { ...criterios, [campo]: atual.includes(valor) ? atual.filter((v) => v !== valor) : [...atual, valor] };
}

/** Fichas de um filtro: dentro dele é OU. */
function Fichas({ nome, opcoes, marcada, onAlternar }: { nome: string; opcoes: { valor: string; rotulo: string }[]; marcada: (valor: string) => boolean; onAlternar: (valor: string) => void }) {
  return (
    <div className="fileira" role="group" aria-label={nome}>
      {opcoes.map((o) => (
        <button type="button" key={o.valor} className={`ficha${marcada(o.valor) ? " marcada" : ""}`} aria-pressed={marcada(o.valor)} onClick={() => onAlternar(o.valor)}>
          {o.rotulo}
        </button>
      ))}
    </div>
  );
}

/** Um campo de valor em reais, que só muda o critério quando o texto é um valor (ou fica vazio). */
function CampoDeValor({ id, rotulo, centavos, onMudar }: { id: string; rotulo: string; centavos?: number | null; onMudar: (centavos: number | undefined) => void }) {
  const [texto, setTexto] = useState(centavos == null ? "" : (centavos / 100).toFixed(2).replace(".", ","));
  return (
    <label htmlFor={id}>
      {rotulo}
      <input
        id={id}
        inputMode="decimal"
        value={texto}
        placeholder="R$"
        onChange={(e) => {
          setTexto(e.target.value);
          const valor = emCentavos(e.target.value);
          if (valor !== undefined) onMudar(valor ?? undefined);
        }}
      />
    </label>
  );
}

/** A folha com os filtros combinados da busca (ticket 24): entre filtros é E, dentro de um filtro é OU. */
export function FolhaDeFiltros({ criterios, onMudar, onFechar }: { criterios: Criterios; onMudar: (criterios: Criterios) => void; onFechar: () => void }) {
  const folha = useRef<HTMLDialogElement>(null);
  const { contasECartoes, cartoes, categorias } = useCadastro();
  const { pessoas } = usePessoas();
  const tags = useTags();
  useEffect(() => folha.current?.showModal(), []);

  const marcada = (campo: Lista) => (valor: string) => ((criterios[campo] ?? []) as string[]).includes(valor);
  const alternar = (campo: Lista) => (valor: string) => onMudar(alternado(criterios, campo, valor));
  const marca = (campo: "sem_categoria" | "sem_tag" | "conjunto") => ({
    marcada: () => !!criterios[campo],
    onAlternar: () => onMudar({ ...criterios, [campo]: !criterios[campo] }),
  });
  const titulares = cartoes.filter((c) => !c.titular_id);

  return (
    <dialog ref={folha} className="folha filtros-da-busca" aria-labelledby="titulo-dos-filtros" onClose={onFechar}>
      <h3 id="titulo-dos-filtros">Filtros</h3>
      <p className="vazio">Entre filtros vale tudo junto; dentro de um filtro, qualquer um dos escolhidos.</p>

      <h4>Tipo</h4>
      <Fichas
        nome="Tipo"
        opcoes={Object.entries(TIPOS).map(([valor, rotulo]) => ({ valor, rotulo }))}
        marcada={marcada("tipos")}
        onAlternar={alternar("tipos")}
      />
      <p className="vazio">O pagamento de fatura só aparece com Transferência.</p>

      <h4>Situação</h4>
      <Fichas
        nome="Situação"
        opcoes={Object.entries(SITUACOES).map(([valor, rotulo]) => ({ valor, rotulo }))}
        marcada={marcada("situacoes")}
        onAlternar={alternar("situacoes")}
      />

      <h4>Período</h4>
      <p className="vazio">Pela data da compra.</p>
      <div className="alternancia">
        <label htmlFor="periodo-de">
          De
          <input id="periodo-de" type="date" value={criterios.periodo_de ?? ""} onChange={(e) => onMudar({ ...criterios, periodo_de: e.target.value || undefined })} />
        </label>
        <label htmlFor="periodo-ate">
          Até
          <input id="periodo-ate" type="date" value={criterios.periodo_ate ?? ""} onChange={(e) => onMudar({ ...criterios, periodo_ate: e.target.value || undefined })} />
        </label>
      </div>

      <h4>Fatura</h4>
      <p className="vazio">Pelo mês da fatura, como na aba Mês; sem cartão, o mês em que cada lançamento conta.</p>
      <div className="alternancia">
        <label htmlFor="fatura-mes">
          Mês
          <input
            id="fatura-mes"
            type="month"
            value={criterios.fatura?.mes.slice(0, 7) ?? ""}
            onChange={(e) => onMudar({ ...criterios, fatura: e.target.value ? { mes: `${e.target.value}-01`, cartao_id: criterios.fatura?.cartao_id } : undefined })}
          />
        </label>
        <label htmlFor="fatura-cartao">
          Cartão
          <select
            id="fatura-cartao"
            value={criterios.fatura?.cartao_id ?? ""}
            disabled={!criterios.fatura}
            onChange={(e) => criterios.fatura && onMudar({ ...criterios, fatura: { mes: criterios.fatura.mes, cartao_id: e.target.value || undefined } })}
          >
            <option value="">Todos</option>
            {titulares.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
      </div>

      <h4>Valor</h4>
      <div className="alternancia">
        <CampoDeValor id="valor-minimo" rotulo="Mínimo" centavos={criterios.valor_minimo_centavos} onMudar={(c) => onMudar({ ...criterios, valor_minimo_centavos: c })} />
        <CampoDeValor id="valor-maximo" rotulo="Máximo" centavos={criterios.valor_maximo_centavos} onMudar={(c) => onMudar({ ...criterios, valor_maximo_centavos: c })} />
      </div>

      <h4>Categorias</h4>
      <Fichas nome="Categorias" opcoes={categorias.map((c) => ({ valor: c.id, rotulo: c.nome }))} marcada={marcada("categoria_ids")} onAlternar={alternar("categoria_ids")} />
      <Fichas nome="Sem categoria" opcoes={[{ valor: "sem", rotulo: "Sem categoria" }]} {...marca("sem_categoria")} />

      <h4>Tags</h4>
      <Fichas nome="Tags" opcoes={tags.map((t) => ({ valor: t, rotulo: `#${t}` }))} marcada={marcada("tags")} onAlternar={alternar("tags")} />
      <Fichas nome="Sem tag" opcoes={[{ valor: "sem", rotulo: "Sem tag" }]} {...marca("sem_tag")} />

      <h4>Conta ou cartão</h4>
      <Fichas nome="Conta ou cartão" opcoes={contasECartoes.map((c) => ({ valor: c.id, rotulo: c.nome }))} marcada={marcada("conta_ids")} onAlternar={alternar("conta_ids")} />

      <h4>Pessoa</h4>
      <div className="fileira">
        <Fichas nome="Conjunto" opcoes={[{ valor: "conjunto", rotulo: "Conjunto" }]} {...marca("conjunto")} />
        <Fichas nome="Pessoa" opcoes={pessoas.map((p) => ({ valor: p.id, rotulo: p.nome }))} marcada={marcada("pessoas")} onAlternar={alternar("pessoas")} />
      </div>

      <div className="acoes-em-linha">
        <button type="button" onClick={() => folha.current?.close()}>
          Pronto
        </button>
        <button type="button" className="secundario" onClick={() => onMudar({ texto: criterios.texto, ordem: criterios.ordem })}>
          Limpar filtros
        </button>
      </div>
    </dialog>
  );
}
