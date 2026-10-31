import { atualizadoAs, useCadastro, useFaturas, useLimite, type Cartao, type LimiteDoCartao } from "../dados";
import { mesPorExtenso } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { faturasDaLinha, SITUACAO } from "./apresentacao";

/** A barra do comprometido e, ao tocar, as três partes, os parcelamentos e os próximos 12 meses. */
function LimiteDoCartaoNaLinha({ limite }: { limite: LimiteDoCartao }) {
  if (limite.limite_centavos == null || limite.disponivel_centavos == null) return null;
  const parte = Math.min(100, Math.max(0, (limite.comprometido_centavos / limite.limite_centavos) * 100));
  return (
    <details className="limite">
      <summary>
        <span>
          Comprometido {formatarCentavos(limite.comprometido_centavos)} · disponível {formatarCentavos(limite.disponivel_centavos)}
        </span>
        <progress
          max={limite.limite_centavos}
          value={Math.min(limite.comprometido_centavos, limite.limite_centavos)}
          aria-label={`Limite comprometido: ${Math.round(parte)}% de ${formatarCentavos(limite.limite_centavos)}`}
        />
      </summary>
      <ul className="lista">
        <li>
          <div>
            <span>Fatura aberta</span>
            <span>{formatarCentavos(limite.fatura_aberta_centavos)}</span>
          </div>
        </li>
        <li>
          <div>
            <span>Faturas fechadas a pagar</span>
            <span>{formatarCentavos(limite.faturas_fechadas_centavos)}</span>
          </div>
        </li>
        <li>
          <div>
            <span>Parcelas futuras</span>
            <span>{formatarCentavos(limite.parcelas_futuras_centavos)}</span>
          </div>
        </li>
      </ul>
      {limite.parcelamentos.length > 0 && (
        <>
          <h4>Parcelamentos em andamento</h4>
          <ul className="lista">
            {limite.parcelamentos.map((p) => (
              <li key={p.id}>
                <div>
                  <strong>{p.descricao || "Parcelamento"}</strong>
                  <span>{formatarCentavos(p.restante_centavos)}</span>
                </div>
                <p className="vazio">
                  Faltam {p.parcelas_restantes} de {p.parcelas} · termina em {mesPorExtenso(p.fim_previsto)}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
      <h4>Próximos {limite.proximos_meses.length} meses</h4>
      <ul className="lista">
        {limite.proximos_meses.map((m) => (
          <li key={m.mes}>
            <div>
              <span>{mesPorExtenso(m.mes)}</span>
              <span>{formatarCentavos(m.libera_centavos)}</span>
            </div>
          </li>
        ))}
      </ul>
    </details>
  );
}

function CartaoComFaturas({ cartao }: { cartao: Cartao }) {
  const { dados, atualizadoEm, semDados } = useFaturas(cartao.id);
  const linhas = faturasDaLinha(dados ?? []);
  const limite = useLimite(cartao.id).dados;

  return (
    <section aria-label={cartao.nome}>
      <h3>💳 {cartao.nome}</h3>
      {limite && <LimiteDoCartaoNaLinha limite={limite} />}
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar as faturas.
        </p>
      )}
      {dados?.length === 0 && <p className="vazio">Nenhuma fatura ainda.</p>}
      <ul className="lista">
        {linhas.map(({ rotulo, fatura }) => (
          <li key={fatura.mes}>
            <a className="linha-da-fatura" href={`#/cartoes/${cartao.id}/${fatura.mes}`} aria-label={`Abrir fatura de ${mesPorExtenso(fatura.mes)} de ${cartao.nome}`}>
              <div>
                <strong>
                  {rotulo} · fatura de {mesPorExtenso(fatura.mes)}
                </strong>
                <span>{formatarCentavos(fatura.total_centavos)}</span>
              </div>
              <p className="vazio">
                {SITUACAO[fatura.situacao]}
                {fatura.situacao === "fechada" && ` · a pagar ${formatarCentavos(fatura.a_pagar_centavos)}`}
              </p>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Uma linha por cartão titular (o adicional compra na fatura dele) com a fatura anterior, a atual e a próxima. */
export function TelaDeCartoes() {
  const { cartoes } = useCadastro();
  const titulares = cartoes.filter((c) => !c.titular_id);

  return (
    <section>
      <h2>Cartões</h2>
      {titulares.length === 0 && <p className="vazio">Nenhum cartão cadastrado.</p>}
      {titulares.map((c) => (
        <CartaoComFaturas key={c.id} cartao={c} />
      ))}
    </section>
  );
}
