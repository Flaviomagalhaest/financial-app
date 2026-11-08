import { useEffect, useRef, useState, type ReactNode } from "react";
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
import { Icone } from "./icones";
import { ABAS, useRota, type Rota } from "./rota";

type Props = { email: string; onSair: () => void; hoje: ReactNode };

/** As telas de lançar: nelas o botão + some (ticket 204). */
const TELAS_DE_LANCAR: Rota[] = ["novo", "estornar", "credito", "favorito"];

/**
 * O círculo com a inicial abre o e-mail, Configurações, os cadastros e Sair (ticket 204). Fecha ao
 * escolher, ao tocar fora, com Esc e quando a rota muda. Fechado, os itens nem estão na página.
 */
function MenuDaConta({ email, onSair }: { email: string; onSair: () => void }) {
  const menu = useRef<HTMLDetailsElement>(null);
  const [aberto, setAberto] = useState(false);
  useEffect(() => {
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
  }, []);
  return (
    <details className="menu-da-conta" ref={menu} open={aberto} onToggle={(e) => setAberto(e.currentTarget.open)}>
      <summary aria-label={`Conta de ${email}`}>{email.charAt(0).toUpperCase()}</summary>
      {aberto && (
        <div onClick={() => setAberto(false)}>
          <p>Entrou como {email}</p>
          <a href="#/configuracoes">Configurações</a>
          <a href="#/contas-e-categorias">Contas e categorias</a>
          <a href="#/favoritos">Favoritos</a>
          <button type="button" onClick={onSair}>
            Sair
          </button>
        </div>
      )}
    </details>
  );
}

/** Casca do app: navegação por abas (embaixo no celular, ao lado na tela larga) e a tela atual. */
export function Casca({ email, onSair, hoje }: Props) {
  const { rota, id, mes, consulta } = useRota();
  // A busca é da aba Histórico (ticket 24), e a lupa a abre de qualquer aba; as edições em lote saem dela.
  const aba = rota === "busca" || rota === "edicoes-em-lote" ? "historico" : rota;

  return (
    <div className="casca">
      <header className="topo">
        <h1>Financial App</h1>
        <a className="botao-de-icone" href="#/busca" aria-label="Buscar lançamentos">
          <Icone nome="lupa" />
        </a>
        <MenuDaConta email={email} onSair={onSair} />
      </header>
      <nav className="abas" aria-label="Telas">
        {!TELAS_DE_LANCAR.includes(rota) && (
          <a className="novo" href="#/novo">
            <span>
              <Icone nome="mais" />
            </span>
            <span className="nome-da-aba">Novo lançamento</span>
          </a>
        )}
        {ABAS.map((a) => (
          <a key={a.id} href={`#/${a.id}`} aria-current={a.id === aba ? "page" : undefined}>
            <Icone nome={a.id} />
            <span className="nome-da-aba">{a.nome}</span>
          </a>
        ))}
      </nav>
      <OfertaDeFavoritar />
      <main>
        {rota === "hoje" && (
          <section className="tela-hoje">
            <h2 className="oculto">Hoje</h2>
            <TelaHoje />
            {hoje}
          </section>
        )}
        {rota === "novo" && (id ? <TelaDeLancamento key={id} id={id} /> : <NovoLancamento />)}
        {rota === "estornar" && id && <TelaDeLancamento key={id} estornoDe={id} />}
        {rota === "credito" && id && <TelaDeLancamento key={id} creditoNoCartao={id} />}
        {rota === "favorito" && id && <NovoLancamento key={id} favoritoId={id} />}
        {rota === "favoritos" && <TelaDeFavoritos />}
        {rota === "conflito" && id && <TelaDeConflito key={id} id={id} />}
        {rota === "parcelamento" && id && <TelaDoParcelamento key={id} id={id} />}
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
