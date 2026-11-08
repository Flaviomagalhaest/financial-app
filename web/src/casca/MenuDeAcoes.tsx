import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Um menu que abre por cima do conteúdo (ticket 204): o ⋯ de uma linha, que reúne as ações que não
 * são a principal dela, e o menu da conta no topo. Fecha ao escolher, ao tocar fora, com Esc (o foco
 * volta ao botão) e quando a rota muda; ao abrir, o foco vai para o primeiro item. Fechado, os itens
 * nem estão na página. `rotulo` é o nome do botão para o leitor de tela ("Mais ações Mercado").
 */
export function MenuDeAcoes({
  rotulo,
  children,
  classe = "menu",
  botao = "⋯",
  nomeDosItens,
}: {
  rotulo: string;
  children: ReactNode;
  /** A classe do menu: "menu" (o ⋯ da linha) ou "menu-da-conta". */
  classe?: string;
  /** O que o botão mostra; o padrão é o ⋯. */
  botao?: ReactNode;
  /** Nome do grupo de itens, para achá-lo pelo papel ("Menu da conta"). */
  nomeDosItens?: string;
}) {
  const menu = useRef<HTMLDetailsElement>(null);
  const [aberto, setAberto] = useState(false);
  useEffect(() => {
    if (!aberto) return;
    menu.current?.querySelector<HTMLElement>(".itens-do-menu a, .itens-do-menu button")?.focus();
    const fechar = () => setAberto(false);
    const fora = (e: PointerEvent) => !menu.current?.contains(e.target as Node) && fechar();
    const esc = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      fechar();
      menu.current?.querySelector("summary")?.focus();
    };
    window.addEventListener("hashchange", fechar);
    document.addEventListener("pointerdown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      window.removeEventListener("hashchange", fechar);
      document.removeEventListener("pointerdown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);
  return (
    <details className={classe} ref={menu} open={aberto} onToggle={(e) => setAberto(e.currentTarget.open)}>
      <summary aria-label={rotulo}>{botao}</summary>
      {aberto && (
        <div className="itens-do-menu" role="group" aria-label={nomeDosItens} onClick={() => setAberto(false)}>
          {children}
        </div>
      )}
    </details>
  );
}
