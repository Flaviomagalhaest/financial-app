import { atualizadoAs, useCadastro, useFaturas, type Cartao } from "../dados";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { faturasDaLinha, mesPorExtenso, SITUACAO } from "./apresentacao";

function CartaoComFaturas({ cartao }: { cartao: Cartao }) {
  const { dados, atualizadoEm, semDados } = useFaturas(cartao.id);
  const linhas = faturasDaLinha(dados ?? []);

  return (
    <section aria-label={cartao.nome}>
      <h3>💳 {cartao.nome}</h3>
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
            <a className="botao secundario" href={`#/cartoes/${cartao.id}/${fatura.mes}`} aria-label={`Abrir fatura de ${mesPorExtenso(fatura.mes)} de ${cartao.nome}`}>
              Abrir
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
