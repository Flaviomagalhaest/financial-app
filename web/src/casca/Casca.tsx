import type { ReactNode } from "react";
import { ListaDeLancamentos } from "../lancamentos/ListaDeLancamentos";
import { TelaDeConfiguracao } from "../configuracao/TelaDeConfiguracao";
import { TelaDeLancamento } from "../lancamentos/TelaDeLancamento";
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
  const { rota, id } = useRota();
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
            <a href="#/configuracao">Contas e categorias</a>
          </section>
        )}
        {rota === "novo" && <TelaDeLancamento key={id ?? "novo"} id={id} />}
        {rota === "configuracao" && <TelaDeConfiguracao />}
        {rota === "historico" && <ListaDeLancamentos />}
        {aba && aba.id !== "hoje" && aba.id !== "historico" && <Vazia nome={aba.nome} />}
      </main>
    </div>
  );
}
