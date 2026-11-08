import { useSyncExternalStore } from "react";

/**
 * Os atalhos da faixa verde da Hoje (ticket 204) ligam e desligam em Configurações. A escolha é deste
 * aparelho: fica no armazenamento do navegador, sem passar pelo servidor. Sem armazenamento (janela
 * privada, dados bloqueados), vale o padrão: ligados.
 */
const CHAVE = "financial-app:atalhos-da-faixa";
const AVISO = "atalhos-da-faixa";

function ler(): boolean {
  try {
    return localStorage.getItem(CHAVE) !== "desligados";
  } catch {
    return true;
  }
}

function assinar(aoMudar: () => void) {
  window.addEventListener(AVISO, aoMudar);
  window.addEventListener("storage", aoMudar);
  return () => {
    window.removeEventListener(AVISO, aoMudar);
    window.removeEventListener("storage", aoMudar);
  };
}

export function mudarAtalhosDaFaixa(ligados: boolean) {
  try {
    if (ligados) localStorage.removeItem(CHAVE);
    else localStorage.setItem(CHAVE, "desligados");
  } catch {
    // Sem armazenamento a escolha não se guarda; a tela segue o padrão.
  }
  window.dispatchEvent(new Event(AVISO));
}

export function useAtalhosDaFaixa(): boolean {
  return useSyncExternalStore(assinar, ler, () => true);
}
