import { useCallback } from "react";
import { useCadastro, useRecorrencias, type RecorrenciaNaTela } from "../dados";
import { tituloDoLancamento } from "../lancamentos/apresentacao";
import { dataPorExtenso } from "../lancamentos/datas";

/**
 * Arquivar conta, cartão ou categoria não mexe nas recorrências (ticket 97): a ativa (com previsto de
 * hoje em diante, que o servidor manda) segue gerando ali até o casal trocar ou encerrar cada uma.
 * Devolve as ativas de um item: as que o têm como conta ou cartão, ou entre as categorias.
 */
export function useRecorrenciasAtivas(): (id: string) => RecorrenciaNaTela[] {
  const { recorrencias } = useRecorrencias();
  return useCallback(
    (id: string) => (recorrencias ?? []).filter((r) => r.proximo_previsto && (r.conta_id === id || r.categoria_ids.includes(id))),
    [recorrencias],
  );
}

const quantas = (n: number, uma: string, varias: string) => (n === 1 ? `1 ${uma}` : `${n} ${varias}`);

/** As recorrências, cada uma abrindo a tela dela pelo próximo previsto. */
function ListaDeRecorrencias({ ativas }: { ativas: RecorrenciaNaTela[] }) {
  const { categorias } = useCadastro();
  return (
    <ul>
      {ativas.map((r) => (
        <li key={r.id}>
          <a href={`#/recorrencia/${r.proximo_previsto!.id}`}>
            {tituloDoLancamento(r, categorias)}, próxima em {dataPorExtenso(r.proximo_previsto!.data)}
          </a>
        </li>
      ))}
    </ul>
  );
}

/** Antes de arquivar: as recorrências ativas seguem gerando no item até o casal trocar ou encerrar cada uma. */
export function AvisoDeArquivar({
  nome,
  oQue,
  ativas,
  aoArquivar,
  aoCancelar,
}: {
  nome: string;
  /** "a conta", "o cartão" ou "a categoria". */
  oQue: string;
  ativas: RecorrenciaNaTela[];
  aoArquivar: () => void;
  aoCancelar: () => void;
}) {
  const n = ativas.length;
  return (
    <div className="aviso" role="group" aria-label={`Arquivar ${nome}`}>
      <p>
        {quantas(n, "recorrência ativa usa", "recorrências ativas usam")} {oQue} {nome}. {n === 1 ? "Ela continua" : "Elas continuam"} gerando previstos aqui até vocês
        trocarem {oQue} ou encerrarem cada uma.
      </p>
      <ListaDeRecorrencias ativas={ativas} />
      <div className="acoes">
        <button type="button" onClick={aoArquivar}>
          Arquivar mesmo assim
        </button>
        <button type="button" className="secundario" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

/** No item arquivado, enquanto alguma recorrência ativa segue gerando nele. */
export function LembreteDeRecorrencias({ nome, ativas }: { nome: string; ativas: RecorrenciaNaTela[] }) {
  if (ativas.length === 0) return null;
  const n = ativas.length;
  return (
    <div className="aviso" role="group" aria-label={`Recorrências ativas em ${nome}`}>
      <p>{quantas(n, "recorrência ativa segue", "recorrências ativas seguem")} gerando previstos aqui:</p>
      <ListaDeRecorrencias ativas={ativas} />
    </div>
  );
}
