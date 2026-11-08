import { useCadastro, useFavoritos } from "../dados";
import { tituloDoFavorito } from "../lancamentos/apresentacao";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { SugeridosDeFavorito } from "../lancamentos/SugeridosDeFavorito";

/**
 * Na Hoje, os mesmos favoritos da fileira do novo lançamento, em grade; tocar abre o lançamento já
 * preenchido. Com os atalhos da faixa ligados (`semGrade`), eles estão nas pílulas e só os sugeridos ficam.
 */
export function GradeDeFavoritos({ semGrade = false }: { semGrade?: boolean }) {
  const { favoritos, sugeridos, recarregar } = useFavoritos();
  const { categorias } = useCadastro();
  if (favoritos.length === 0 && sugeridos.length === 0) return null;
  return (
    <>
      {!semGrade && favoritos.length > 0 && (
        <section aria-labelledby="favoritos-da-hoje" className="bloco-da-hoje">
          <h3 id="favoritos-da-hoje">Favoritos</h3>
          <div className="grade-de-favoritos">
            {favoritos.map((f) => (
              <a key={f.id} className="favorito-da-grade" href={`#/favorito/${f.id}`}>
                <strong>{tituloDoFavorito(f, categorias)}</strong>
                <span>{formatarCentavos(f.valor_padrao_centavos)}</span>
              </a>
            ))}
          </div>
        </section>
      )}
      <SugeridosDeFavorito sugeridos={sugeridos} aoMudar={recarregar} />
    </>
  );
}
