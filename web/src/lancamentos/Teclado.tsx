import { apagar, digitar } from "./dinheiro";

const TECLAS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "0"];

type Props = { centavos: number; onMudar: (centavos: number) => void };

/** Teclado numérico próprio: o valor entra pelos centavos, sem vírgula. */
export function Teclado({ centavos, onMudar }: Props) {
  return (
    <div className="teclado" role="group" aria-label="Teclado do valor">
      {TECLAS.map((tecla) => (
        <button type="button" key={tecla} className="tecla" onClick={() => onMudar(digitar(centavos, tecla))}>
          {tecla}
        </button>
      ))}
      <button type="button" className="tecla" onClick={() => onMudar(apagar(centavos))}>
        Apagar
      </button>
    </div>
  );
}
