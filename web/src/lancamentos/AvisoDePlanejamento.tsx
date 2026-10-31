import { atualizadoAs, oQueSobra, type Aviso } from "../dados";
import { dataPorExtenso, rotuloDaFatura, rotuloDoMes } from "./datas";

type Props = {
  aviso: Aviso | null;
  /** O mês em que o lançamento conta; `null` no cartão sem dia de fechamento e sem fatura escolhida. */
  mes: string | null;
  tipo: "despesa" | "receita";
  /** No cartão, o fechamento da fatura em que a compra cai. */
  fechamento: string | null;
  noCartao: boolean;
  atualizadoEm: number | null;
  semPlanejamento: boolean;
  nomeDaCategoria: (id: string) => string;
  escolha: string | null;
  onEscolher: (categoria: string) => void;
};

/** O planejado como uma barra: o que já conta e, mais claro, a parte deste lançamento. */
function Medidor({ antes, depois }: { antes: number; depois: number }) {
  const ate100 = (p: number) => Math.min(Math.max(p, 0), 100);
  const base = ate100(Math.min(antes, depois));
  const parte = ate100(Math.max(antes, depois)) - base;
  return (
    <div className={`medidor${depois > 100 ? " estourado" : ""}`} aria-hidden="true">
      <span className="medidor-antes" style={{ width: `${base}%` }} />
      <span className="medidor-lancamento" style={{ width: `${parte}%` }} />
    </div>
  );
}

/** O efeito do lançamento no planejamento do mês, a cada toque (ticket 52). */
export function AvisoDePlanejamento(props: Props) {
  const { aviso, mes } = props;
  return (
    <section className="aviso-do-planejamento" aria-label="Aviso de planejamento" aria-live="polite">
      {props.noCartao &&
        (mes ? (
          <p className="detalhe-do-aviso">
            Cai na {rotuloDaFatura(mes)}
            {props.fechamento && `, que fecha em ${dataPorExtenso(props.fechamento).slice(0, 5)},`} e conta em {rotuloDoMes(mes)}.
          </p>
        ) : (
          <p className="erro">Cartão sem dia de fechamento: escolha a fatura nos detalhes.</p>
        ))}
      {props.semPlanejamento && mes && <p className="vazio">Sem internet: o planejamento de {rotuloDoMes(mes)} não está no aparelho.</p>}
      {aviso?.item && (
        <>
          <p data-testid="efeito-no-item">
            <strong>{props.nomeDaCategoria(aviso.item.categoria_id)}</strong>: {aviso.item.antes.percentual}%
            {aviso.item.depois.ainda_da_para_gastar_centavos !== aviso.item.antes.ainda_da_para_gastar_centavos && (
              <>
                {" → "}
                <strong>{aviso.item.depois.percentual}%</strong>
              </>
            )}{" "}
            do planejado de {rotuloDoMes(aviso.mes)}
          </p>
          <Medidor antes={aviso.item.antes.percentual} depois={aviso.item.depois.percentual} />
          <p className={aviso.item.depois.ainda_da_para_gastar_centavos < 0 ? "erro" : "detalhe-do-aviso"}>{oQueSobra(props.tipo, aviso.item.depois.ainda_da_para_gastar_centavos)}</p>
        </>
      )}
      {aviso && aviso.categoriasComItem.length === 0 && (
        <p className="detalhe-do-aviso">Nenhuma das categorias tem item no planejamento de {rotuloDoMes(aviso.mes)}, então conta só no total do mês.</p>
      )}
      {aviso && aviso.categoriasComItem.length > 1 && (
        <>
          <h3 id="onde-conta">Conta no planejamento em:</h3>
          <div className="fileira" role="group" aria-labelledby="onde-conta">
            {aviso.categoriasComItem.map((c) => (
              <button type="button" key={c} className={`ficha${c === props.escolha ? " marcada" : ""}`} aria-pressed={c === props.escolha} onClick={() => props.onEscolher(c)}>
                {props.nomeDaCategoria(c)}
              </button>
            ))}
          </div>
          {aviso.aEscolher && <p className="detalhe-do-aviso">Sem escolha, ele fica em "a escolher" até alguém escolher o item.</p>}
        </>
      )}
      {props.atualizadoEm && (aviso || props.noCartao) && <p className="vazio">Planejamento {atualizadoAs(props.atualizadoEm)}</p>}
    </section>
  );
}
