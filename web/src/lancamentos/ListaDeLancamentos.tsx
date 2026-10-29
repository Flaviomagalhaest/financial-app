import { useState } from "react";
import {
  atualizadoAs,
  descartarNaoEnviado,
  excluirLancamento,
  lancarDeNovoOExcluido,
  useCadastro,
  useLancamentos,
  type LancamentoNaTela,
} from "../dados";
import { nomePorId as nome, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { dataPorExtenso } from "./datas";

/** Lançamentos do casal, do mais recente ao mais antigo, com editar e excluir em cada linha. */
export function ListaDeLancamentos() {
  const { contas, categorias } = useCadastro();
  const { lancamentos, atualizadoEm, semDados } = useLancamentos();
  const [erro, setErro] = useState("");

  async function excluir(l: LancamentoNaTela) {
    if (!window.confirm(`Excluir "${l.descricao || "este lançamento"}"?`)) return;
    setErro("");
    await excluirLancamento(l).catch(() => setErro("Não foi possível excluir no aparelho."));
  }

  async function lancarDeNovo(l: LancamentoNaTela) {
    setErro("");
    await lancarDeNovoOExcluido(l.id).catch(() => setErro("Não foi possível lançar de novo no aparelho."));
  }

  async function descartar(l: LancamentoNaTela) {
    setErro("");
    await descartarNaoEnviado(l.id).catch(() => setErro("Não foi possível descartar no aparelho."));
  }

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
          const titulo = tituloDoLancamento(l, categorias);
          return (
            <li key={l.id}>
              <div>
                <strong>{titulo}</strong>
                <ValorComSinal l={l} />
              </div>
              <p className="vazio">
                {dataPorExtenso(l.data)} · {nome(contas, l.conta_id)} · {l.categoria_ids.map((c) => nome(categorias, c)).join(", ")}
                {l.situacao === "previsto" && (l.atrasado ? " · previsto, atrasado" : " · previsto")}
              </p>
              {l.conflito ? (
                <p className="erro">⚠ conflito: sua mudança espera decisão</p>
              ) : l.exclusao ? (
                <p className="erro">
                  {l.exclusao.por_voce ? "Você excluiu este lançamento em outro aparelho" : "A outra pessoa excluiu este lançamento"}; sua alteração não foi
                  salva.
                </p>
              ) : (
                l.naoEnviado && <p className={l.recusa ? "erro" : "vazio"}>{l.recusa ? `⏳ não enviado: ${l.recusa}` : "⏳ não enviado"}</p>
              )}
              <div className="acoes">
                {l.conflito ? (
                  <a className="botao" href={`#/conflito/${l.id}`} aria-label={`Decidir ${titulo}`}>
                    Decidir
                  </a>
                ) : l.exclusao ? (
                  <>
                    <button type="button" aria-label={`Lançar de novo ${titulo}`} onClick={() => void lancarDeNovo(l)}>
                      Lançar de novo
                    </button>
                    <button type="button" className="secundario" aria-label={`Dispensar ${titulo}`} onClick={() => void descartar(l)}>
                      Dispensar
                    </button>
                  </>
                ) : (
                  <>
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
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
