import type { ReactNode } from "react";
import { ABAS, useRota } from "./rota";

type Props = { email: string; onSair: () => void; hoje: ReactNode };

function Vazia({ nome }: { nome: string }) {
  return (
    <section>
      <h2>{nome}</h2>
      <p className="vazio">Esta tela chega nas próximas etapas.</p>
    </section>
  );
}

/** Casca do app: navegação por abas (embaixo no celular, ao lado na tela larga) e a tela atual. */
export function Casca({ email, onSair, hoje }: Props) {
  const rota = useRota();
  const aba = ABAS.find((a) => a.id === rota);

  return (
    <div className="casca">
      <header className="topo">
        <h1>Financial App</h1>
        <p>Entrou como {email}</p>
        <button className="secundario" onClick={onSair}>
          Sair
        </button>
      </header>
      <nav className="abas" aria-label="Telas">
        {ABAS.map((a) => (
          <a key={a.id} href={`#/${a.id}`} aria-current={a.id === rota ? "page" : undefined}>
            {a.nome}
          </a>
        ))}
      </nav>
      <main>
        {rota === "hoje" && (
          <section>
            <h2>Hoje</h2>
            <a className="botao" href="#/novo">
              + Novo lançamento
            </a>
            {hoje}
          </section>
        )}
        {rota === "novo" && (
          <section>
            <h2>Novo lançamento</h2>
            <p className="vazio">O formulário chega na próxima etapa.</p>
            <a href="#/hoje">Voltar</a>
          </section>
        )}
        {aba && aba.id !== "hoje" && <Vazia nome={aba.nome} />}
      </main>
    </div>
  );
}
