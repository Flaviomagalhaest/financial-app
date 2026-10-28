import { useCallback, useEffect, useState } from "react";
import { api } from "../api/cliente";
import { nomePorId as nome, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { dataPorExtenso } from "./datas";
import { useCadastro, type Lancamento } from "./useCadastro";

/** Lançamentos do casal, do mais recente ao mais antigo, com editar e excluir em cada linha. */
export function ListaDeLancamentos() {
  const { contas, categorias } = useCadastro();
  const [lancamentos, setLancamentos] = useState<Lancamento[] | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.GET("/api/lancamentos");
      if (data) setLancamentos(data);
      else setErro("Não foi possível carregar os lançamentos.");
    } catch {
      setErro("Sem internet: não foi possível carregar os lançamentos.");
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function excluir(l: Lancamento) {
    if (!window.confirm(`Excluir "${l.descricao || "este lançamento"}"?`)) return;
    setErro("");
    try {
      const { response } = await api.DELETE("/api/lancamentos/{id}", { params: { path: { id: l.id } } });
      if (!response.ok) return setErro("O servidor recusou a exclusão.");
      await carregar();
    } catch {
      setErro("Sem internet: excluir precisa de internet.");
    }
  }

  return (
    <section>
      <h2>Histórico</h2>
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      {lancamentos?.length === 0 && <p className="vazio">Nenhum lançamento ainda.</p>}
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
              <div className="acoes">
                <a className="botao secundario" href={`#/novo/${l.id}`} aria-label={`Editar ${titulo}`}>
                  Editar
                </a>
                <button type="button" className="secundario" aria-label={`Excluir ${titulo}`} onClick={() => void excluir(l)}>
                  Excluir
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
