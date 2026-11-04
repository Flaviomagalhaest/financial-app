import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/cliente";
import type { LancamentoNaTela } from "../dados";
import { inicioDaJanela } from "../dados/armazem";
import { hoje, mesDepois } from "./datas";

/** Quantos meses o Histórico desenha de início, contando do atual para trás (o futuro vem todo); a cada chegada ao fim da tela, mais um. */
const MESES_DE_INICIO = 3;

export type MesDoHistorico = { mes: string; lancamentos: LancamentoNaTela[] };

/** O mês em que o lançamento conta (`AAAA-MM-01`): o da fatura, na compra no cartão; no resto, o da data. */
const mesDe = (l: LancamentoNaTela) => l.mes ?? `${l.data.slice(0, 7)}-01`;

/** Junta, na ordem em que vêm (do mais novo ao mais antigo), os lançamentos de cada mês. */
function porMes(lancamentos: LancamentoNaTela[]): MesDoHistorico[] {
  const grupos = new Map<string, LancamentoNaTela[]>();
  for (const l of lancamentos) {
    const mes = mesDe(l);
    grupos.set(mes, [...(grupos.get(mes) ?? []), l]);
  }
  return [...grupos].sort(([a], [b]) => (a < b ? 1 : -1)).map(([mes, ls]) => ({ mes, lancamentos: ls }));
}

/**
 * Os meses lidos do servidor depois dos da tela. Um mês que a tela já tem (a edição não enviada de um
 * lançamento antigo o põe lá) recebe só o que ainda não tem, para o mês e o lançamento não repetirem.
 */
function juntar(daTela: MesDoHistorico[], doServidor: MesDoHistorico[]): MesDoHistorico[] {
  const jaNaTela = new Set(daTela.flatMap((m) => m.lancamentos.map((l) => l.id)));
  const meses = daTela.map((m) => ({ ...m }));
  for (const { mes, lancamentos } of doServidor) {
    const novos = lancamentos.filter((l) => !jaNaTela.has(l.id));
    const dele = meses.find((m) => m.mes === mes);
    if (dele) dele.lancamentos = [...dele.lancamentos, ...novos];
    else if (novos.length > 0) meses.push({ mes, lancamentos: novos });
  }
  return meses.sort((a, b) => (a.mes < b.mes ? 1 : -1));
}

/**
 * O Histórico mês a mês (ticket 167, ADR 0025). Desenha os meses mais recentes da janela do aparelho
 * e, a cada `chegouAoFim`, mais um. Depois do fim da janela, com internet, lê do servidor um mês por
 * vez (`/api/meses/{mes}/lancamentos`) até o mais antigo que existe, sem guardar no aparelho. Sem
 * internet, `semInternet` diz que o fim da janela precisa dela.
 */
export function useHistoricoMesAMes(lancamentos: LancamentoNaTela[]) {
  const daJanela = porMes(lancamentos);
  // Quantos meses além dos de início a pessoa já pediu ao chegar ao fim da tela.
  const [alemDosDeInicio, setAlemDosDeInicio] = useState(0);
  const [doServidor, setDoServidor] = useState<MesDoHistorico[]>([]);
  const [semInternet, setSemInternet] = useState(false);
  const [acabou, setAcabou] = useState(false);
  const lendo = useRef(false);
  // O próximo mês a ler do servidor e o mais antigo que existe (lido uma vez).
  const proximo = useRef(mesDepois(inicioDaJanela(), -1));
  const maisAntigo = useRef<string | null | undefined>(undefined);

  const lerDoServidor = useCallback(async () => {
    if (lendo.current || acabou) return;
    lendo.current = true;
    try {
      if (!navigator.onLine) return setSemInternet(true);
      if (maisAntigo.current === undefined) {
        const { data } = await api.GET("/api/lancamentos-primeiro-mes");
        if (!data) return setSemInternet(true);
        maisAntigo.current = data.mes ?? null;
      }
      // Meses sem lançamento não têm cabeçalho: segue para o anterior até achar um.
      for (;;) {
        const mes = proximo.current;
        if (!maisAntigo.current || mes < maisAntigo.current) return setAcabou(true);
        const { data } = await api.GET("/api/meses/{mes}/lancamentos", { params: { path: { mes: mes.slice(0, 7) } } });
        if (!data) return setSemInternet(true);
        proximo.current = mesDepois(mes, -1);
        if (data.length > 0) {
          setDoServidor((antes) => [...antes, { mes, lancamentos: data.map((l) => ({ ...l, naoEnviado: false })) }]);
          return;
        }
      }
    } catch {
      setSemInternet(true);
    } finally {
      lendo.current = false;
    }
  }, [acabou]);

  // A rede voltou: o fim da janela tenta de novo.
  useEffect(() => {
    const voltou = () => setSemInternet(false);
    window.addEventListener("online", voltou);
    return () => window.removeEventListener("online", voltou);
  }, []);

  // O futuro (parcelas e previstos) vem inteiro na frente: os meses de início contam do atual.
  const mesAtual = `${hoje().slice(0, 7)}-01`;
  const futuros = daJanela.filter((m) => m.mes > mesAtual).length;
  const desenhados = futuros + MESES_DE_INICIO + alemDosDeInicio;

  const chegouAoFim = useCallback(() => {
    if (desenhados < daJanela.length) setAlemDosDeInicio((n) => n + 1);
    else void lerDoServidor();
  }, [desenhados, daJanela.length, lerDoServidor]);

  // O mês com algo na fila (não enviado, recusado, em conflito) aparece sempre: a pessoa precisa vê-lo.
  const daTela = daJanela.filter((m, i) => i < desenhados || m.lancamentos.some((l) => l.naoEnviado));
  const noFimDaJanelaAgora = desenhados >= daJanela.length;
  const meses = noFimDaJanelaAgora ? juntar(daTela, doServidor) : daTela;
  const noFimDaJanela = noFimDaJanelaAgora;
  return { meses, chegouAoFim, semInternet: noFimDaJanela && semInternet, acabou: noFimDaJanela && acabou, depoisDe: doServidor.length + daJanela.length, noFimDaJanela };
}
