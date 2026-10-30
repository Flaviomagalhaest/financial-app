import type { ReactNode } from "react";
import { Configuracoes } from "../configuracoes/Configuracoes";
import { ContasDaSemana } from "../lancamentos/ContasDaSemana";
import { ListaDeLancamentos } from "../lancamentos/ListaDeLancamentos";
import { NovoLancamento } from "../lancamentos/NovoLancamento";
import { TelaDeContasECategorias } from "../contas-e-categorias/TelaDeContasECategorias";
import { TelaDeConflito } from "../lancamentos/TelaDeConflito";
import { TelaDeLancamento } from "../lancamentos/TelaDeLancamento";
import { TelaDeCartoes } from "../cartoes/TelaDeCartoes";
import { TelaDaFatura } from "../cartoes/TelaDaFatura";
import { TelaDoMes } from "../mes/TelaDoMes";
import { TelaDoModelo } from "../mes/TelaDoModelo";
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
  const { rota, id, mes } = useRota();
  const aba = ABAS.find((a) => a.id === rota);

  return (
    <div className="casca">
      <header className="topo">
        <h1>Financial App</h1>
        <p>Entrou como {email}</p>
        <a href="#/configuracoes">Configurações</a>
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
            <ContasDaSemana />
            {hoje}
            <a href="#/contas-e-categorias">Contas e categorias</a>
          </section>
        )}
        {rota === "novo" && (id ? <TelaDeLancamento key={id} id={id} /> : <NovoLancamento />)}
        {rota === "conflito" && id && <TelaDeConflito key={id} id={id} />}
        {rota === "contas-e-categorias" && <TelaDeContasECategorias />}
        {rota === "configuracoes" && <Configuracoes />}
        {rota === "historico" && <ListaDeLancamentos />}
        {rota === "mes" && <TelaDoMes key={mes ?? "atual"} mes={mes} />}
        {rota === "modelo-do-planejamento" && <TelaDoModelo />}
        {rota === "cartoes" && (id && mes ? <TelaDaFatura key={`${id}/${mes}`} cartaoId={id} mes={mes} /> : <TelaDeCartoes />)}
        {aba && aba.id !== "hoje" && aba.id !== "mes" && aba.id !== "historico" && aba.id !== "cartoes" && <Vazia nome={aba.nome} />}
      </main>
    </div>
  );
}
