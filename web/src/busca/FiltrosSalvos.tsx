import { useState } from "react";
import { excluirFiltro, renomearFiltro, salvarFiltro, useFiltrosSalvos, type Criterios, type FiltroSalvo } from "../dados";
import { pedidoDaBusca } from "../dados/busca";

const PERIODOS = {
  fixo: "Período como está",
  este_mes: "Este mês",
  mes_passado: "Mês passado",
  este_ano: "Este ano",
  ultimos_30_dias: "Últimos 30 dias",
} as const;
type Periodo = keyof typeof PERIODOS;

/**
 * Os filtros salvos do casal (ticket 60): tocar num filtro aplica os critérios, a ordem e o período
 * (o relativo já vem resolvido de hoje). Salvar, renomear e excluir precisam de internet.
 */
export function FiltrosSalvos({ criterios, onAplicar }: { criterios: Criterios; onAplicar: (c: Criterios) => void }) {
  const { filtros } = useFiltrosSalvos();
  const [salvando, setSalvando] = useState(false);
  const [nome, setNome] = useState("");
  const [periodo, setPeriodo] = useState<Periodo>("fixo");
  const [aberto, setAberto] = useState<FiltroSalvo | null>(null);
  const [novoNome, setNovoNome] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const resolver = async (pedido: Promise<string | null>, depois: () => void) => {
    const motivo = await pedido;
    setErro(motivo);
    if (motivo === null) depois();
  };

  const salvar = () => {
    const { ordem, pagina: _pagina, ...dosCriterios } = pedidoDaBusca(criterios, 0);
    return resolver(
      salvarFiltro({
        id: crypto.randomUUID(),
        nome,
        criterios: dosCriterios,
        ordem,
        periodo_relativo: periodo === "fixo" ? null : periodo,
      }),
      () => {
        setSalvando(false);
        setNome("");
        setPeriodo("fixo");
      },
    );
  };

  return (
    <div className="filtros-salvos">
      {filtros.length > 0 && (
        <ul className="fileira" aria-label="Filtros salvos">
          {filtros.map((f) => (
            <li key={f.id}>
              <button type="button" className="ficha" onClick={() => onAplicar(f.pedido)}>
                {f.nome}
              </button>
              <button
                type="button"
                className="secundario"
                aria-label={`Gerenciar o filtro ${f.nome}`}
                onClick={() => {
                  setAberto(f);
                  setNovoNome(f.nome);
                  setErro(null);
                }}
              >
                ⋯
              </button>
            </li>
          ))}
        </ul>
      )}
      {aberto && (
        <form
          className="linha"
          aria-label={`Filtro ${aberto.nome}`}
          onSubmit={(e) => {
            e.preventDefault();
            void resolver(renomearFiltro(aberto.id, novoNome), () => setAberto(null));
          }}
        >
          <label className="oculto" htmlFor="novo-nome-do-filtro">
            Novo nome do filtro
          </label>
          <input id="novo-nome-do-filtro" value={novoNome} onChange={(e) => setNovoNome(e.target.value)} />
          <button type="submit">Renomear</button>
          <button type="button" className="secundario" onClick={() => void resolver(excluirFiltro(aberto.id), () => setAberto(null))}>
            Excluir
          </button>
          <button type="button" className="secundario" onClick={() => setAberto(null)}>
            Fechar
          </button>
        </form>
      )}
      {salvando ? (
        <form
          className="linha"
          aria-label="Salvar esta busca"
          onSubmit={(e) => {
            e.preventDefault();
            void salvar();
          }}
        >
          <label className="oculto" htmlFor="nome-do-filtro">
            Nome do filtro
          </label>
          <input id="nome-do-filtro" value={nome} placeholder="Nome do filtro" autoComplete="off" onChange={(e) => setNome(e.target.value)} />
          <label className="oculto" htmlFor="periodo-do-filtro">
            Período do filtro
          </label>
          <select id="periodo-do-filtro" value={periodo} onChange={(e) => setPeriodo(e.target.value as Periodo)}>
            {Object.entries(PERIODOS).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
          <button type="submit" disabled={!nome.trim()}>
            Salvar
          </button>
          <button type="button" className="secundario" onClick={() => setSalvando(false)}>
            Cancelar
          </button>
        </form>
      ) : (
        <button type="button" className="secundario" onClick={() => { setSalvando(true); setErro(null); }}>
          Salvar esta busca
        </button>
      )}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
    </div>
  );
}
