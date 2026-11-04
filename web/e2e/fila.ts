import { expect, type Page } from "@playwright/test";

/** A fila guardada no aparelho, com a recusa de cada pedido, lida direto do IndexedDB. */
export const filaDoAparelho = (page: Page) =>
  page.evaluate(
    () =>
      new Promise<unknown[]>((resolve, reject) => {
        const abertura = indexedDB.open("financial-app-dados");
        abertura.onerror = () => reject(abertura.error);
        abertura.onsuccess = () => {
          const pedido = abertura.result.transaction("fila").objectStore("fila").getAll();
          pedido.onsuccess = () => {
            abertura.result.close();
            resolve(pedido.result);
          };
        };
      }),
  );

/**
 * Espera a fila do aparelho esvaziar e confere o aviso depois. O aviso (`AvisoDaFila`) não aparece
 * enquanto a tela não leu a fila, então `toHaveCount(0)` sozinho passa na hora com o pedido ainda
 * na fila, e a janela cresce com a CPU ocupada (ticket 182).
 */
export async function esperarFilaVazia(page: Page, opcoes?: { timeout?: number }) {
  await expect.poll(() => filaDoAparelho(page), { message: "a fila do aparelho", ...opcoes }).toEqual([]);
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0, opcoes);
}
