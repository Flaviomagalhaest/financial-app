import { useEffect, useState } from "react";
import { definirModeloPadrao, useCadastro, useConexao, useModeloPadrao } from "../dados";
import { formatarCentavos } from "../lancamentos/dinheiro";

/** "1.234,56", "1234,5" ou "80" viram centavos; `null` se não é um valor maior que zero. */
export function lerReais(texto: string): number | null {
  const limpo = texto.replace(/R\$|\s/g, "");
  const numero = Number(limpo.includes(",") ? limpo.replace(/\./g, "").replace(",", ".") : limpo);
  return Number.isFinite(numero) && numero > 0 ? Math.round(numero * 100) : null;
}

type Linha = { categoria_id: string; reais: string };

export const comoReais = (centavos: number) => formatarCentavos(centavos).replace(/^R\$ /, "");

/**
 * O modelo padrão do planejamento: categoria e valor de cada item, que "Aplicar modelo padrão"
 * copia para um mês vazio. Salvar troca o modelo inteiro e precisa de internet.
 */
export function TelaDoModelo() {
  const { dados, buscar } = useModeloPadrao();
  const { categorias } = useCadastro();
  const online = useConexao();
  const [linhas, setLinhas] = useState<Linha[] | null>(null);
  const [aviso, setAviso] = useState<{ erro: boolean; texto: string } | null>(null);
  const [salvando, setSalvando] = useState(false);

  // A primeira resposta (guardada ou do servidor) preenche o formulário; depois, vale o que se editou.
  useEffect(() => {
    if (dados && linhas === null) setLinhas(dados.itens.map((i) => ({ categoria_id: i.categoria_id, reais: comoReais(i.valor_centavos) })));
  }, [dados, linhas]);

  const atuais = linhas ?? [];
  const usadas = new Set(atuais.map((l) => l.categoria_id));
  const disponiveis = categorias.filter((c) => !c.arquivada && !usadas.has(c.id));
  const mudar = (posicao: number, mudanca: Partial<Linha>) => setLinhas(atuais.map((l, i) => (i === posicao ? { ...l, ...mudanca } : l)));

  async function salvar() {
    const itens = atuais.map((l) => ({ categoria_id: l.categoria_id, valor_centavos: lerReais(l.reais) }));
    if (itens.some((i) => i.valor_centavos === null)) {
      setAviso({ erro: true, texto: "Cada item precisa de um valor maior que zero." });
      return;
    }
    setSalvando(true);
    const recusa = await definirModeloPadrao(itens as { categoria_id: string; valor_centavos: number }[]);
    setSalvando(false);
    setAviso(recusa ? { erro: true, texto: `Não deu: ${recusa}.` } : { erro: false, texto: "Modelo padrão salvo." });
    if (!recusa) void buscar();
  }

  return (
    <section className="modelo-do-planejamento">
      <a href="#/mes">Voltar ao mês</a>
      <h2>Modelo padrão do planejamento</h2>
      <p className="vazio">Os itens que "Aplicar modelo padrão" cria num mês sem planejamento.</p>
      {!online && <p className="vazio">Sem internet: o modelo padrão só se salva com conexão.</p>}
      {atuais.length === 0 && <p className="vazio">O modelo padrão ainda não tem itens.</p>}
      <ul className="lista">
        {atuais.map((l, posicao) => {
          const categoria = categorias.find((c) => c.id === l.categoria_id);
          return (
            <li key={l.categoria_id}>
              <label htmlFor={`modelo-${l.categoria_id}`}>{categoria?.nome ?? "?"}</label>
              <div className="linha">
                <input id={`modelo-${l.categoria_id}`} inputMode="decimal" autoComplete="off" placeholder="0,00" value={l.reais} onChange={(e) => mudar(posicao, { reais: e.target.value })} />
                <button className="secundario" onClick={() => setLinhas(atuais.filter((_, i) => i !== posicao))} aria-label={`Tirar ${categoria?.nome ?? "item"} do modelo padrão`}>
                  Tirar
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {disponiveis.length > 0 && (
        <label>
          Adicionar item
          <select value="" onChange={(e) => e.target.value && setLinhas([...atuais, { categoria_id: e.target.value, reais: "" }])}>
            <option value="">Escolha a categoria</option>
            {disponiveis.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
      )}
      <button disabled={!online || salvando || linhas === null} onClick={() => void salvar()}>
        Salvar modelo padrão
      </button>
      {aviso && (
        <p role={aviso.erro ? "alert" : "status"} className={aviso.erro ? "erro" : undefined}>
          {aviso.texto}
        </p>
      )}
    </section>
  );
}
