import { useEffect, useRef } from "react";
import { atualizadoAs, salvarLancamento, useCadastro, useContasDaSemana, useFila, useHoje, useLancamentos, type LancamentoNaTela, type LeituraDaHoje } from "../dados";
import { GradeDeFavoritos } from "./GradeDeFavoritos";
import { AvisoDaFila } from "../lancamentos/AvisoDaFila";
import { ContasDaSemana } from "../lancamentos/ContasDaSemana";
import { nomePorId, plural, tituloDoLancamento } from "../lancamentos/apresentacao";
import { dataPorExtenso } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";


/** Escolher o item é uma mudança do lançamento: vai pela fila, sobre o que a tela mostrava. */
function escolher(l: LancamentoNaTela | LeituraDaHoje["lancamentos_a_escolher"][number], itemCategoriaId: string, mostrado?: LancamentoNaTela) {
  const { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags, pessoa } = l;
  return salvarLancamento(
    { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags, pessoa, item_categoria_id: itemCategoriaId },
    false,
    mostrado,
  );
}

function AEscolher({ hoje }: { hoje: LeituraDaHoje }) {
  const { categorias } = useCadastro();
  const { lancamentos: naTela } = useLancamentos();
  // O que se escolheu aqui e ainda não subiu já não está a escolher.
  const pendentes = hoje.a_escolher.flatMap((a) => {
    const lancamento = hoje.lancamentos_a_escolher.find((l) => l.id === a.lancamento_id);
    const mostrado = naTela?.find((l) => l.id === a.lancamento_id);
    if (!lancamento || mostrado?.item_categoria_id) return [];
    return [{ a, lancamento, mostrado }];
  });
  if (pendentes.length === 0) return null;

  return (
    <section aria-labelledby="a-escolher" className="bloco-da-hoje">
      <h3 id="a-escolher">A escolher</h3>
      <p className="vazio">{plural(pendentes.length, "lançamento", "lançamentos")} com mais de um item do planejamento: em qual conta?</p>
      <ul className="lista">
        {pendentes.map(({ a, lancamento, mostrado }) => {
          const titulo = tituloDoLancamento(lancamento, categorias);
          return (
            <li key={a.lancamento_id}>
              <div>
                <strong>{titulo}</strong>
                <span>{formatarCentavos(lancamento.valor_centavos)}</span>
              </div>
              <p className="vazio">{dataPorExtenso(lancamento.data)}</p>
              <div className="fileira" role="group" aria-label={`Item de ${titulo}`}>
                {a.categorias_com_item.map((categoriaId) => (
                  <button
                    type="button"
                    key={categoriaId}
                    className={`ficha${categoriaId === a.item_categoria_id ? " marcada" : ""}`}
                    onClick={() => void escolher(mostrado ?? lancamento, categoriaId, mostrado)}
                  >
                    {nomePorId(categorias, categoriaId)}
                  </button>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function FaturasQueVencem({ faturas, dia }: { faturas: LeituraDaHoje["faturas_que_vencem"]; dia: string }) {
  const { cartoes } = useCadastro();
  if (faturas.length === 0) return null;
  return (
    <section aria-labelledby="faturas-que-vencem" className="bloco-da-hoje">
      <h3 id="faturas-que-vencem">Fatura que vence</h3>
      <ul className="lista">
        {faturas.map((f) => {
          const nome = nomePorId(cartoes, f.cartao_id);
          const vencida = !!f.vencimento && f.vencimento < dia;
          return (
            <li key={`${f.cartao_id}/${f.mes}`}>
              <div>
                <strong>{nome}</strong>
                <span>{formatarCentavos(f.a_pagar_centavos)}</span>
              </div>
              <p className="vazio">
                {vencida && <span className="selo-atrasado">vencida</span>}
                {f.vencimento && `vence em ${dataPorExtenso(f.vencimento)}`}
                {f.saldo_anterior_centavos > 0 && ` · ${formatarCentavos(f.saldo_anterior_centavos)} de saldo anterior`}
              </p>
              <a className="botao secundario" href={`#/cartoes/${f.cartao_id}/${f.mes}`} aria-label={`Abrir fatura de ${nome}`}>
                Abrir
              </a>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ItensEmDestaque({ itens }: { itens: LeituraDaHoje["itens_em_destaque"] }) {
  const { categorias } = useCadastro();
  if (itens.length === 0) return null;
  return (
    <section aria-labelledby="itens-em-destaque" className="bloco-da-hoje">
      <h3 id="itens-em-destaque">Itens em destaque</h3>
      <ul className="lista">
        {itens.map((i) => (
          <li key={i.id}>
            <div>
              <strong>{nomePorId(categorias, i.categoria_id)}</strong>
              <span className={i.percentual > 100 ? "erro" : undefined}>{i.percentual}%</span>
            </div>
            <progress max={100} value={Math.min(i.percentual, 100)} aria-label={`${nomePorId(categorias, i.categoria_id)}: ${i.percentual}% do planejado`} />
            <p className="vazio">
              {i.ainda_da_para_gastar_centavos >= 0
                ? `ainda dá para gastar ${formatarCentavos(i.ainda_da_para_gastar_centavos)} de ${formatarCentavos(i.planejado_centavos)}`
                : `estourou ${formatarCentavos(-i.ainda_da_para_gastar_centavos)} do planejado de ${formatarCentavos(i.planejado_centavos)}`}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** A Hoje: o essencial ao abrir o app, de uma leitura só (`GET /api/hoje`), guardada para ver sem internet. */
export function TelaHoje() {
  const { dados, atualizadoEm, semDados, buscar } = useHoje();
  const naFila = useFila().length;
  const eraNaFila = useRef(naFila);
  // A fila esvaziou (o que se fez aqui subiu): a leitura guardada já não é a do servidor.
  useEffect(() => {
    if (naFila < eraNaFila.current) void buscar();
    eraNaFila.current = naFila;
  }, [naFila, buscar]);
  // O que se confirmou aqui e ainda não subiu já não é conta da semana.
  const contasDaSemana = useContasDaSemana(dados?.contas_da_semana ?? null);
  const atrasados = (contasDaSemana?.filter((l) => l.atrasado).length ?? 0) + (dados?.transferencias_da_semana.filter((t) => t.atrasado).length ?? 0);

  return (
    <>
      <AvisoDaFila />
      {atualizadoEm && (
        <p className="vazio" data-testid="atualizado-em">
          Sem internet: {atualizadoAs(atualizadoEm)}
        </p>
      )}
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar a Hoje.
        </p>
      )}
      {dados && (
        <>
          <section aria-labelledby="ainda-da-para-gastar" className="destaque-da-hoje">
            <h3 id="ainda-da-para-gastar">Ainda dá para gastar este mês</h3>
            <p className="valor" data-testid="ainda-da-para-gastar">
              {formatarCentavos(dados.ainda_da_para_gastar_centavos)}
            </p>
            <p className="vazio">
              {dados.planejado_centavos > 0
                ? `de ${formatarCentavos(dados.planejado_centavos)} planejados`
                : "Nenhum item planejado para este mês."}
            </p>
          </section>
          {atrasados > 0 && (
            <p className="aviso" role="status" data-testid="atrasados">
              ⚠ {plural(atrasados, "conta atrasada", "contas atrasadas")}: confirme abaixo.
            </p>
          )}
          <AEscolher hoje={dados} />
          <FaturasQueVencem faturas={dados.faturas_que_vencem} dia={dados.dia} />
          <ItensEmDestaque itens={dados.itens_em_destaque} />
        </>
      )}
      <GradeDeFavoritos />
      <ContasDaSemana lancamentos={contasDaSemana} transferencias={dados ? dados.transferencias_da_semana : null} />
    </>
  );
}
