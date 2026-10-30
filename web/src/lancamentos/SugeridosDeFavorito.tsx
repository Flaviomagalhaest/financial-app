import { useState } from "react";
import { dispensarSugerido, promoverSugerido, useCadastro, useConexao, type Sugerido } from "../dados";
import { nomePorId, tituloDoFavorito } from "./apresentacao";
import { formatarCentavos } from "./dinheiro";

/**
 * O grupo "Sugeridos": os lançamentos mais repetidos que ainda não são favoritos. A ⭐ promove e
 * "Dispensar" tira da lista; os dois precisam de internet (ADR 0011).
 */
export function SugeridosDeFavorito({ sugeridos, aoMudar }: { sugeridos: Sugerido[]; aoMudar: () => void }) {
  const { categorias } = useCadastro();
  const online = useConexao();
  const [erro, setErro] = useState("");
  if (sugeridos.length === 0) return null;

  async function mudar(acao: Promise<string | null>) {
    const motivo = await acao;
    setErro(motivo ? `Não foi possível mudar: ${motivo}.` : "");
    aoMudar();
  }

  return (
    <section aria-labelledby="sugeridos-de-favorito" className="bloco-da-hoje">
      <h3 id="sugeridos-de-favorito">Sugeridos</h3>
      <p className="vazio">Você repete estes lançamentos com frequência. Toque na ⭐ para favoritar.</p>
      <ul className="lista">
        {sugeridos.map((s) => {
          const titulo = tituloDoFavorito(s, categorias);
          return (
            <li key={s.chave}>
              <div>
                <strong>{titulo}</strong>
                <span>{s.usos} usos</span>
              </div>
              <div className="acoes">
                <button type="button" disabled={!online} aria-label={`Favoritar ${titulo}`} onClick={() => void mudar(promoverSugerido(s))}>
                  ⭐ Favoritar · {formatarCentavos(s.valor_centavos)}
                </button>
                <button type="button" className="secundario" disabled={!online} aria-label={`Dispensar ${titulo}`} onClick={() => void mudar(dispensarSugerido(s.chave))}>
                  Dispensar
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {!online && <p className="aviso">Favoritar e dispensar precisam de internet.</p>}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
    </section>
  );
}
