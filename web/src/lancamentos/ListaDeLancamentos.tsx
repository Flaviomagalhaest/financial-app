import { useMemo, useState, type ReactNode } from "react";
import {
  atualizadoAs,
  descartarNaoEnviado,
  excluirLancamento,
  excluirRecorrencia,
  lancarDeNovoOExcluido,
  manterOsDois,
  situacaoDaFatura,
  useCadastro,
  useLancamentos,
  useMudancasDaRecorrenciaNaoEnviadas,
  useParcelamentosNaoEnviados,
  usePessoas,
  useRecorrencias,
  useRecorrenciasNaoEnviadas,
  type LancamentoNaTela,
  type NovoLancamento,
} from "../dados";
import { indiceDeEstornos, ligacaoDoEstorno, nomePorId as nome, numeroDaParcela, podeEstornar, tituloDoLancamento, ValorComSinal } from "./apresentacao";
import { mesPorExtenso } from "../cartoes/apresentacao";
import { dataPorExtenso, quando } from "./datas";
import { divisao, rotuloDasParcelas } from "./parcelamento";
import { oQueMuda, rotuloDaRecorrencia } from "./recorrencia";

/** A recorrência ou o parcelamento que ainda não subiu, como a lista o mostra. */
type RegraNaLista = {
  id: string;
  titulo: string;
  valor: Pick<NovoLancamento, "tipo" | "valor_centavos">;
  detalhes: string;
  /** "todo mês", "10x". */
  rotulo: string;
  recusa?: string;
  podeDescartar: boolean;
};

/**
 * As regras criadas no aparelho que ainda não subiram: os lançamentos que elas geram vêm do
 * servidor. Com `onExcluir`, a que talvez já esteja lá se exclui em vez de se descartar.
 */
function RegrasNaoEnviadas(props: {
  id: string;
  titulo: string;
  explicacao: string;
  semResposta: string;
  regras: RegraNaLista[];
  onDescartar: (id: string) => void;
  onExcluir?: (id: string) => void;
}) {
  if (props.regras.length === 0) return null;
  return (
    <section aria-labelledby={props.id}>
      <h3 id={props.id}>{props.titulo}</h3>
      <p className="vazio">{props.explicacao}</p>
      <ul className="lista">
        {props.regras.map((r) => (
          <li key={r.id}>
            <div>
              <strong>{r.titulo}</strong>
              <ValorComSinal l={r.valor} />
            </div>
            <p className="vazio">{r.detalhes}</p>
            <p className={r.recusa ? "erro" : "vazio"}>
              ⏳ {r.titulo}, {r.rotulo}, não enviado{r.recusa ? `: ${r.recusa}` : ""}
            </p>
            {r.podeDescartar ? (
              <div className="acoes">
                <button type="button" className="secundario" aria-label={`Descartar ${r.titulo}`} onClick={() => props.onDescartar(r.id)}>
                  Descartar
                </button>
              </div>
            ) : (
              <>
                <p className="vazio">{props.semResposta}</p>
                {props.onExcluir && (
                  <div className="acoes">
                    <button type="button" className="secundario" aria-label={`Excluir ${r.titulo}`} onClick={() => props.onExcluir!(r.id)}>
                      Excluir
                    </button>
                  </div>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Lançamentos do casal, do mais recente ao mais antigo, com editar e excluir em cada linha. */
export function ListaDeLancamentos({ topo }: { topo?: ReactNode }) {
  const { cartoes, contasECartoes, categorias } = useCadastro();
  const { lancamentos, atualizadoEm, semDados } = useLancamentos();
  const recorrencias = useRecorrenciasNaoEnviadas();
  const mudancasDeRecorrencia = useMudancasDaRecorrenciaNaoEnviadas();
  const { recorrencias: regras } = useRecorrencias();
  const parcelamentos = useParcelamentosNaoEnviados();
  const { euId, nomeDe } = usePessoas();
  const [erro, setErro] = useState("");
  const [informacoes, setInformacoes] = useState<string | null>(null);
  // A compra de fatura já fechada que se pediu para excluir: a tela sugere o estorno antes.
  const [sugerindoEstorno, setSugerindoEstorno] = useState<string | null>(null);
  const estornos = useMemo(() => indiceDeEstornos(lancamentos ?? []), [lancamentos]);

  async function excluir(l: LancamentoNaTela, mesmoFechada = false) {
    setSugerindoEstorno(null);
    // Cancelar a compra de uma fatura aberta é excluir; depois do fechamento o valor já foi cobrado e o certo é estornar.
    const cartao = cartoes.find((c) => c.id === l.conta_id);
    if (!mesmoFechada && cartao && l.mes && !l.naoEnviado) {
      const situacao = await situacaoDaFatura(cartao.titular_id ?? cartao.id, l.mes);
      if (situacao && situacao !== "aberta" && !l.estorno_de) return setSugerindoEstorno(l.id);
    }
    if (!window.confirm(`Excluir "${l.descricao || "este lançamento"}"?`)) return;
    setErro("");
    await excluirLancamento(l).catch(() => setErro("Não foi possível excluir no aparelho."));
  }

  async function lancarDeNovo(l: LancamentoNaTela) {
    setErro("");
    await lancarDeNovoOExcluido(l.id).catch(() => setErro("Não foi possível lançar de novo no aparelho."));
  }

  async function manter(l: LancamentoNaTela) {
    setErro("");
    if (!(await manterOsDois(l.id))) setErro("Sem internet: não foi possível manter os dois agora.");
  }

  /** Quem fez, pelo nome; o que só existe neste aparelho é de quem está com ele. */
  const quem = (id?: string) => (id ? (id === euId ? "você" : nomeDe(id)) : "você");

  async function descartar({ id }: { id: string }) {
    setErro("");
    await descartarNaoEnviado(id).catch(() => setErro("Não foi possível descartar no aparelho."));
  }

  /** A recorrência que talvez já tenha subido: a exclusão tira do servidor também, se ela estiver lá. */
  async function excluirNaoEnviada(id: string) {
    const recorrencia = recorrencias.find((r) => r.id === id);
    if (!recorrencia) return;
    if (!window.confirm(`Excluir a recorrência ${tituloDoLancamento(recorrencia, categorias)}? Se ela já chegou ao servidor, os previstos de hoje em diante saem.`)) return;
    setErro("");
    await excluirRecorrencia(recorrencia).catch(() => setErro("Não foi possível excluir no aparelho."));
  }

  return (
    <section>
      <h2>Histórico</h2>
      {topo}
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
      {semDados && lancamentos?.length === 0 && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar os lançamentos.
        </p>
      )}
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <RegrasNaoEnviadas
        id="recorrencias-nao-enviadas"
        titulo="Recorrências não enviadas"
        explicacao="Os previstos aparecem quando a recorrência subir."
        semResposta="O envio ficou sem resposta: ela talvez já esteja no servidor e sobe quando a rede voltar."
        regras={recorrencias.map((r) => ({
          ...r,
          titulo: tituloDoLancamento(r, categorias),
          valor: r,
          detalhes: [`desde ${dataPorExtenso(r.inicio)}`, nome(contasECartoes, r.conta_id), r.categoria_ids.map((c) => nome(categorias, c)).join(", "), r.tipo_do_valor === "estimado" ? "estimado" : ""]
            .filter(Boolean)
            .join(" · "),
          rotulo: rotuloDaRecorrencia(r),
        }))}
        onDescartar={(id) => void descartar({ id })}
        onExcluir={(id) => void excluirNaoEnviada(id)}
      />
      {mudancasDeRecorrencia.length > 0 && (
        <section aria-labelledby="mudancas-de-recorrencia-nao-enviadas">
          <h3 id="mudancas-de-recorrencia-nao-enviadas">Mudanças de recorrência não enviadas</h3>
          <p className="vazio">Os previstos mudam quando a mudança subir.</p>
          <ul className="lista">
            {mudancasDeRecorrencia.map((m) => {
              const titulo = tituloDoLancamento(m.recorrencia, categorias);
              return (
                <li key={m.id}>
                  <p className={m.recusa ? "erro" : "vazio"}>
                    ⏳ {titulo}: {m.alteracao ? oQueMuda(m.alteracao) : "excluir"}, não enviado{m.recusa ? `: ${m.recusa}` : ""}
                  </p>
                  {m.podeDescartar ? (
                    <div className="acoes">
                      <button type="button" className="secundario" aria-label={`Descartar a mudança de ${titulo}`} onClick={() => void descartar(m)}>
                        Descartar
                      </button>
                    </div>
                  ) : (
                    <p className="vazio">O envio ficou sem resposta: ela talvez já valha no servidor e sobe quando a rede voltar.</p>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
      <RegrasNaoEnviadas
        id="parcelamentos-nao-enviados"
        titulo="Parcelamentos não enviados"
        explicacao="As parcelas aparecem quando o parcelamento subir."
        semResposta="O envio ficou sem resposta: ele talvez já esteja no servidor e sobe quando a rede voltar."
        regras={parcelamentos.map((p) => ({
          ...p,
          titulo: tituloDoLancamento(p, categorias),
          valor: { tipo: p.tipo, valor_centavos: divisao(p).total },
          detalhes: [dataPorExtenso(p.data), nome(contasECartoes, p.conta_id), p.categoria_ids.map((c) => nome(categorias, c)).join(", "), rotuloDasParcelas(p), p.automatico ? "automático" : ""]
            .filter(Boolean)
            .join(" · "),
          rotulo: `${p.parcelas}x`,
        }))}
        onDescartar={(id) => void descartar({ id })}
      />
      {!semDados && lancamentos?.length === 0 && <p className="vazio">Nenhum lançamento ainda.</p>}
      <ul className="lista">
        {lancamentos?.map((l) => {
          const titulo = tituloDoLancamento(l, categorias);
          const ligacao = ligacaoDoEstorno(l, estornos, categorias);
          return (
            <li key={l.id}>
              <div>
                <strong>
                  {titulo}
                  {l.parcela && l.parcelas ? ` ${numeroDaParcela(l.parcela, l.parcelas)}` : ""}
                </strong>
                <ValorComSinal l={l} />
              </div>
              <p className="vazio">
                {dataPorExtenso(l.data)} · {nome(contasECartoes, l.conta_id)} · {l.categoria_ids.map((c) => nome(categorias, c)).join(", ")}
                {l.tags?.length ? ` · ${l.tags.map((t) => `#${t}`).join(" ")}` : ""}
                {ligacao && ` · ${ligacao}`}
                {l.situacao === "previsto" && (l.atrasado ? " · previsto, atrasado" : " · previsto")}
                {l.alterada_a_mao && " · alterada à mão"}
                {" · "}
                {l.pessoa ? nomeDe(l.pessoa) : "conjunto"}
              </p>
              {l.parece_repetido_de && euId && l.criado_por !== euId && !l.naoEnviado && (
                <div className="aviso" role="group" aria-label={`Parece repetido ${titulo}`}>
                  <p className="erro">Parece repetido: {nomeDe(l.criado_por)} lançou o mesmo valor na mesma conta.</p>
                  <div className="acoes">
                    <button type="button" aria-label={`Manter os dois ${titulo}`} onClick={() => void manter(l)}>
                      Manter os dois
                    </button>
                    <button type="button" className="secundario" aria-label={`Excluir este ${titulo}`} onClick={() => void excluir(l)}>
                      Excluir este
                    </button>
                  </div>
                </div>
              )}
              {sugerindoEstorno === l.id && (
                <div className="aviso" role="group" aria-label="Fatura fechada">
                  <p>
                    A fatura de {mesPorExtenso(l.mes!)} já fechou: excluir a compra não devolve o valor cobrado. Estorne a compra para acertar a fatura.
                  </p>
                  <div className="acoes">
                    {podeEstornar(l, cartoes, estornos) && (
                      <a className="botao" href={`#/estornar/${l.id}`}>
                        Estornar
                      </a>
                    )}
                    <button type="button" className="secundario" onClick={() => void excluir(l, true)}>
                      Excluir mesmo assim
                    </button>
                    <button type="button" className="secundario" onClick={() => setSugerindoEstorno(null)}>
                      Voltar
                    </button>
                  </div>
                </div>
              )}
              {l.conflito ? (
                <p className="erro">⚠ conflito: sua mudança espera decisão</p>
              ) : l.exclusao ? (
                <p className="erro">
                  {l.exclusao.por_voce ? "Você excluiu este lançamento em outro aparelho" : `${nomeDe(l.exclusao.excluido_por)} excluiu este lançamento`}; sua alteração não foi
                  salva.
                </p>
              ) : (
                l.naoEnviado && <p className={l.recusa ? "erro" : "vazio"}>{l.recusa ? `⏳ não enviado: ${l.recusa}` : "⏳ não enviado"}</p>
              )}
              <div className="acoes">
                {l.conflito ? (
                  <a className="botao" href={`#/conflito/${l.id}`} aria-label={`Decidir ${titulo}`}>
                    Decidir
                  </a>
                ) : l.exclusao ? (
                  <>
                    <button type="button" aria-label={`Lançar de novo ${titulo}`} onClick={() => void lancarDeNovo(l)}>
                      Lançar de novo
                    </button>
                    <button type="button" className="secundario" aria-label={`Dispensar ${titulo}`} onClick={() => void descartar(l)}>
                      Dispensar
                    </button>
                  </>
                ) : (
                  <>
                    <a className="botao secundario" href={`#/novo/${l.id}`} aria-label={`${l.recusa ? "Corrigir" : "Editar"} ${titulo}`}>
                      {l.recusa ? "Corrigir" : "Editar"}
                    </a>
                    {podeEstornar(l, cartoes, estornos) && (
                      <a className="botao secundario" href={`#/estornar/${l.id}`} aria-label={`Estornar ${titulo}`}>
                        Estornar
                      </a>
                    )}
                    {l.recusa ? (
                      <button type="button" className="secundario" aria-label={`Descartar ${titulo}`} onClick={() => void descartar(l)}>
                        Descartar
                      </button>
                    ) : (
                      <button type="button" className="secundario" aria-label={`Excluir ${titulo}`} onClick={() => void excluir(l)}>
                        Excluir
                      </button>
                    )}
                  </>
                )}
                <details className="menu">
                  <summary aria-label={`Mais ações ${titulo}`}>⋯</summary>
                  <button type="button" className="secundario" aria-label={`Informações ${titulo}`} onClick={() => setInformacoes(informacoes === l.id ? null : l.id)}>
                    Informações
                  </button>
                  {l.recorrencia_id && l.ocorrencia && (!regras || regras.some((r) => r.id === l.recorrencia_id)) && (
                    <a className="botao secundario" href={`#/recorrencia/${l.id}`} aria-label={`Recorrência ${titulo}`}>
                      Recorrência
                    </a>
                  )}
                  {l.parcelamento_id && !l.naoEnviado && (
                    <a className="botao secundario" href={`#/parcelamento/${l.parcelamento_id}`} aria-label={`Parcelamento ${titulo}`}>
                      Parcelamento
                    </a>
                  )}
                </details>
              </div>
              {informacoes === l.id && (
                <dl className="informacoes" aria-label={`Informações de ${titulo}`}>
                  <dt>Criado por</dt>
                  <dd>
                    {quem(l.criado_por)}
                    {l.criado_em ? `, ${quando(l.criado_em)}` : ", ainda não enviado"}
                  </dd>
                  <dt>Alterado por último por</dt>
                  <dd>
                    {quem(l.alterado_por)}
                    {l.alterado_em ? `, ${quando(l.alterado_em)}` : ", ainda não enviado"}
                  </dd>
                  <dt>Origem</dt>
                  <dd>{l.fonte === "mobills" ? "importado do Mobills" : "app"}</dd>
                </dl>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
