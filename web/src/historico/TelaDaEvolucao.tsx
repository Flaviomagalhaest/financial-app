import { useState } from "react";
import { atualizadoAs, useCadastro, useHistorico, type Historico } from "../dados";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { hoje } from "../lancamentos/datas";
import { mesEAno, POR_EXTENSO as MESES } from "../futuro/apresentacao";

type Metrica = Historico["metrica"];
type Visao = "doze-meses" | "por-ano" | "mesmo-mes";

const METRICAS: { id: Metrica; nome: string }[] = [
  { id: "despesas", nome: "Despesas" },
  { id: "receitas", nome: "Receitas" },
  { id: "sobra", nome: "Sobra" },
  { id: "categoria", nome: "Uma categoria" },
];
const VISOES: { id: Visao; nome: string }[] = [
  { id: "doze-meses", nome: "12 meses" },
  { id: "por-ano", nome: "Por ano" },
  { id: "mesmo-mes", nome: "Mesmo mês" },
];

type Barra = { chave: string; nome: string; centavos: number; contra?: number };

/** Uma linha por período: a barra do valor (e, se houver, a do período de comparação, mais clara). */
function Barras({ linhas, contra }: { linhas: Barra[]; contra?: string }) {
  const maior = Math.max(1, ...linhas.flatMap((l) => [Math.abs(l.centavos), Math.abs(l.contra ?? 0)]));
  const largura = (centavos: number) => `${(Math.abs(centavos) * 100) / maior}%`;
  return (
    <ol className="evolucao">
      {linhas.map((l) => (
        <li key={l.chave}>
          <span className="nome">{l.nome}</span>
          <span className="valor-da-linha">
            <span className={l.centavos < 0 ? "negativo" : undefined}>{formatarCentavos(l.centavos)}</span>
            {l.contra != null && (
              <span className="contra">
                {contra}: {formatarCentavos(l.contra)}
              </span>
            )}
          </span>
          <span className="trilho" aria-hidden="true">
            <span className={l.centavos < 0 ? "barra negativa" : "barra"} style={{ width: largura(l.centavos) }} />
            {l.contra != null && <span className="barra anterior" style={{ width: largura(l.contra) }} />}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Em relação ao período de comparação: "12% a mais", "7% a menos", ou nada quando ele é zero. */
function variacao(atual: number, anterior: number): string | null {
  if (anterior === 0) return null;
  const pontos = Math.round(((atual - anterior) * 100) / Math.abs(anterior));
  return pontos === 0 ? "igual" : `${Math.abs(pontos)}% ${pontos > 0 ? "a mais" : "a menos"}`;
}

/** A leitura da métrica escolhida; só existe com a categoria escolhida quando a métrica é "categoria". */
function Resultado({ metrica, categoriaId, visao, mesDoAno, nomeDaCategoria }: { metrica: Metrica; categoriaId?: string; visao: Visao; mesDoAno: number; nomeDaCategoria?: string }) {
  const { dados, atualizadoEm, semDados } = useHistorico(metrica, categoriaId, mesDoAno);
  const comparacao = dados && variacao(dados.total_centavos, dados.total_anterior_centavos);

  return (
    <>
      {atualizadoEm && <p className="vazio">Evolução sem internet, {atualizadoAs(atualizadoEm)}</p>}
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar a evolução.
        </p>
      )}
      {dados && (
        <>
          {visao === "doze-meses" && (
            <>
              <p>
                <strong>{formatarCentavos(dados.total_centavos)}</strong> nos últimos 12 meses
                {comparacao && `, ${comparacao} que nos 12 anteriores (${formatarCentavos(dados.total_anterior_centavos)})`}
                {nomeDaCategoria && ` · ${nomeDaCategoria}`}
              </p>
              <Barras
                contra="um ano antes"
                linhas={dados.doze_meses.map((m) => ({ chave: m.mes, nome: mesEAno(`${m.mes}-01`), centavos: m.centavos, contra: m.anterior_centavos }))}
              />
            </>
          )}
          {visao === "por-ano" && (
            <Barras linhas={dados.por_ano.map((a) => ({ chave: String(a.ano), nome: a.parcial ? `${a.ano} (até agora)` : String(a.ano), centavos: a.centavos }))} />
          )}
          {visao === "mesmo-mes" && (
            <Barras
              linhas={dados.mesmo_mes.anos.map((a) => ({ chave: String(a.ano), nome: `${MESES[dados.mesmo_mes.mes_do_ano - 1]} de ${a.ano}`, centavos: a.centavos }))}
            />
          )}
          <p className="vazio">Conta só o realizado, pelo mês em que cada lançamento conta (no cartão, o da fatura).</p>
        </>
      )}
    </>
  );
}

/**
 * A evolução de longo prazo na aba Histórico: uma métrica por vez, em 12 meses contra os 12
 * anteriores, por ano desde o primeiro lançamento ou no mesmo mês de cada ano.
 */
export function TelaDaEvolucao() {
  const { categorias } = useCadastro();
  const [metrica, setMetrica] = useState<Metrica>("despesas");
  const [categoriaId, setCategoriaId] = useState("");
  const [visao, setVisao] = useState<Visao>("doze-meses");
  const [mesDoAno, setMesDoAno] = useState(Number(hoje().slice(5, 7)));
  const escolhida = categorias.find((c) => c.id === categoriaId);

  return (
    <section aria-label="Evolução" className="evolucao-da-aba">
      <h3>Evolução</h3>
      <div className="campos-da-evolucao">
        <label>
          Métrica
          <select value={metrica} onChange={(e) => setMetrica(e.target.value as Metrica)}>
            {METRICAS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nome}
              </option>
            ))}
          </select>
        </label>
        {metrica === "categoria" && (
          <label>
            Categoria
            <select value={categoriaId} onChange={(e) => setCategoriaId(e.target.value)}>
              <option value="">Escolha…</option>
              {categorias.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
            </select>
          </label>
        )}
      </div>
      <div className="abas-internas" role="group" aria-label="Período">
        {VISOES.map((v) => (
          <button key={v.id} className="secundario" aria-pressed={visao === v.id} onClick={() => setVisao(v.id)}>
            {v.nome}
          </button>
        ))}
      </div>
      {visao === "mesmo-mes" && (
        <label>
          Mês
          <select value={mesDoAno} onChange={(e) => setMesDoAno(Number(e.target.value))}>
            {MESES.map((nome, i) => (
              <option key={nome} value={i + 1}>
                {nome}
              </option>
            ))}
          </select>
        </label>
      )}
      {metrica === "categoria" && !categoriaId ? (
        <p className="vazio">Escolha uma categoria.</p>
      ) : (
        <Resultado metrica={metrica} categoriaId={metrica === "categoria" ? categoriaId : undefined} visao={visao} mesDoAno={mesDoAno} nomeDaCategoria={escolhida?.nome} />
      )}
    </section>
  );
}
