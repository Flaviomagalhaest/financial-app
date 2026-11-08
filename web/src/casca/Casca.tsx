import { useEffect, useState, type ReactNode } from "react";
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
import { MenuDeAcoes } from "./MenuDeAcoes";
import { TelaExplorar } from "./TelaExplorar";
import { ABAS, useRota, type Rota } from "./rota";

type Props = { email: string; onSair: () => void; hoje: ReactNode };

/** As telas de lançar: nelas o botão + some (ticket 204). */
const TELAS_DE_LANCAR: Rota[] = ["novo", "estornar", "credito", "favorito"];

const SEM_MARCA_NA_LARGA: Rota[] = ["explorar", "favoritos", "contas-e-categorias", "configuracoes", "conflito", "parcelamento", "recorrencia", ...TELAS_DE_LANCAR];

/** Tela larga (barra lateral, com nomes) a partir de 900 px; abaixo disso, a barra de baixo só com ícones. */
function useTelaLarga(): boolean {
  const consulta = "(min-width: 900px)";
  const [larga, setLarga] = useState(() => window.matchMedia(consulta).matches);
  useEffect(() => {
    const lista = window.matchMedia(consulta);
    const aoMudar = () => setLarga(lista.matches);
    aoMudar();
    lista.addEventListener("change", aoMudar);
    return () => lista.removeEventListener("change", aoMudar);
  }, []);
  return larga;
}

/** O círculo com a inicial abre o e-mail, Configurações, os cadastros e Sair (ticket 204). */
function MenuDaConta({ email, onSair }: { email: string; onSair: () => void }) {
  return (
    <MenuDeAcoes classe="menu-da-conta" rotulo={`Conta de ${email}`} botao={email.charAt(0).toUpperCase()} nomeDosItens="Menu da conta">
      <p>Entrou como {email}</p>
      <a href="#/configuracoes">Configurações</a>
      <a href="#/contas-e-categorias">Contas e categorias</a>
      <a href="#/favoritos">Favoritos</a>
      <button type="button" onClick={onSair}>
        Sair
      </button>
    </MenuDeAcoes>
  );
}

/** Casca do app: navegação por abas (embaixo no celular, ao lado na tela larga) e a tela atual. */
export function Casca({ email, onSair, hoje }: Props) {
  const { rota, id, mes, consulta } = useRota();
  const larga = useTelaLarga();
  // Tela larga: a busca e as edições em lote marcam Histórico (ticket 24), o modelo do planejamento marca Mês, e as
  // telas do Menu da conta e Explorar não marcam nada. Celular (ticket 211): marcam Hoje, Mês e Cartões; as telas de
  // lançar, o parcelamento, a recorrência e o conflito não marcam; toda outra tela marca a grade (Explorar).
  const marcada: string | undefined = larga
    ? rota === "busca" || rota === "edicoes-em-lote"
      ? "historico"
      : rota === "modelo-do-planejamento"
        ? "mes"
        : SEM_MARCA_NA_LARGA.includes(rota)
          ? undefined
          : rota
    : ["hoje", "mes", "cartoes"].includes(rota)
      ? rota
      : rota === "modelo-do-planejamento"
        ? "mes"
        : [...TELAS_DE_LANCAR, "conflito", "parcelamento", "recorrencia"].includes(rota)
          ? undefined
          : "explorar";
  const abas = larga ? ABAS : ABAS.filter((a) => a.id !== "historico" && a.id !== "futuro");

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
        {abas.map((a) => (
          <a key={a.id} href={`#/${a.id}`} aria-label={a.nome} aria-current={a.id === marcada ? "page" : undefined}>
            <Icone nome={a.id} />
            <span className="nome-da-aba">{a.nome}</span>
          </a>
        ))}
        {!larga && (
          <a href="#/explorar" aria-label="Explorar" aria-current={marcada === "explorar" ? "page" : undefined}>
            <Icone nome="grade" />
          </a>
        )}
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
        {rota === "explorar" && <TelaExplorar />}
      </main>
    </div>
  );
}
