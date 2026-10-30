import { useEffect, useState } from "react";
import {
  criteriosDoEndereco,
  enderecoDaBusca,
  useBusca,
  useCadastro,
  usePessoas,
  type Criterios,
  type LancamentoNaTela,
  type ParcelamentoNaTela,
  type Transferencia,
} from "../dados";
import { nomePorId, tituloDoLancamento, ValorComSinal } from "../lancamentos/apresentacao";
import { dataPorExtenso } from "../lancamentos/datas";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { mesPorExtenso } from "../cartoes/apresentacao";
import { SITUACOES, TIPOS } from "./apresentacao";
import { FolhaDeFiltros } from "./FolhaDeFiltros";

type Cadastro = ReturnType<typeof useCadastro>;

/** `3` de `10` vira `03/10`, como a fatura mostra a parcela. */
const numeroDaParcela = (parcela: number, parcelas: number) => `${String(parcela).padStart(2, "0")}/${String(parcelas).padStart(2, "0")}`;

/** Um filtro escolhido, como ficha que se tira com um toque. */
type Ficha = { rotulo: string; tirar: (c: Criterios) => Criterios };

function fichasDos(criterios: Criterios, { contasECartoes, cartoes, categorias }: Cadastro, nomeDe: (id: string) => string): Ficha[] {
  const sem = <K extends keyof Criterios>(campo: K, valor?: string): Ficha["tirar"] =>
    (c) => ({ ...c, [campo]: valor === undefined ? undefined : ((c[campo] ?? []) as string[]).filter((v) => v !== valor) });
  const fichas: Ficha[] = [
    ...(criterios.tipos ?? []).map((t) => ({ rotulo: TIPOS[t], tirar: sem("tipos", t) })),
    ...(criterios.situacoes ?? []).map((s) => ({ rotulo: SITUACOES[s], tirar: sem("situacoes", s) })),
  ];
  if (criterios.periodo_de) fichas.push({ rotulo: `De ${dataPorExtenso(criterios.periodo_de)}`, tirar: sem("periodo_de") });
  if (criterios.periodo_ate) fichas.push({ rotulo: `Até ${dataPorExtenso(criterios.periodo_ate)}`, tirar: sem("periodo_ate") });
  if (criterios.fatura) {
    const cartao = criterios.fatura.cartao_id && nomePorId(cartoes, criterios.fatura.cartao_id);
    fichas.push({ rotulo: cartao ? `Fatura ${mesPorExtenso(criterios.fatura.mes)} · ${cartao}` : `Conta em ${mesPorExtenso(criterios.fatura.mes)}`, tirar: sem("fatura") });
  }
  if (criterios.valor_minimo_centavos != null) fichas.push({ rotulo: `A partir de ${formatarCentavos(criterios.valor_minimo_centavos)}`, tirar: sem("valor_minimo_centavos") });
  if (criterios.valor_maximo_centavos != null) fichas.push({ rotulo: `Até ${formatarCentavos(criterios.valor_maximo_centavos)}`, tirar: sem("valor_maximo_centavos") });
  fichas.push(...(criterios.categoria_ids ?? []).map((id) => ({ rotulo: nomePorId(categorias, id), tirar: sem("categoria_ids", id) })));
  if (criterios.sem_categoria) fichas.push({ rotulo: "Sem categoria", tirar: sem("sem_categoria") });
  fichas.push(...(criterios.tags ?? []).map((t) => ({ rotulo: `#${t}`, tirar: sem("tags", t) })));
  if (criterios.sem_tag) fichas.push({ rotulo: "Sem tag", tirar: sem("sem_tag") });
  fichas.push(...(criterios.conta_ids ?? []).map((id) => ({ rotulo: nomePorId(contasECartoes, id), tirar: sem("conta_ids", id) })));
  if (criterios.conjunto) fichas.push({ rotulo: "Conjunto", tirar: sem("conjunto") });
  fichas.push(...(criterios.pessoas ?? []).map((id) => ({ rotulo: nomeDe(id), tirar: sem("pessoas", id) })));
  return fichas;
}

/**
 * O que a linha mostra embaixo do título: data da compra, onde, categorias, tags, fatura e situação.
 * A parcela, que aparece dentro do parcelamento, mostra a situação sempre e não repete a data.
 */
function Detalhes({ l, cadastro, parcela = false }: { l: LancamentoNaTela; cadastro: Cadastro; parcela?: boolean }) {
  return (
    <p className="vazio">
      {!parcela && `${dataPorExtenso(l.data)} · `}
      {nomePorId(cadastro.contasECartoes, l.conta_id)} · {l.categoria_ids.map((c) => nomePorId(cadastro.categorias, c)).join(", ")}
      {l.tags?.length ? ` · ${l.tags.map((t) => `#${t}`).join(" ")}` : ""}
      {l.fatura_mes && ` · fatura de ${mesPorExtenso(l.fatura_mes)}`}
      {l.situacao === "previsto" ? (l.atrasado ? " · previsto, atrasado" : " · previsto") : parcela && " · realizado"}
      {l.naoEnviado && " · ⏳ não enviado"}
    </p>
  );
}

function LinhaDoLancamento({ l, cadastro }: { l: LancamentoNaTela; cadastro: Cadastro }) {
  const titulo = tituloDoLancamento(l, cadastro.categorias);
  return (
    <li>
      <div>
        <strong>
          {titulo}
          {l.parcela && l.parcelas ? ` ${numeroDaParcela(l.parcela, l.parcelas)}` : ""}
        </strong>
        <ValorComSinal l={l} />
      </div>
      <Detalhes l={l} cadastro={cadastro} />
      <a href={`#/novo/${l.id}`} aria-label={`Editar ${titulo}`}>
        Editar
      </a>
    </li>
  );
}

/** O parcelamento numa linha, com o total; tocar abre as parcelas (ADR 0013). */
function LinhaDoParcelamento({ parcelamento, cadastro }: { parcelamento: ParcelamentoNaTela<LancamentoNaTela>; cadastro: Cadastro }) {
  const [aberta, setAberta] = useState(false);
  const titulo = parcelamento.descricao || tituloDoLancamento(parcelamento.lancamentos[0], cadastro.categorias);
  return (
    <li>
      <div>
        <button className="linha-que-abre" aria-expanded={aberta} onClick={() => setAberta(!aberta)}>
          <strong>{titulo}</strong> · {parcelamento.parcelas}x
        </button>
        <ValorComSinal l={{ ...parcelamento.lancamentos[0], valor_centavos: parcelamento.valor_centavos }} />
      </div>
      <p className="vazio">
        {dataPorExtenso(parcelamento.data)} · parcelado
        {parcelamento.lancamentos.length < parcelamento.parcelas && `, ${parcelamento.lancamentos.length} das ${parcelamento.parcelas} parcelas na busca`}
      </p>
      {aberta && (
        <ul className="lista parcelas" aria-label={`Parcelas de ${titulo}`}>
          {parcelamento.lancamentos.map((p) => (
            <li key={p.id}>
              <div>
                <span>{p.parcela && numeroDaParcela(p.parcela, parcelamento.parcelas)}</span>
                <ValorComSinal l={p} />
              </div>
              <Detalhes l={p} cadastro={cadastro} parcela />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function LinhaDaTransferencia({ t, cadastro }: { t: Transferencia; cadastro: Cadastro }) {
  const pagamento = !!t.fatura_mes;
  return (
    <li>
      <div>
        <strong>{t.descricao || (pagamento ? "Pagamento de fatura" : "Transferência")}</strong>
        <span>⇄ {formatarCentavos(t.valor_centavos)}</span>
      </div>
      <p className="vazio">
        {dataPorExtenso(t.data)} · {nomePorId(cadastro.contasECartoes, t.conta_origem_id)} → {nomePorId(cadastro.contasECartoes, t.conta_destino_id)}
        {t.fatura_mes && ` · fatura de ${mesPorExtenso(t.fatura_mes)}`}
        {t.categoria_id && ` · ${nomePorId(cadastro.categorias, t.categoria_id)}`}
        {t.situacao === "previsto" && " · previsto"}
      </p>
    </li>
  );
}

/**
 * A busca em todo o histórico (ticket 59): texto livre e filtros combinados, com os totais no topo.
 * Os critérios ficam no endereço (`#/busca?...`), que é o que os atalhos do Mês e dos Cartões abrem.
 */
export function TelaDaBusca({ consulta }: { consulta: string }) {
  const [criterios, setCriterios] = useState<Criterios>(() => criteriosDoEndereco(consulta));
  const [texto, setTexto] = useState(criterios.texto ?? "");
  const [filtrando, setFiltrando] = useState(false);
  const cadastro = useCadastro();
  const { nomeDe } = usePessoas();
  const { resultado, parcial, carregando, temMais, carregarMais } = useBusca(criterios);

  // O texto vai para a busca quando a pessoa para de digitar.
  useEffect(() => {
    const espera = setTimeout(() => setCriterios((c) => (c.texto ?? "") === texto ? c : { ...c, texto }), 300);
    return () => clearTimeout(espera);
  }, [texto]);

  // O endereço acompanha o que se escolheu, sem nova entrada no histórico do navegador.
  useEffect(() => {
    history.replaceState(null, "", enderecoDaBusca(criterios));
  }, [criterios]);

  const fichas = fichasDos(criterios, cadastro, nomeDe);
  const totais = resultado?.totais;
  const previstos = totais && (totais.despesas.previsto_centavos !== 0 || totais.receitas.previsto_centavos !== 0);

  return (
    <section className="busca">
      <h2>Busca</h2>
      <div className="linha">
        <label className="oculto" htmlFor="texto-da-busca">
          Buscar na descrição
        </label>
        <input id="texto-da-busca" type="search" value={texto} placeholder="Buscar na descrição" autoComplete="off" onChange={(e) => setTexto(e.target.value)} />
        <button type="button" className="secundario" onClick={() => setFiltrando(true)}>
          Filtros{fichas.length ? ` (${fichas.length})` : ""}
        </button>
      </div>
      {fichas.length > 0 && (
        <ul className="fileira fichas-da-busca" aria-label="Filtros escolhidos">
          {fichas.map((f) => (
            <li key={f.rotulo}>
              <button type="button" className="ficha marcada" aria-label={`Tirar o filtro ${f.rotulo}`} onClick={() => setCriterios(f.tirar(criterios))}>
                {f.rotulo} ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="alternancia" role="group" aria-label="Ordem">
        {(["recentes", "valor"] as const).map((ordem) => {
          const escolhida = (criterios.ordem ?? "recentes") === ordem;
          return (
            <button key={ordem} type="button" className={escolhida ? undefined : "secundario"} aria-pressed={escolhida} onClick={() => setCriterios({ ...criterios, ordem })}>
              {ordem === "recentes" ? "Mais recentes" : "Maior valor"}
            </button>
          );
        })}
      </div>
      {!criterios.fatura && <p className="vazio">Período pela data da compra; a aba Mês conta pelo mês da fatura.</p>}
      {parcial && (
        <p role="status" className="erro">
          Resultado parcial, sem internet: só o que este aparelho guarda.
        </p>
      )}
      {totais && (
        <dl className="totais-da-busca" aria-label="Totais da busca">
          <div>
            <dt>Lançamentos</dt>
            <dd>{totais.quantidade}</dd>
          </div>
          <div>
            <dt>Despesas</dt>
            <dd>{formatarCentavos(totais.despesas.realizado_centavos)}</dd>
          </div>
          <div>
            <dt>Receitas</dt>
            <dd>{formatarCentavos(totais.receitas.realizado_centavos)}</dd>
          </div>
          <div>
            <dt>Saldo</dt>
            <dd>{formatarCentavos(totais.saldo.realizado_centavos)}</dd>
          </div>
        </dl>
      )}
      {previstos && (
        <p className="vazio" aria-label="Previstos à parte">
          Previstos à parte: {formatarCentavos(totais.despesas.previsto_centavos)} de despesas e {formatarCentavos(totais.receitas.previsto_centavos)} de receitas, saldo de{" "}
          {formatarCentavos(totais.saldo.previsto_centavos)}.
        </p>
      )}
      {totais && <p className="vazio">Transferências ficam fora dos totais.</p>}
      {!resultado && carregando && <p className="vazio">Buscando…</p>}
      {resultado && resultado.linhas.length === 0 && <p className="vazio">Nenhum lançamento com esses critérios.</p>}
      <ul className="lista" aria-label="Resultado da busca">
        {resultado?.linhas.map((linha) =>
          "parcelamento" in linha ? (
            <LinhaDoParcelamento key={linha.parcelamento.parcelamento_id} parcelamento={linha.parcelamento} cadastro={cadastro} />
          ) : "transferencia" in linha ? (
            <LinhaDaTransferencia key={linha.transferencia.id} t={linha.transferencia} cadastro={cadastro} />
          ) : (
            <LinhaDoLancamento key={linha.lancamento.id} l={linha.lancamento} cadastro={cadastro} />
          ),
        )}
      </ul>
      {temMais && (
        <button type="button" className="secundario" disabled={carregando} onClick={carregarMais}>
          Carregar mais
        </button>
      )}
      {filtrando && <FolhaDeFiltros criterios={criterios} onMudar={setCriterios} onFechar={() => setFiltrando(false)} />}
    </section>
  );
}
