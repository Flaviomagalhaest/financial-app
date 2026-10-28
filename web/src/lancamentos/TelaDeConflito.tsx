import { useState } from "react";
import {
  decidir,
  descartarNaoEnviado,
  excluirApesarDoConflito,
  useCadastro,
  useFila,
  type Campo,
  type Categoria,
  type Conflito,
  type Conta,
  type NovoLancamento,
} from "../dados";
import { nomePorId as nome } from "./apresentacao";
import { dataPorExtenso, hoje } from "./datas";
import { formatarCentavos } from "./dinheiro";

const ROTULOS: Record<Campo, string> = {
  tipo: "Tipo",
  situacao: "Situação",
  valor_centavos: "Valor",
  data: "Data",
  descricao: "Descrição",
  conta_id: "Conta",
  categoria_ids: "Categorias",
  tags: "Tags",
};

function valorDoCampo(campo: Campo, l: NovoLancamento, contas: Conta[], categorias: Categoria[]): string {
  switch (campo) {
    case "tipo":
      return l.tipo === "despesa" ? "Despesa" : "Receita";
    case "situacao":
      return l.situacao === "previsto" ? "Previsto" : "Realizado";
    case "valor_centavos":
      return formatarCentavos(l.valor_centavos);
    case "data":
      return dataPorExtenso(l.data);
    case "descricao":
      return l.descricao || "(sem descrição)";
    case "conta_id":
      return nome(contas, l.conta_id);
    case "categoria_ids":
      return l.categoria_ids.map((c) => nome(categorias, c)).join(", ");
    case "tags":
      return l.tags.length ? l.tags.join(", ") : "(sem tags)";
  }
}

/** "às 14:32", ou "em 13/10 às 14:32" se não foi hoje. */
function quando(iso: string): string {
  const em = new Date(iso);
  const hora = em.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const dia = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(em);
  return dia === hoje() ? `às ${hora}` : `em ${dataPorExtenso(dia).slice(0, 5)} às ${hora}`;
}

/** De onde veio o outro lado: a outra pessoa, você em outro aparelho ou uma regra do app. */
function outroLado(c: Conflito["campos"][number]): string {
  const quem = c.origem ? `O da regra ${c.origem}` : c.por_voce ? "O seu, de outro aparelho" : "O da outra pessoa";
  return `${quem}, ${quando(c.alterado_em)}`;
}

/** Decide o conflito campo a campo, ou descarta a mudança do aparelho (ADR 0011). */
export function TelaDeConflito({ id }: { id: string }) {
  const { contas, categorias } = useCadastro();
  const item = useFila().find((i) => i.id === id);
  const [escolhas, setEscolhas] = useState<Partial<Record<Campo, "meu" | "deles">>>({});
  const [erro, setErro] = useState("");

  async function fazer(acao: () => Promise<void>) {
    setErro("");
    try {
      await acao();
      window.location.hash = "#/historico";
    } catch {
      setErro("Não foi possível guardar a decisão no aparelho.");
    }
  }

  if (!item?.conflito) {
    return (
      <section>
        <h2>Conflito</h2>
        <p className="vazio">Este lançamento não tem conflito para decidir.</p>
        <a href="#/historico">Voltar ao Histórico</a>
      </section>
    );
  }
  const { lancamento: servidor, campos } = item.conflito;

  if (item.acao === "excluir") {
    const ultimo = campos.reduce((a, b) => (a.alterado_em > b.alterado_em ? a : b), campos[0]);
    return (
      <section className="conflito">
        <h2>Excluir mesmo assim?</h2>
        <p>
          {ultimo?.por_voce ? "Você alterou este lançamento em outro aparelho" : "A outra pessoa alterou este lançamento"} depois da versão que você
          excluiu{campos.length > 0 && `: ${campos.map((c) => ROTULOS[c.campo].toLowerCase()).join(", ")}`}.
        </p>
        <ul className="lista">
          {campos.map((c) => (
            <li key={c.campo}>
              <div>
                <strong>{ROTULOS[c.campo]}</strong>
                <span>{valorDoCampo(c.campo, servidor, contas, categorias)}</span>
              </div>
            </li>
          ))}
        </ul>
        {erro && (
          <p role="alert" className="erro">
            {erro}
          </p>
        )}
        <div className="acoes">
          <button type="button" onClick={() => void fazer(() => excluirApesarDoConflito(id))}>
            Excluir mesmo assim
          </button>
          <button type="button" className="secundario" onClick={() => void fazer(() => descartarNaoEnviado(id))}>
            Manter o lançamento
          </button>
        </div>
      </section>
    );
  }

  const meu = item.lancamento!;
  const decidido = campos.every((c) => escolhas[c.campo]);
  return (
    <section className="conflito">
      <h2>Conflito</h2>
      <p>Você e o outro lado mudaram os mesmos campos deste lançamento. Escolha qual valor fica em cada um; o resto da sua mudança entra junto.</p>
      {campos.map((c) => (
        <div key={c.campo} className="campo-em-conflito" role="group" aria-label={ROTULOS[c.campo]}>
          <h3>{ROTULOS[c.campo]}</h3>
          <button
            type="button"
            className={`ficha${escolhas[c.campo] === "meu" ? " marcada" : ""}`}
            aria-pressed={escolhas[c.campo] === "meu"}
            onClick={() => setEscolhas({ ...escolhas, [c.campo]: "meu" })}
          >
            O seu: {valorDoCampo(c.campo, meu, contas, categorias)}
          </button>
          <button
            type="button"
            className={`ficha${escolhas[c.campo] === "deles" ? " marcada" : ""}`}
            aria-pressed={escolhas[c.campo] === "deles"}
            onClick={() => setEscolhas({ ...escolhas, [c.campo]: "deles" })}
          >
            {outroLado(c)}: {valorDoCampo(c.campo, servidor, contas, categorias)}
          </button>
        </div>
      ))}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <div className="acoes">
        <button
          type="button"
          disabled={!decidido}
          onClick={() => void fazer(() => decidir(id, campos.filter((c) => escolhas[c.campo] === "meu").map((c) => c.campo)))}
        >
          Salvar a decisão
        </button>
        <button type="button" className="secundario" onClick={() => void fazer(() => descartarNaoEnviado(id))}>
          Descartar a minha mudança
        </button>
      </div>
    </section>
  );
}
