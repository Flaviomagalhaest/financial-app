import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/cliente";
import type { LancamentoNaTela } from "../dados";
import { inicioDaJanela } from "../dados/armazem";
import { mesDepois } from "./datas";

/** Quantos meses da janela o Histórico desenha de início; a cada chegada ao fim da tela, mais um. */
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
 * O Histórico mês a mês (ticket 167, ADR 0025). Desenha os meses mais recentes da janela do aparelho
 * e, a cada `chegouAoFim`, mais um. Depois do fim da janela, com internet, lê do servidor um mês por
 * vez (`/api/meses/{mes}/lancamentos`) até o mais antigo que existe, sem guardar no aparelho. Sem
 * internet, `semInternet` diz que o fim da janela precisa dela.
 */
export function useHistoricoMesAMes(lancamentos: LancamentoNaTela[]) {
  const daJanela = porMes(lancamentos);
  const [desenhados, setDesenhados] = useState(MESES_DE_INICIO);
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

  const chegouAoFim = useCallback(() => {
    if (desenhados < daJanela.length) setDesenhados((n) => n + 1);
    else void lerDoServidor();
  }, [desenhados, daJanela.length, lerDoServidor]);

  const meses = [...daJanela.slice(0, desenhados), ...(desenhados >= daJanela.length ? doServidor : [])];
  const noFimDaJanela = desenhados >= daJanela.length;
  return { meses, chegouAoFim, semInternet: noFimDaJanela && semInternet, acabou: noFimDaJanela && acabou, depoisDe: doServidor.length + daJanela.length, noFimDaJanela };
}
