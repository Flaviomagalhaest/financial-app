import { useEffect, useRef, useState, type PointerEvent } from "react";
import { atualizadoAs, useFuturo, type Futuro } from "../dados";
import { formatarCentavos } from "../lancamentos/dinheiro";
import { marcasDoEixo, mesCurto, mesEAno, pontosDaProjecao, reaisCompactos, type Ponto } from "./apresentacao";

const ALTURA = 220;
const MARGEM = { topo: 12, direita: 12, base: 28, esquerda: 72 };

const LINHAS = [
  { chave: "realizado", nome: "Saldo realizado", classe: "serie-realizado" },
  { chave: "soPrevistos", nome: "Só com os previstos", classe: "serie-previstos" },
  { chave: "comPlanejamento", nome: "Com o planejamento", classe: "serie-planejamento" },
] as const;

/** A largura do elemento em pixels, para o gráfico desenhar o texto no tamanho de verdade. */
function useLargura() {
  const ref = useRef<HTMLDivElement>(null);
  const [largura, setLargura] = useState(0);
  useEffect(() => {
    const elemento = ref.current;
    if (!elemento) return;
    const observador = new ResizeObserver(([entrada]) => setLargura(entrada.contentRect.width));
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);
  return { ref, largura };
}

/** Os trechos contínuos de uma linha, pulando os meses sem valor. */
function trechos(pontos: Ponto[], chave: (typeof LINHAS)[number]["chave"], x: (i: number) => number, y: (v: number) => number) {
  const lista: string[] = [];
  let atual: string[] = [];
  pontos.forEach((p, i) => {
    const v = p[chave];
    if (v == null) {
      if (atual.length > 1) lista.push(atual.join(" "));
      atual = [];
    } else atual.push(`${x(i)},${y(v)}`);
  });
  if (atual.length > 1) lista.push(atual.join(" "));
  return lista;
}

function GraficoDaProjecao({ pontos, passados }: { pontos: Ponto[]; passados: number }) {
  const { ref, largura } = useLargura();
  const [foco, setFoco] = useState<number | null>(null);
  const valores = pontos.flatMap((p) => [p.realizado, p.soPrevistos, p.comPlanejamento]).filter((v): v is number => v != null);
  const marcas = marcasDoEixo(Math.min(0, ...valores), Math.max(0, ...valores));
  const [minimo, maximo] = [marcas[0], marcas.at(-1)!];
  const area = Math.max(largura - MARGEM.esquerda - MARGEM.direita, 1);
  const coluna = area / pontos.length;
  const x = (i: number) => MARGEM.esquerda + (i + 0.5) * coluna;
  const y = (v: number) => MARGEM.topo + ((maximo - v) / (maximo - minimo)) * (ALTURA - MARGEM.topo - MARGEM.base);
  const inicioDoFuturo = MARGEM.esquerda + passados * coluna;

  function aoMover(evento: PointerEvent<SVGRectElement>) {
    const caixa = evento.currentTarget.getBoundingClientRect();
    const i = Math.floor((evento.clientX - caixa.left) / coluna);
    setFoco(Math.min(Math.max(i, 0), pontos.length - 1));
  }

  const focado = foco == null ? null : pontos[foco];
  // Sem o ponteiro em cima, a leitura mostra o fim do mês atual.
  const lido = focado ?? pontos[passados] ?? pontos[0];
  // O último fim de mês que passou, de onde as duas linhas do futuro saem.
  const ultimoRealizado = pontos[passados - 1]?.realizado != null ? passados - 1 : -1;

  return (
    <div className="grafico" ref={ref}>
      {largura > 0 && (
        <svg width={largura} height={ALTURA} role="img" aria-label="Gráfico da projeção de saldo; os valores estão na tabela dos próximos meses">
          <rect className="futuro-fundo" x={inicioDoFuturo} y={MARGEM.topo} width={MARGEM.esquerda + area - inicioDoFuturo} height={ALTURA - MARGEM.topo - MARGEM.base} />
          {marcas.map((v) => (
            <g key={v}>
              <line className={v === 0 ? "eixo-zero" : "grade"} x1={MARGEM.esquerda} x2={MARGEM.esquerda + area} y1={y(v)} y2={y(v)} />
              <text className="rotulo" x={MARGEM.esquerda - 8} y={y(v)} dy="0.32em" textAnchor="end">
                {reaisCompactos(v)}
              </text>
            </g>
          ))}
          {pontos.map(
            (p, i) =>
              i % 3 === 0 && (
                <text key={p.mes} className="rotulo" x={x(i)} y={ALTURA - 8} textAnchor="middle">
                  {mesCurto(p.mes)}
                </text>
              ),
          )}
          <text className="rotulo" x={inicioDoFuturo + 4} y={MARGEM.topo + 12}>
            hoje
          </text>
          {LINHAS.map((linha) =>
            trechos(pontos, linha.chave, x, y).map((pontosDoTrecho) => <polyline key={`${linha.chave}${pontosDoTrecho}`} className={linha.classe} points={pontosDoTrecho} />),
          )}
          {ultimoRealizado >= 0 && <circle className="ponta serie-realizado" cx={x(ultimoRealizado)} cy={y(pontos[ultimoRealizado].realizado!)} r={4} />}
          {focado && foco != null && (
            <g>
              <line className="mira" x1={x(foco)} x2={x(foco)} y1={MARGEM.topo} y2={ALTURA - MARGEM.base} />
              {LINHAS.map((linha) => focado[linha.chave] != null && <circle key={linha.chave} className={`ponta ${linha.classe}`} cx={x(foco)} cy={y(focado[linha.chave]!)} r={4} />)}
            </g>
          )}
          <rect
            className="alvo"
            x={MARGEM.esquerda}
            y={0}
            width={area}
            height={ALTURA}
            onPointerMove={aoMover}
            onPointerDown={aoMover}
            onPointerLeave={() => setFoco(null)}
          />
        </svg>
      )}
      <p className="leitura" aria-live="polite">
        <strong>Fim de {mesEAno(lido.mes)}</strong>
        {LINHAS.map(
          (linha) =>
            lido[linha.chave] != null &&
            !(linha.chave !== "realizado" && lido.realizado != null) && (
              <span key={linha.chave}>
                <i className={`amostra ${linha.classe}`} aria-hidden="true" />
                {linha.nome}: {formatarCentavos(lido[linha.chave]!)}
              </span>
            ),
        )}
      </p>
    </div>
  );
}

function Legenda() {
  return (
    <ul className="legenda">
      {LINHAS.map((linha) => (
        <li key={linha.chave}>
          <svg width="24" height="8" aria-hidden="true">
            <line className={linha.classe} x1="0" x2="24" y1="4" y2="4" />
          </svg>
          {linha.nome}
        </li>
      ))}
    </ul>
  );
}

const comSinal = (centavos: number) => (centavos > 0 ? `+${formatarCentavos(centavos)}` : formatarCentavos(centavos));
const descontado = (centavos: number) => (centavos === 0 ? formatarCentavos(0) : formatarCentavos(-centavos));

function TabelaDosProximosMeses({ futuro }: { futuro: Futuro }) {
  return (
    <div className="rolavel-de-lado">
      <table className="tabela">
        <thead>
          <tr>
            <th scope="col">Mês</th>
            <th scope="col">Previstos</th>
            <th scope="col">Faturas</th>
            <th scope="col">Planejamento</th>
            <th scope="col">Fim, só previstos</th>
            <th scope="col">Fim, com planejamento</th>
          </tr>
        </thead>
        <tbody>
          {futuro.proximos_meses.map((m) => (
            <tr key={m.mes}>
              <th scope="row">{mesEAno(m.mes)}</th>
              <td>{comSinal(m.previstos_centavos)}</td>
              <td>{descontado(m.faturas_centavos)}</td>
              <td>{descontado(m.planejamento_centavos)}</td>
              <td className={m.so_previstos_centavos < 0 ? "negativo" : undefined}>{formatarCentavos(m.so_previstos_centavos)}</td>
              <td className={m.com_planejamento_centavos < 0 ? "negativo" : undefined}>
                <strong>{formatarCentavos(m.com_planejamento_centavos)}</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A aba Futuro: a projeção de saldo (realizado no passado e as duas linhas adiante) e a tabela dos próximos meses. */
export function TelaDoFuturo() {
  const { dados, atualizadoEm, semDados } = useFuturo();
  const esteMes = dados?.proximos_meses[0];

  return (
    <section>
      <h2>Futuro</h2>
      {atualizadoEm && <p className="vazio">Sem internet: {atualizadoAs(atualizadoEm)}</p>}
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: não foi possível carregar a projeção.
        </p>
      )}
      {dados && esteMes && (
        <>
          <section aria-label="Projeção de saldo" className="projecao">
            <h3>Projeção de saldo</h3>
            <p>
              Hoje, nas contas: <strong>{formatarCentavos(dados.saldo_hoje_centavos)}</strong>. No fim de {mesEAno(esteMes.mes)}:{" "}
              <strong className={esteMes.com_planejamento_centavos < 0 ? "negativo" : undefined}>{formatarCentavos(esteMes.com_planejamento_centavos)}</strong>{" "}
              com o planejamento, {formatarCentavos(esteMes.so_previstos_centavos)} só com os previstos.
            </p>
            <Legenda />
            <GraficoDaProjecao pontos={pontosDaProjecao(dados)} passados={dados.passado.length} />
            <p className="vazio">
              A soma das contas no fim de cada mês. Cada fatura sai no mês dela. A linha com o planejamento também desconta o que ainda falta gastar de cada item. Sem
              saldo antes da abertura das contas.
            </p>
          </section>
          <section aria-label="Próximos meses">
            <h3>Próximos meses</h3>
            <TabelaDosProximosMeses futuro={dados} />
          </section>
        </>
      )}
    </section>
  );
}
