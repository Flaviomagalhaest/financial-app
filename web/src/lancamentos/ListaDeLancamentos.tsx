import { useState } from "react";
import { atualizadoAs, descartarNaoEnviado, excluirLancamento, useCadastro, useLancamentos, type LancamentoNaTela } from "../dados";
import { formatarCentavos } from "./dinheiro";

function dataPorExtenso(iso: string): string {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

/** Lançamentos do casal, do mais recente ao mais antigo, com editar e excluir em cada linha. */
export function ListaDeLancamentos() {
  const { contas, categorias } = useCadastro();
  const { lancamentos, atualizadoEm, semDados } = useLancamentos();
  const [erro, setErro] = useState("");

  async function excluir(l: LancamentoNaTela) {
    if (!window.confirm(`Excluir "${l.descricao || "este lançamento"}"?`)) return;
    setErro("");
    await excluirLancamento(l.id).catch(() => setErro("Não foi possível excluir no aparelho."));
  }

  async function descartar(l: LancamentoNaTela) {
    setErro("");
    await descartarNaoEnviado(l.id).catch(() => setErro("Não foi possível descartar no aparelho."));
  }

  const nome = (lista: { id: string; nome: string }[], id: string) => lista.find((i) => i.id === id)?.nome ?? "?";

  return (
    <section>
      <h2>Histórico</h2>
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
      {semDados && lancamentos?.length === 0 && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar os lançamentos.
        </p>
      )}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      {!semDados && lancamentos?.length === 0 && <p className="vazio">Nenhum lançamento ainda.</p>}
      <ul className="lista">
        {lancamentos?.map((l) => {
          const titulo = l.descricao || l.categoria_ids.map((c) => nome(categorias, c)).join(", ");
          return (
            <li key={l.id}>
              <div>
                <strong>{titulo}</strong>
                <span className={l.tipo === "despesa" ? "despesa" : "receita"}>
                  {l.tipo === "despesa" ? "−" : "+"} {formatarCentavos(l.valor_centavos)}
                </span>
              </div>
              <p className="vazio">
                {dataPorExtenso(l.data)} · {nome(contas, l.conta_id)} · {l.categoria_ids.map((c) => nome(categorias, c)).join(", ")}
                {l.situacao === "previsto" && " · previsto"}
              </p>
              {l.naoEnviado && (
                <p className={l.recusa ? "erro" : "vazio"}>{l.recusa ? `⏳ não enviado: ${l.recusa}` : "⏳ não enviado"}</p>
              )}
              <div className="acoes">
                <a className="botao secundario" href={`#/novo/${l.id}`} aria-label={`${l.recusa ? "Corrigir" : "Editar"} ${titulo}`}>
                  {l.recusa ? "Corrigir" : "Editar"}
                </a>
                {l.recusa ? (
                  <button type="button" className="secundario" aria-label={`Descartar ${titulo}`} onClick={() => void descartar(l)}>
                    Descartar
                  </button>
                ) : (
                  <button type="button" className="secundario" aria-label={`Excluir ${titulo}`} onClick={() => void excluir(l)}>
                    Excluir
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
