import { useState } from "react";
import { removerFavorito, reordenarFavoritos, useCadastro, useConexao, useFavoritos } from "../dados";
import { nomePorId } from "../lancamentos/apresentacao";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { SugeridosDeFavorito } from "../lancamentos/SugeridosDeFavorito";

/** Reordenar e remover favoritos: mudança de cadastro, só com internet (ADR 0011). */
export function TelaDeFavoritos() {
  const { favoritos, sugeridos, carregado, semDados, recarregar } = useFavoritos();
  const { categorias, contasECartoes } = useCadastro();
  const online = useConexao();
  const [erro, setErro] = useState("");

  async function mudar(acao: Promise<string | null>) {
    const motivo = await acao;
    setErro(motivo ? `Não foi possível mudar: ${motivo}.` : "");
    recarregar();
  }

  function mover(indice: number, deslocamento: -1 | 1) {
    const ids = favoritos.map((f) => f.id);
    [ids[indice], ids[indice + deslocamento]] = [ids[indice + deslocamento], ids[indice]];
    void mudar(reordenarFavoritos(ids));
  }

  return (
    <section className="configuracoes">
      <h2>Favoritos</h2>
      <a href="#/configuracoes">Configurações</a>
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar os favoritos.
        </p>
      )}
      {carregado && favoritos.length === 0 && (
        <p className="vazio">Nenhum favorito ainda. Marque a ⭐ ao lançar, ou favorite um dos sugeridos.</p>
      )}
      <ul className="lista" aria-label="Favoritos">
        {favoritos.map((f, i) => {
          const titulo = f.descricao || f.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ");
          return (
            <li key={f.id}>
              <div>
                <strong>{titulo}</strong>
                <span>{formatarCentavos(f.valor_padrao_centavos)}</span>
              </div>
              <p className="vazio">
                {f.categoria_ids.map((c) => nomePorId(categorias, c)).join(", ")} · {nomePorId(contasECartoes, f.conta_id)}
              </p>
              <div className="acoes">
                <button type="button" className="secundario" disabled={!online || i === 0} aria-label={`Subir ${titulo}`} onClick={() => mover(i, -1)}>
                  ↑
                </button>
                <button type="button" className="secundario" disabled={!online || i === favoritos.length - 1} aria-label={`Descer ${titulo}`} onClick={() => mover(i, 1)}>
                  ↓
                </button>
                <button type="button" className="secundario" disabled={!online} aria-label={`Remover ${titulo}`} onClick={() => void mudar(removerFavorito(f.id))}>
                  Remover
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {!online && <p className="aviso">Reordenar e remover precisam de internet.</p>}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <SugeridosDeFavorito sugeridos={sugeridos} aoMudar={recarregar} />
    </section>
  );
}
