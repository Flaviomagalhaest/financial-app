import { useEffect, useState } from "react";
import { config } from "../config";
import { enviarAgora, useFila, usePessoas } from "../dados";

const AVISO_DE_NAO_ENVIADO_MS = config.avisoDeNaoEnviadoHoras * 3_600_000;

function useAgora(): number {
  const [agora, setAgora] = useState(Date.now);
  useEffect(() => {
    const relogio = setInterval(() => setAgora(Date.now()), 60_000);
    return () => clearInterval(relogio);
  }, []);
  return agora;
}

/** "1 lançamento não enviado", "2 recorrências não enviadas", "1 lançamento e 1 recorrência não enviados". */
function naoEnviados(lancamentos: number, recorrencias: number): string {
  const lanc = lancamentos === 1 ? "1 lançamento" : `${lancamentos} lançamentos`;
  const rec = recorrencias === 1 ? "1 recorrência" : `${recorrencias} recorrências`;
  if (!recorrencias) return `${lanc} ${lancamentos === 1 ? "não enviado" : "não enviados"}`;
  if (!lancamentos) return `${rec} ${recorrencias === 1 ? "não enviada" : "não enviadas"}`;
  return `${lanc} e ${rec} não enviados`;
}

/** Na Hoje: quantos lançamentos e recorrências não foram enviados, com "Enviar agora"; em destaque depois de 24 h. */
export function AvisoDaFila() {
  const fila = useFila();
  const { nomeDe } = usePessoas();
  const agora = useAgora();
  const [enviando, setEnviando] = useState(false);
  const [semInternet, setSemInternet] = useState(false);
  if (fila.length === 0) return null;
  const conflitos = fila.filter((item) => item.conflito).length;
  const recorrencias = fila.filter((item) => item.acao === "criar_recorrencia").length;
  // Só recorrências na fila: o motivo fala delas, no feminino.
  const soRecorrencias = recorrencias === fila.length;

  const atrasado = agora - fila[0].desde > AVISO_DE_NAO_ENVIADO_MS;
  const contar = (n: number, um: string, varios: string) => (n === 0 ? null : `${n} ${n === 1 ? um : varios}`);
  const exclusoes = fila.flatMap((item) => (item.exclusao ? [item.exclusao] : []));
  const quemExcluiu = [...new Set(exclusoes.map((e) => (e.por_voce ? "você" : nomeDe(e.excluido_por))))].join(" e ");
  const excluidos = contar(exclusoes.length, "excluído", "excluídos");
  const esperando = [
    contar(fila.filter((item) => item.recusa).length, soRecorrencias ? "recusada" : "recusado", soRecorrencias ? "recusadas" : "recusados"),
    excluidos && `${excluidos} por ${quemExcluiu}`,
  ].filter(Boolean);

  async function enviar() {
    setEnviando(true);
    setSemInternet(!(await enviarAgora()));
    setEnviando(false);
  }

  return (
    <div className={atrasado ? "aviso" : undefined} data-testid="nao-enviados">
      <p>
        {naoEnviados(fila.length - recorrencias, recorrencias)}
        {esperando.length > 0 && ` (${esperando.join(", ")}: veja no Histórico)`}
      </p>
      {conflitos > 0 && (
        <p className="erro">
          {conflitos === 1 ? "1 lançamento com conflito" : `${conflitos} lançamentos com conflito`}: decida no Histórico.
        </p>
      )}
      {atrasado && <p>Há mais de {config.avisoDeNaoEnviadoHoras} h sem enviar: abra com internet para enviar.</p>}
      {semInternet && <p className="vazio">Sem internet: os não enviados sobem quando a conexão voltar.</p>}
      <button type="button" className="secundario" disabled={enviando} onClick={() => void enviar()}>
        Enviar agora
      </button>
    </div>
  );
}
