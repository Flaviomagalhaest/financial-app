// A aba aberta numa versão anterior do app recarrega sozinha (ticket 168): quando o service worker
// de uma versão nova assume, e quando o banco do aparelho já está numa versão mais nova que o código
// dela (`VersionError`). O que estiver sendo digitado se perde: decisão do dono.

const MARCA = "financial-app-recarregou-em";
/** Uma recarga sozinha a cada 10 s, no máximo: o banco mais novo que o código não vira um laço. */
const INTERVALO = 10_000;

/** Recarrega a aba, se esta não recarregou sozinha há menos de 10 s. No service worker, nada. */
export function recarregarParaAVersaoNova() {
  if (typeof document === "undefined") return;
  try {
    const agora = Date.now();
    if (agora - Number(sessionStorage.getItem(MARCA) ?? 0) < INTERVALO) return;
    sessionStorage.setItem(MARCA, String(agora));
  } catch {
    // Sem onde marcar, não há como evitar o laço: a aba segue como está.
    return;
  }
  location.reload();
}

/**
 * Recarrega a aba quando outro service worker assume o controle dela. A primeira instalação também
 * dispara `controllerchange` (a página passa a ter controlador), mas ela já roda o código novo.
 */
export function recarregarQuandoAVersaoNovaAssumir(servico: ServiceWorkerContainer) {
  let controlada = !!servico.controller;
  servico.addEventListener("controllerchange", () => {
    if (controlada) recarregarParaAVersaoNova();
    controlada = true;
  });
}
