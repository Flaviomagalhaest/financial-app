import { Fragment, useEffect, useRef, useState } from "react";
import {
  aplicarModeloPadrao,
  atualizadoAs,
  copiarPlanejamento,
  criarItemDoPlanejamento,
  enderecoDaBusca,
  escolherItem,
  excluirItemDoPlanejamento,
  mudarItemDoPlanejamento,
  useCadastro,
  useConexao,
  useLancamentos,
  useMes,
  usePessoas,
  type LancamentoNaTela,
  type LeituraDoMes,
} from "../dados";
import { nomePorId, tituloDoLancamento, ValorComSinal } from "../lancamentos/apresentacao";
import { dataPorExtenso, hoje } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { lerReais } from "./TelaDoModelo";
import { mesCurto, mesVizinho, nomeDoMes, textoDoFechamento, variacao } from "./apresentacao";

type Categorias = ReturnType<typeof useCadastro>["categorias"];

/** Despesas do mês contra o planejado: o realizado, o previsto e o que ainda está livre. */
function BarraDoMes({ leitura }: { leitura: LeituraDoMes }) {
  const { realizado_centavos: realizado, previsto_centavos: previsto, planejado_centavos: planejado, livre_centavos: livre } = leitura.despesas;
  const escala = Math.max(planejado, realizado + previsto, 1);
  const largura = (centavos: number) => `${(Math.max(centavos, 0) * 100) / escala}%`;
  const passou = realizado + previsto - planejado;
  return (
    <section aria-label="Despesas × planejamento">
      <h3>Despesas × planejamento</h3>
      <div className="barra-do-mes" role="img" aria-label={`realizado ${formatarCentavos(realizado)}, previsto ${formatarCentavos(previsto)}, livre ${formatarCentavos(livre)}`}>
        <span className="realizado" style={{ width: largura(realizado) }} />
        <span className="previsto" style={{ width: largura(previsto) }} />
        {planejado > 0 && <span className="marca-do-planejado" style={{ left: `calc(${largura(planejado)} - 1px)` }} />}
      </div>
      <ul className="legenda">
        <li>
          <i className="realizado" /> realizado {formatarCentavos(realizado)}
        </li>
        <li>
          <i className="previsto" /> previsto {formatarCentavos(previsto)}
        </li>
        <li>
          <i className="livre" /> livre {formatarCentavos(livre)}
        </li>
      </ul>
      <p className="vazio">
        {planejado > 0 ? `De ${formatarCentavos(planejado)} planejados para despesas.` : "Sem planejamento de despesas neste mês."}
        {planejado > 0 && passou > 0 && <strong className="acima"> Passou {formatarCentavos(passou)} do planejado.</strong>}
      </p>
      <p>
        Receitas: {formatarCentavos(leitura.receitas.realizado_centavos)} recebidas, {formatarCentavos(leitura.receitas.previsto_centavos)} previstas.
      </p>
    </section>
  );
}

function Fechamento({ leitura, categorias }: { leitura: LeituraDoMes; categorias: Categorias }) {
  return (
    <section aria-label="Fechamento do mês" className="fechamento">
      <h3>Fechamento do mês</h3>
      {textoDoFechamento(leitura, (id) => nomePorId(categorias, id)).map((paragrafo) => (
        <p key={paragrafo}>{paragrafo}</p>
      ))}
    </section>
  );
}

/** Os lançamentos com duas ou mais categorias com item: a escolha vai pela fila, com ou sem internet. */
function AEscolher({ leitura, categorias, lancamentos, aoEscolher }: { leitura: LeituraDoMes; categorias: Categorias; lancamentos: LancamentoNaTela[]; aoEscolher: () => void }) {
  // A escolha que ainda está na fila já tira o lançamento da lista.
  const aEscolher = leitura.planejamento.a_escolher.flatMap((escolha) => {
    const lancamento = lancamentos.find((l) => l.id === escolha.lancamento_id);
    return lancamento && !lancamento.item_categoria_id ? [{ escolha, lancamento }] : [];
  });
  if (!aEscolher.length) return null;
  return (
    <section aria-label="A escolher">
      <h3>A escolher</h3>
      <p className="vazio">Têm duas ou mais categorias com item no planejamento. Em qual item cada um conta?</p>
      <ul className="lista">
        {aEscolher.map(({ escolha, lancamento }) => (
          <li key={lancamento.id} aria-label={tituloDoLancamento(lancamento, categorias)}>
            <div>
              <strong>{tituloDoLancamento(lancamento, categorias)}</strong>
              <ValorComSinal l={lancamento} />
            </div>
            <p className="vazio">
              {dataPorExtenso(lancamento.data)}
              {escolha.item_categoria_id && ` · por ora conta em ${nomePorId(categorias, escolha.item_categoria_id)}`}
            </p>
            <div className="acoes-em-linha">
              {escolha.categorias_com_item.map((c) => (
                <button key={c} className="secundario" onClick={() => void escolherItem(lancamento, c).then(aoEscolher)}>
                  Conta em {nomePorId(categorias, c)}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Os itens do mês; no mês vazio, copiar do anterior ou aplicar o modelo padrão (só com internet). */
function Itens({ leitura, categorias, aoMudar }: { leitura: LeituraDoMes; categorias: Categorias; aoMudar: () => void }) {
  const online = useConexao();
  const [recusa, setRecusa] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [editando, setEditando] = useState<{ id: string; reais: string } | null>(null);
  const [novo, setNovo] = useState({ categoria_id: "", reais: "" });
  const { itens, ainda_da_para_gastar_centavos } = leitura.planejamento;
  const anterior = mesVizinho(leitura.mes, -1);

  async function pedir(fazer: () => Promise<string | null>) {
    setEnviando(true);
    setRecusa(null);
    const motivo = await fazer();
    setEnviando(false);
    setRecusa(motivo);
    if (!motivo) aoMudar();
    return motivo;
  }

  /** Um valor em reais inválido não sai do aparelho. */
  function comValor(reais: string, fazer: (centavos: number) => Promise<string | null>) {
    const centavos = lerReais(reais);
    if (centavos === null) {
      setRecusa("o valor precisa ser maior que zero");
      return Promise.resolve("valor inválido");
    }
    return pedir(() => fazer(centavos));
  }

  const usadas = new Set(itens.map((i) => i.categoria_id));
  const disponiveis = categorias.filter((c) => !c.arquivada && !usadas.has(c.id));

  return (
    <section aria-label="Itens do planejamento">
      <h3>Itens do planejamento</h3>
      {itens.length > 0 ? (
        <>
          {leitura.situacao !== "passado" && <p>Ainda dá para gastar: {formatarCentavos(ainda_da_para_gastar_centavos)}</p>}
          <div className="rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Realizado</th>
                  <th>Previsto</th>
                  <th>Planejado</th>
                  <th>%</th>
                  <th>
                    <span className="oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {itens.map((i) => (
                  <tr key={i.id}>
                    <td>{nomePorId(categorias, i.categoria_id)}</td>
                    <td>{formatarCentavos(i.realizado_centavos)}</td>
                    <td className="vazio">{i.previsto_centavos ? formatarCentavos(i.previsto_centavos) : "—"}</td>
                    <td>{formatarCentavos(i.planejado_centavos)}</td>
                    <td className={i.percentual > 100 ? "acima" : undefined}>
                      {i.percentual > 100 && "⚠ "}
                      {i.percentual}%
                    </td>
                    <td>
                      {editando?.id === i.id ? (
                        <div className="linha">
                          <input aria-label={`Novo valor de ${nomePorId(categorias, i.categoria_id)}`} inputMode="decimal" autoComplete="off" placeholder="0,00" value={editando.reais} onChange={(e) => setEditando({ id: i.id, reais: e.target.value })} />
                          <button
                            disabled={!online || enviando}
                            onClick={() =>
                              void comValor(editando.reais, (c) => mudarItemDoPlanejamento(i.id, c)).then((motivo) => {
                                if (!motivo) setEditando(null);
                              })
                            }
                          >
                            Salvar valor
                          </button>
                          <button className="secundario" onClick={() => setEditando(null)}>
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <div className="acoes-em-linha">
                          <button className="secundario" disabled={!online || enviando} aria-label={`Mudar valor de ${nomePorId(categorias, i.categoria_id)}`} onClick={() => setEditando({ id: i.id, reais: (i.planejado_centavos / 100).toFixed(2).replace(".", ",") })}>
                            Mudar valor
                          </button>
                          <button className="secundario" disabled={!online || enviando} aria-label={`Excluir ${nomePorId(categorias, i.categoria_id)}`} onClick={() => void pedir(() => excluirItemDoPlanejamento(i.id))}>
                            Excluir
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <>
          <p className="vazio">Nenhum item planejado neste mês.</p>
          {!online && <p className="vazio">Sem internet: copiar e aplicar o modelo esperam a conexão.</p>}
          <div className="acoes-em-linha">
            <button className="secundario" disabled={!online || enviando} onClick={() => void pedir(() => copiarPlanejamento(leitura.mes, anterior))}>
              Copiar do mês anterior
            </button>
            <button className="secundario" disabled={!online || enviando} onClick={() => void pedir(() => aplicarModeloPadrao(leitura.mes))}>
              Aplicar modelo padrão
            </button>
          </div>
        </>
      )}
      {disponiveis.length > 0 && (
        <div className="linha">
          <select aria-label="Categoria do novo item" value={novo.categoria_id} onChange={(e) => setNovo({ ...novo, categoria_id: e.target.value })}>
            <option value="">Escolha a categoria</option>
            {disponiveis.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
          <input aria-label="Valor do novo item" inputMode="decimal" autoComplete="off" placeholder="0,00" value={novo.reais} onChange={(e) => setNovo({ ...novo, reais: e.target.value })} />
          <button
            disabled={!online || enviando || !novo.categoria_id}
            onClick={() =>
              void comValor(novo.reais, (c) => criarItemDoPlanejamento(leitura.mes, novo.categoria_id, c)).then((motivo) => {
                if (!motivo) setNovo({ categoria_id: "", reais: "" });
              })
            }
          >
            Adicionar item
          </button>
        </div>
      )}
      {!online && itens.length > 0 && <p className="vazio">Sem internet: mudar os itens espera a conexão.</p>}
      {recusa && (
        <p role="alert" className="erro">
          Não deu: {recusa}.
        </p>
      )}
      <a href="#/modelo-do-planejamento">Modelo padrão</a>
    </section>
  );
}

/** Cada categoria contra os dois períodos; tocar na linha mostra os valores antigos. */
function Comparacao({ leitura, categorias }: { leitura: LeituraDoMes; categorias: Categorias }) {
  const [aberta, setAberta] = useState<string | null>(null);
  const { anterior, ano_passado, linhas, total } = leitura.comparacao;
  if (!linhas.length && !total.mes_centavos && !total.anterior_centavos && !total.ano_passado_centavos) {
    return (
      <section aria-label="Comparação">
        <h3>Comparação</h3>
        <p className="vazio">Sem despesas neste mês, em {nomeDoMes(anterior)} nem em {nomeDoMes(ano_passado)}.</p>
      </section>
    );
  }
  const todas = [...linhas.map((l) => ({ chave: l.categoria_id, nome: nomePorId(categorias, l.categoria_id), valores: l, total: false })), { chave: "total", nome: "Total de despesas", valores: total, total: true }];
  return (
    <section aria-label="Comparação">
      <h3>Comparação</h3>
      <div className="rolagem">
        <table className="tabela comparacao">
          <thead>
            <tr>
              <th>Categoria</th>
              <th>{mesCurto(leitura.mes)}</th>
              <th>× {mesCurto(anterior)}</th>
              <th>× {mesCurto(ano_passado)}</th>
            </tr>
          </thead>
          <tbody>
            {todas.map(({ chave, nome, valores, total: ehTotal }) => (
              <Fragment key={chave}>
                <tr className={ehTotal ? "total" : undefined}>
                  <td>
                    <button className="linha-que-abre" aria-expanded={aberta === chave} onClick={() => setAberta(aberta === chave ? null : chave)}>
                      {nome}
                    </button>
                  </td>
                  <td>{formatarCentavos(valores.mes_centavos)}</td>
                  <td>{variacao(valores.mes_centavos, valores.anterior_centavos)}</td>
                  <td>{variacao(valores.mes_centavos, valores.ano_passado_centavos)}</td>
                </tr>
                {aberta === chave && (
                  <tr className="valores-antigos">
                    <td colSpan={4}>
                      {nomeDoMes(anterior)}: {formatarCentavos(valores.anterior_centavos)} · {nomeDoMes(ano_passado)}: {formatarCentavos(valores.ano_passado_centavos)}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="vazio">O total conta cada lançamento uma vez; as linhas somam mais quando um lançamento tem várias categorias.</p>
    </section>
  );
}

type Dimensao = "categoria" | "tag" | "pessoa";
const DIMENSOES: { id: Dimensao; nome: string; linhas: keyof LeituraDoMes["ranking"]; vazio: string; somaMais: boolean }[] = [
  { id: "categoria", nome: "Categoria", linhas: "por_categoria", vazio: "Nenhuma despesa neste mês.", somaMais: true },
  { id: "tag", nome: "Tag", linhas: "por_tag", vazio: "Nenhuma despesa com tag neste mês.", somaMais: true },
  { id: "pessoa", nome: "Pessoa", linhas: "por_pessoa", vazio: "Nenhuma despesa neste mês.", somaMais: false },
];

type LinhaAberta = { nome: string; centavos: number; ids: string[]; busca: string };

/** A busca das despesas da linha, pelo mês em que contam (o da fatura no cartão), como o ranking. */
function buscaDaLinha(mes: string, dimensao: Dimensao, chave: string | null): string {
  const filtro = dimensao === "categoria" ? { categoria_ids: [chave ?? ""] } : dimensao === "tag" ? { tags: [chave ?? ""] } : chave ? { pessoas: [chave] } : { conjunto: true };
  return enderecoDaBusca({ tipos: ["despesa"], fatura: { mes: `${mes}-01` }, ...filtro });
}

/** Os lançamentos de uma linha do ranking, numa folha que sobe de baixo. */
function FolhaDoRanking({ linha, categorias, lancamentos, aoFechar }: { linha: LinhaAberta; categorias: Categorias; lancamentos: LancamentoNaTela[]; aoFechar: () => void }) {
  const folha = useRef<HTMLDialogElement>(null);
  const { contasECartoes } = useCadastro();
  useEffect(() => folha.current?.showModal(), []);
  const daLinha = linha.ids.flatMap((id) => lancamentos.filter((l) => l.id === id));
  return (
    <dialog ref={folha} className="folha" aria-labelledby="titulo-da-linha" onClose={aoFechar}>
      <h3 id="titulo-da-linha">{linha.nome}</h3>
      <p className="vazio">{formatarCentavos(linha.centavos)}</p>
      <ul className="lista">
        {daLinha.map((l) => (
          <li key={l.id}>
            <div>
              <strong>{tituloDoLancamento(l, categorias)}</strong>
              <ValorComSinal l={l} />
            </div>
            <p className="vazio">
              {dataPorExtenso(l.data)} · {nomePorId(contasECartoes, l.conta_id)}
              {l.situacao === "previsto" && " · previsto"}
            </p>
          </li>
        ))}
      </ul>
      <a className="botao secundario" href={linha.busca}>
        Ver os lançamentos
      </a>
      <button onClick={() => folha.current?.close()}>Fechar</button>
    </dialog>
  );
}

/** Para onde foi o dinheiro: barras por categoria, tag ou pessoa, sem pizza. */
function Ranking({ leitura, categorias, lancamentos }: { leitura: LeituraDoMes; categorias: Categorias; lancamentos: LancamentoNaTela[] }) {
  const [dimensao, setDimensao] = useState(DIMENSOES[0]);
  const [aberta, setAberta] = useState<LinhaAberta | null>(null);
  const { nomeDe } = usePessoas();
  const linhas = leitura.ranking[dimensao.linhas];
  // A chave é o id da categoria, o nome da tag ou o id da pessoa (vazia, o conjunto).
  const nomesDaChave: Record<Dimensao, (chave: string | null) => string> = {
    categoria: (chave) => nomePorId(categorias, chave ?? ""),
    tag: (chave) => `#${chave}`,
    pessoa: (chave) => (chave ? nomeDe(chave) : "Conjunto"),
  };
  const nome = nomesDaChave[dimensao.id];
  const maior = Math.max(...linhas.map((l) => l.centavos), 1);
  const total = leitura.despesas.realizado_centavos + leitura.despesas.previsto_centavos;
  return (
    <section aria-label="Ranking">
      <h3>Ranking</h3>
      <div className="alternancia tres" role="group" aria-label="Ranking por">
        {DIMENSOES.map((d) => (
          <button key={d.id} className={dimensao.id === d.id ? undefined : "secundario"} aria-pressed={dimensao.id === d.id} onClick={() => setDimensao(d)}>
            {d.nome}
          </button>
        ))}
      </div>
      {linhas.length === 0 ? (
        <p className="vazio">{dimensao.vazio}</p>
      ) : (
        <ol className="ranking">
          {linhas.map((l) => (
            <li key={l.chave ?? "conjunto"}>
              <button onClick={() => setAberta({ nome: nome(l.chave), centavos: l.centavos, ids: l.lancamento_ids, busca: buscaDaLinha(leitura.mes, dimensao.id, l.chave) })}>
                <span className="nome">{nome(l.chave)}</span>
                <span className="valor-da-linha">{formatarCentavos(l.centavos)}</span>
                <span className="trilho" aria-hidden="true">
                  <span style={{ width: `${(Math.max(l.centavos, 0) * 100) / maior}%` }} />
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
      <p className="vazio">
        Toque numa linha para ver os lançamentos.
        {dimensao.somaMais && ` Um lançamento conta inteiro em cada ${dimensao.id} que tem, então as linhas podem somar mais que as despesas do mês (${formatarCentavos(total)}).`}
      </p>
      {aberta && <FolhaDoRanking linha={aberta} categorias={categorias} lancamentos={lancamentos} aoFechar={() => setAberta(null)} />}
    </section>
  );
}

const SITUACAO: Record<LeituraDoMes["situacao"], string> = { passado: "mês fechado", atual: "mês atual", futuro: "mês que vem pela frente" };

/** A aba Mês: navega mês a mês; o mês passado mostra o fechamento, o atual e o futuro, a barra. */
export function TelaDoMes({ mes = hoje().slice(0, 7) }: { mes?: string }) {
  const { dados: leitura, atualizadoEm, semDados, buscar } = useMes(mes);
  const { categorias } = useCadastro();
  const { lancamentos } = useLancamentos();

  return (
    <section className="aba-mes">
      <h2 className="oculto">Mês</h2>
      <nav className="navegacao-do-mes" aria-label="Meses">
        <a className="botao secundario" href={`#/mes/${mesVizinho(mes, -1)}`} aria-label="Mês anterior">
          ‹
        </a>
        <div>
          <h3 className="nome-do-mes">{nomeDoMes(mes).replace(/^./, (c) => c.toUpperCase())}</h3>
          {leitura && <p className="vazio">{SITUACAO[leitura.situacao]}</p>}
        </div>
        <a className="botao secundario" href={`#/mes/${mesVizinho(mes, 1)}`} aria-label="Próximo mês">
          ›
        </a>
      </nav>
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar este mês.
        </p>
      )}
      {leitura && (
        <>
          {leitura.situacao === "passado" ? <Fechamento leitura={leitura} categorias={categorias} /> : <BarraDoMes leitura={leitura} />}
          <AEscolher leitura={leitura} categorias={categorias} lancamentos={lancamentos ?? []} aoEscolher={() => void buscar()} />
          <Itens leitura={leitura} categorias={categorias} aoMudar={() => void buscar()} />
          <Comparacao leitura={leitura} categorias={categorias} />
          <Ranking leitura={leitura} categorias={categorias} lancamentos={lancamentos ?? []} />
        </>
      )}
    </section>
  );
}
