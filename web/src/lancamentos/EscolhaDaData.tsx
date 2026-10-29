import { diaAnterior, hoje } from "./datas";

type Props = { data: string; onMudar: (data: string) => void };

/** Hoje e ontem num toque; outra data pelo calendário. */
export function EscolhaDaData({ data, onMudar }: Props) {
  const dia = hoje();
  const atalhos = [
    { nome: "Hoje", data: dia },
    { nome: "Ontem", data: diaAnterior(dia) },
  ];
  return (
    <div className="escolha-da-data">
      {atalhos.map((a) => (
        <button type="button" key={a.nome} className={data === a.data ? "" : "secundario"} aria-pressed={data === a.data} onClick={() => onMudar(a.data)}>
          {a.nome}
        </button>
      ))}
      <label className="oculto" htmlFor="outra-data">
        Outra data
      </label>
      <input id="outra-data" type="date" value={data} onChange={(e) => e.target.value && onMudar(e.target.value)} required />
    </div>
  );
}
