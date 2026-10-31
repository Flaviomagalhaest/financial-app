import { useState } from "react";
import { desfazerLote, useConexao, useEdicoesEmLote, usePessoas, type DesfazerDaEdicaoEmLote, type EdicaoEmLote } from "../dados";
import { dataPorExtenso, quando } from "../lancamentos/datas";
import { config } from "../config";
import { contagem } from "./FolhaDaEdicaoEmLote";

type Pulado = DesfazerDaEdicaoEmLote["pulados"][number];

/**
 * As edições em lote dos últimos dias (ticket 61), cada uma com "Desfazer". O desfazer volta o que
 * a edição mudou, pula o que alguém mudou depois e diz quais. Só com internet.
 */
export function TelaDasEdicoesEmLote() {
  const { edicoes, semResposta, recarregar } = useEdicoesEmLote();
  const online = useConexao();
  const { euId, nomeDe } = usePessoas();
  const [desfazendo, setDesfazendo] = useState<string | null>(null);
  const [desfeita, setDesfeita] = useState<{ resumo: string; resultado: DesfazerDaEdicaoEmLote } | null>(null);
  const [recusa, setRecusa] = useState<string | null>(null);

  const quem = (id: string | null | undefined) => (id && id === euId ? "você" : nomeDe(id));
  const porque = (p: Pulado) =>
    p.motivo === "excluido"
      ? `excluído por ${quem(p.alterado_por)}`
      : p.motivo === "mudou_depois"
        ? `${quem(p.alterado_por)} mudou as categorias ou as tags depois${p.alterado_em ? `, ${quando(p.alterado_em)}` : ""}`
        : "uma categoria ou tag que ele tinha foi juntada a outra ou excluída";

  async function desfazer(edicao: EdicaoEmLote) {
    setDesfazendo(edicao.id);
    setRecusa(null);
    const resposta = await desfazerLote(edicao.id);
    setDesfazendo(null);
    if (typeof resposta === "string") return setRecusa(resposta);
    setDesfeita({ resumo: edicao.resumo, resultado: resposta });
    await recarregar();
  }

  return (
    <section className="edicoes-em-lote">
      <h2>Edições em lote</h2>
      <p className="vazio">
        Cada edição se desfaz por {config.desfazerEdicaoEmLoteDias} dias. O desfazer não mexe no que alguém mudou depois nos mesmos lançamentos.
      </p>
      {(semResposta || !online) && (
        <p role="status" className="erro">
          Sem internet: as edições em lote só aparecem e se desfazem com internet.
        </p>
      )}
      {desfeita && (
        <div role="status" className={desfeita.resultado.pulados.length ? "aviso" : undefined}>
          <p>
            Desfeita: {desfeita.resumo}, em {contagem(desfeita.resultado.desfeitos, "lançamento", "lançamentos")}.
          </p>
          {desfeita.resultado.pulados.length > 0 && (
            <>
              <p>{contagem(desfeita.resultado.pulados.length, "ficou como está", "ficaram como estão")}:</p>
              <ul aria-label="Pulados no desfazer">
                {desfeita.resultado.pulados.map((p) => (
                  <li key={p.lancamento_id}>
                    {p.descricao || "Sem descrição"}: {porque(p)}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
      {recusa && (
        <p role="alert" className="erro">
          {recusa}
        </p>
      )}
      {edicoes?.length === 0 && <p className="vazio">Nenhuma edição em lote para desfazer.</p>}
      <ul className="lista" aria-label="Edições em lote">
        {edicoes?.map((e) => (
          <li key={e.id}>
            <strong>{e.resumo}</strong>
            <p className="vazio">
              {contagem(e.lancamentos, "lançamento", "lançamentos")} · por {quem(e.criado_por)} {quando(e.criado_em)} · desfaz até{" "}
              {dataPorExtenso(new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(e.desfazer_ate)))}
            </p>
            {e.situacao === "aplicando" && <p className="erro">A gravação parou no meio: desfaça para voltar o que já foi gravado.</p>}
            <div className="acoes">
              <button type="button" className="secundario" disabled={!online || !!desfazendo} aria-label={`Desfazer ${e.resumo}`} onClick={() => void desfazer(e)}>
                {desfazendo === e.id ? "Desfazendo…" : "Desfazer"}
              </button>
            </div>
          </li>
        ))}
      </ul>
      <a href="#/busca">Voltar à busca</a>
    </section>
  );
}
