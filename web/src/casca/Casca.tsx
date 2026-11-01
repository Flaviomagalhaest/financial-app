import type { ReactNode } from "react";
import { Configuracoes } from "../configuracoes/Configuracoes";
import { TelaDeFavoritos } from "../configuracoes/TelaDeFavoritos";
import { OfertaDeFavoritar } from "../lancamentos/OfertaDeFavoritar";
import { TelaHoje } from "../hoje/TelaHoje";
import { ListaDeLancamentos } from "../lancamentos/ListaDeLancamentos";
import { NovoLancamento } from "../lancamentos/NovoLancamento";
import { TelaDeContasECategorias } from "../contas-e-categorias/TelaDeContasECategorias";
import { TelaDeConflito } from "../lancamentos/TelaDeConflito";
import { TelaDeLancamento } from "../lancamentos/TelaDeLancamento";
import { TelaDoParcelamento } from "../lancamentos/TelaDoParcelamento";
import { TelaDaRecorrencia } from "../lancamentos/TelaDaRecorrencia";
import { TelaDeCartoes } from "../cartoes/TelaDeCartoes";
import { TelaDaFatura } from "../cartoes/TelaDaFatura";
import { TelaDaEvolucao } from "../historico/TelaDaEvolucao";
import { TelaDoFuturo } from "../futuro/TelaDoFuturo";
import { TelaDoMes } from "../mes/TelaDoMes";
import { TelaDoModelo } from "../mes/TelaDoModelo";
import { TelaDaBusca } from "../busca/TelaDaBusca";
import { TelaDasEdicoesEmLote } from "../busca/TelaDasEdicoesEmLote";
import { ABAS, useRota } from "./rota";

type Props = { email: string; onSair: () => void; hoje: ReactNode };

/** Casca do app: navegação por abas (embaixo no celular, ao lado na tela larga) e a tela atual. */
export function Casca({ email, onSair, hoje }: Props) {
  const { rota, id, mes, consulta, parcela } = useRota();
  // A busca é da aba Histórico (ticket 24), e a lupa a abre de qualquer aba; as edições em lote saem dela.
  const aba = rota === "busca" || rota === "edicoes-em-lote" ? "historico" : rota;

  return (
    <div className="casca">
      <header className="topo">
        <h1>Financial App</h1>
        <p>Entrou como {email}</p>
        <a className="lupa" href="#/busca" aria-label="Buscar lançamentos">
          🔍
        </a>
        <a href="#/configuracoes">Configurações</a>
        <button className="secundario" onClick={onSair}>
          Sair
        </button>
      </header>
      <nav className="abas" aria-label="Telas">
        {ABAS.map((a) => (
          <a key={a.id} href={`#/${a.id}`} aria-current={a.id === aba ? "page" : undefined}>
            {a.nome}
          </a>
        ))}
      </nav>
      <OfertaDeFavoritar />
      <main>
        {rota === "hoje" && (
          <section>
            <h2>Hoje</h2>
            <a className="botao" href="#/novo">
              + Novo lançamento
            </a>
            <TelaHoje />
            {hoje}
            <a href="#/contas-e-categorias">Contas e categorias</a>
          </section>
        )}
        {rota === "novo" && (id ? <TelaDeLancamento key={id} id={id} /> : <NovoLancamento />)}
        {rota === "estornar" && id && <TelaDeLancamento key={id} estornoDe={id} />}
        {rota === "favorito" && id && <NovoLancamento key={id} favoritoId={id} />}
        {rota === "favoritos" && <TelaDeFavoritos />}
        {rota === "conflito" && id && <TelaDeConflito key={id} id={id} />}
        {rota === "parcelamento" && id && <TelaDoParcelamento key={`${id}/${parcela ?? ""}`} id={id} parcela={parcela} />}
        {rota === "recorrencia" && id && <TelaDaRecorrencia key={id} id={id} />}
        {rota === "contas-e-categorias" && <TelaDeContasECategorias />}
        {rota === "configuracoes" && <Configuracoes />}
        {rota === "historico" && <ListaDeLancamentos topo={<TelaDaEvolucao />} />}
        {rota === "busca" && <TelaDaBusca key={consulta} consulta={consulta ?? ""} />}
        {rota === "edicoes-em-lote" && <TelaDasEdicoesEmLote />}
        {rota === "mes" && <TelaDoMes key={mes ?? "atual"} mes={mes} />}
        {rota === "modelo-do-planejamento" && <TelaDoModelo />}
        {rota === "cartoes" && (id && mes ? <TelaDaFatura key={`${id}/${mes}`} cartaoId={id} mes={mes} /> : <TelaDeCartoes />)}
        {rota === "futuro" && <TelaDoFuturo />}
      </main>
    </div>
  );
}
