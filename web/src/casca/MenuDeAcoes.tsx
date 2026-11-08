import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * O ⋯ de uma linha (ticket 204): reúne as ações que não são a principal da linha. Abre por cima do
 * conteúdo, fecha ao escolher, ao tocar fora, com Esc e quando a rota muda; fechado, as ações nem
 * estão na página. `rotulo` é o nome do botão para o leitor de tela ("Mais ações Mercado").
 */
export function MenuDeAcoes({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  const menu = useRef<HTMLDetailsElement>(null);
  const [aberto, setAberto] = useState(false);
  useEffect(() => {
    if (!aberto) return;
    const fechar = () => setAberto(false);
    const fora = (e: PointerEvent) => !menu.current?.contains(e.target as Node) && fechar();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && fechar();
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
    <details className="menu" ref={menu} open={aberto} onToggle={(e) => setAberto(e.currentTarget.open)}>
      <summary aria-label={rotulo}>⋯</summary>
      {aberto && (
        <div className="itens-do-menu" onClick={() => setAberto(false)}>
          {children}
        </div>
      )}
    </details>
  );
}
