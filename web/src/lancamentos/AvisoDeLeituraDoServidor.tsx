import type { ReactNode } from "react";

/**
 * Os avisos das telas que leem do servidor (ticket 165): `daUltimaLeitura` (a data da resposta guardada,
 * quando é ela que a tela mostra) e `semDados` (sem internet e sem resposta guardada). `oQue` completa
 * "as <oQue> são as da última leitura" e `precisam` o que vem depois de "Sem internet: ".
 */
export function AvisoDeLeituraDoServidor({ daUltimaLeitura, semDados, oQue, precisam }: { daUltimaLeitura: unknown; semDados: boolean; oQue: string; precisam: ReactNode }) {
  return (
    <>
      {daUltimaLeitura && <p className="vazio">Sem internet: {oQue} são as da última leitura.</p>}
      {semDados && (
        <p role="alert" className="erro">
          Sem internet: {precisam}
        </p>
      )}
    </>
  );
}
