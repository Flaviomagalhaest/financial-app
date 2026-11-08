import { Icone, type NomeDoIcone } from "./icones";

const CARTOES: { href: string; nome: string; icone: NomeDoIcone }[] = [
  { href: "#/historico", nome: "Histórico", icone: "historico" },
  { href: "#/futuro", nome: "Futuro", icone: "futuro" },
  { href: "#/busca", nome: "Busca", icone: "lupa" },
  { href: "#/favoritos", nome: "Favoritos", icone: "estrela" },
  { href: "#/contas-e-categorias", nome: "Contas e categorias", icone: "pastas" },
  { href: "#/configuracoes", nome: "Configurações", icone: "engrenagem" },
];

/** Tela Explorar (ticket 211): o que não cabe na barra de baixo do celular, em cartões de ícone e nome. */
export function TelaExplorar() {
  return (
    <section className="tela-explorar">
      <h2>Explorar</h2>
      <div className="cartoes-explorar">
        {CARTOES.map((c) => (
          <a key={c.href} href={c.href}>
            <Icone nome={c.icone} />
            <span>{c.nome}</span>
          </a>
        ))}
      </div>
    </section>
  );
}
