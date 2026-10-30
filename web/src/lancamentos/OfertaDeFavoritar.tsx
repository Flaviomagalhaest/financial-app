import { useEffect, useState } from "react";
import { favoritar, oferecerFavoritar, useOfertaDeFavoritar } from "../dados";

const QUANTO_A_OFERTA_FICA_MS = 15_000;

/** Depois de salvar um lançamento que ainda não é favorito, o app oferece "Favoritar". */
export function OfertaDeFavoritar() {
  const oferta = useOfertaDeFavoritar();
  const [aviso, setAviso] = useState<string | null>(null);

  // A oferta some sozinha: quem não quer favoritar não precisa dispensar.
  useEffect(() => {
    if (!oferta) return;
    const tempo = setTimeout(() => oferecerFavoritar(null), QUANTO_A_OFERTA_FICA_MS);
    return () => clearTimeout(tempo);
  }, [oferta]);

  useEffect(() => {
    if (!aviso) return;
    const tempo = setTimeout(() => setAviso(null), QUANTO_A_OFERTA_FICA_MS);
    return () => clearTimeout(tempo);
  }, [aviso]);

  if (!oferta) return aviso ? <p role="status" className="aviso">{aviso}</p> : null;

  async function aceitar() {
    if (!oferta) return;
    const motivo = await favoritar(oferta);
    oferecerFavoritar(null);
    setAviso(motivo ? `Não foi possível favoritar: ${motivo}.` : "⭐ Favorito criado.");
  }

  return (
    <div role="status" className="aviso oferta-de-favoritar">
      <span>Salvo.</span>
      <button type="button" onClick={() => void aceitar()}>
        ⭐ Favoritar
      </button>
      <button type="button" className="secundario" onClick={() => oferecerFavoritar(null)}>
        Agora não
      </button>
    </div>
  );
}
