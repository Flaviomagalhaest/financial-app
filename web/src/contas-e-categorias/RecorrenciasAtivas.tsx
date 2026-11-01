import { useCallback, useState, type ReactNode } from "react";
import { useCadastro, useRecorrencias, type RecorrenciaNaTela } from "../dados";
import { plural, tituloDoLancamento } from "../lancamentos/apresentacao";
import { dataPorExtenso, hoje } from "../lancamentos/datas";

/**
 * Arquivar conta, cartão ou categoria não mexe nas recorrências (ticket 97): a ativa, com previsto de
 * hoje em diante (o servidor manda o próximo), segue gerando ali até o casal trocar ou encerrar cada uma.
 * Devolve as ativas de um item, pela conta ou cartão e pelas categorias da regra, ou `null` enquanto as
 * recorrências não chegaram (aí não dá para saber se o arquivamento pede aviso).
 */
export function useRecorrenciasAtivas(): (id: string) => RecorrenciaNaTela[] | null {
  const { recorrencias } = useRecorrencias();
  return useCallback(
    (id: string) => {
      if (!recorrencias) return null;
      // A guardada pode ser de outro dia: o previsto que já passou não conta mais.
      const dia = hoje();
      return recorrencias.filter((r) => r.proximo_previsto && r.proximo_previsto.data >= dia && (r.conta_id === id || r.categoria_ids.includes(id)));
    },
    [recorrencias],
  );
}

/**
 * Arquivar com aviso: `tocar` arquiva direto, ou abre o aviso quando há recorrência ativa; desarquivar é
 * sempre direto. `painel` é o aviso antes de arquivar ou, no item arquivado, o lembrete das que seguem nele.
 * `alternar(arquivar)` grava e diz se deu certo.
 */
export function useArquivarComAviso({
  nome,
  oQue,
  arquivado,
  ativas,
  alternar,
}: {
  nome: string;
  /** "a conta", "o cartão" ou "a categoria". */
  oQue: string;
  arquivado: boolean;
  ativas: RecorrenciaNaTela[] | null;
  alternar: (arquivar: boolean) => Promise<boolean>;
}): { tocar: () => void; esperando: boolean; painel: ReactNode } {
  const [avisando, setAvisando] = useState(false);
  const lista = ativas ?? [];
  const tocar = () => (!arquivado && lista.length > 0 ? setAvisando(true) : void alternar(!arquivado));
  const painel = arquivado ? (
    <LembreteDeRecorrencias nome={nome} ativas={lista} />
  ) : avisando ? (
    <AvisoDeArquivar
      nome={nome}
      oQue={oQue}
      ativas={lista}
      aoArquivar={() => void alternar(true).then((ok) => ok && setAvisando(false))}
      aoCancelar={() => setAvisando(false)}
    />
  ) : null;
  return { tocar, esperando: !arquivado && ativas === null, painel };
}

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

function AvisoDeArquivar({
  nome,
  oQue,
  ativas,
  aoArquivar,
  aoCancelar,
}: {
  nome: string;
  oQue: string;
  ativas: RecorrenciaNaTela[];
  aoArquivar: () => void;
  aoCancelar: () => void;
}) {
  const uma = ativas.length === 1;
  return (
    <div className="aviso" role="group" aria-label={`Arquivar ${nome}`}>
      <p>
        {plural(ativas.length, "recorrência ativa usa", "recorrências ativas usam")} {oQue} {nome}. {uma ? "Ela continua" : "Elas continuam"} gerando previstos
        aqui até vocês trocarem {oQue} ou encerrarem cada uma.
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

function LembreteDeRecorrencias({ nome, ativas }: { nome: string; ativas: RecorrenciaNaTela[] }) {
  if (ativas.length === 0) return null;
  return (
    <div className="aviso" role="group" aria-label={`Recorrências ativas em ${nome}`}>
      <p>{plural(ativas.length, "recorrência ativa segue", "recorrências ativas seguem")} gerando previstos aqui:</p>
      <ListaDeRecorrencias ativas={ativas} />
    </div>
  );
}
