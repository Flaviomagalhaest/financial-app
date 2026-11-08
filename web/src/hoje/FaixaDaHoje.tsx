import { useCadastro, useFavoritos, type LeituraDaHoje } from "../dados";
import { Icone } from "../casca/icones";
import { TrilhoDaFaixa } from "../casca/TrilhoDaFaixa";
import { nomePorId, plural, tituloDoFavorito } from "../lancamentos/apresentacao";
import { diaEMes } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";

/**
 * As pílulas da faixa (ticket 204): cada favorito com o valor (tocar abre o lançamento preenchido),
 * a fatura que vence (sem fatura, os cartões) e as contas. Desligadas em Configurações, somem.
 */
function Atalhos({ hoje }: { hoje: LeituraDaHoje }) {
  const { favoritos } = useFavoritos();
  const { categorias, contas, cartoes } = useCadastro();
  const fatura = hoje.faturas_que_vencem[0];
  const ativas = contas.filter((c) => !c.arquivada).length;
  return (
    <ul className="pilulas" aria-label="Atalhos">
      {favoritos.map((f) => (
        <li key={f.id}>
          <a href={`#/favorito/${f.id}`}>
            <Icone nome="estrela" />
            <span>
              <strong>{tituloDoFavorito(f, categorias)}</strong>
              <small>{formatarCentavos(f.valor_padrao_centavos)}</small>
            </span>
          </a>
        </li>
      ))}
      <li>
        {fatura ? (
          <a href={`#/cartoes/${fatura.cartao_id}/${fatura.mes}`}>
            <Icone nome="cartoes" />
            <span>
              <strong>Fatura {formatarCentavos(fatura.a_pagar_centavos)}</strong>
              <small>
                {nomePorId(cartoes, fatura.cartao_id)}
                {fatura.vencimento && ` · vence ${diaEMes(fatura.vencimento)}`}
              </small>
            </span>
          </a>
        ) : (
          <a href="#/cartoes">
            <Icone nome="cartoes" />
            <span>
              <strong>Cartões</strong>
              <small>{plural(cartoes.length, "cartão", "cartões")}</small>
            </span>
          </a>
        )}
      </li>
      <li>
        <a href="#/contas-e-categorias">
          <Icone nome="pastas" />
          <span>
            <strong>Contas e categorias</strong>
            <small>{plural(ativas, "conta", "contas")}</small>
          </span>
        </a>
      </li>
    </ul>
  );
}

/** A faixa verde da Hoje: quanto ainda dá para gastar no mês, a parte já usada do planejado e, se ligados, os atalhos. */
export function FaixaDaHoje({ hoje, atalhos }: { hoje: LeituraDaHoje; atalhos: boolean }) {
  return (
    <section aria-labelledby="ainda-da-para-gastar" className="faixa">
      <h3 id="ainda-da-para-gastar">Ainda dá para gastar este mês</h3>
      <p className="valor-da-faixa" data-testid="ainda-da-para-gastar">
        {hoje.ainda_da_para_gastar_centavos < 0 ? `passou ${formatarCentavos(-hoje.ainda_da_para_gastar_centavos)}` : formatarCentavos(hoje.ainda_da_para_gastar_centavos)}
      </p>
      {hoje.planejado_centavos > 0 && <TrilhoDaFaixa usado={hoje.planejado_centavos - hoje.ainda_da_para_gastar_centavos} total={hoje.planejado_centavos} />}
      <p className="vazio">{hoje.planejado_centavos > 0 ? `de ${formatarCentavos(hoje.planejado_centavos)} planejados` : "Nenhum item planejado para este mês."}</p>
      {atalhos && <Atalhos hoje={hoje} />}
    </section>
  );
}
