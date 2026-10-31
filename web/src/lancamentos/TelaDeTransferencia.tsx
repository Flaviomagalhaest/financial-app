import { useState } from "react";
import { criarTransferencia, useAvisoDePlanejamento, useCadastro, useConexao } from "../dados";
import { nomePorId } from "./apresentacao";
import { AvisoDePlanejamento } from "./AvisoDePlanejamento";
import { hoje } from "./datas";
import { formatarCentavos } from "./dinheiro";
import { EscolhaDaData } from "./EscolhaDaData";
import { EscolhaDoTipo, type TipoDaEntrada } from "./EscolhaDoTipo";
import { Teclado } from "./Teclado";

type Ficha = { id: string; nome: string };

/** Fileira de toque de uma escolha só; `nome` vira o nome do grupo para o leitor de tela. */
function Fileira({ nome, opcoes, marcada, onMarcar }: { nome: string; opcoes: Ficha[]; marcada: string | null; onMarcar: (id: string) => void }) {
  return (
    <>
      <h3>{nome}</h3>
      <div className="fileira rolavel" role="group" aria-label={nome}>
        {opcoes.map((o) => (
          <button type="button" key={o.id} className={`ficha${o.id === marcada ? " marcada" : ""}`} aria-pressed={o.id === marcada} onClick={() => onMarcar(o.id)}>
            {o.nome}
          </button>
        ))}
      </div>
    </>
  );
}

/** Nova transferência entre duas contas do casal (ADR 0014). Precisa de internet (ADR 0011). */
type Props = {
  centavosIniciais: number;
  /** A troca para despesa ou receita, levando o valor digitado. */
  onTipo: (tipo: TipoDaEntrada, centavos: number) => void;
};

export function TelaDeTransferencia({ centavosIniciais, onTipo }: Props) {
  const { contas, categorias } = useCadastro();
  const online = useConexao();
  // A identidade nasce no aparelho: tentar de novo depois de uma falha não duplica.
  const [id] = useState(() => crypto.randomUUID());
  const [centavos, setCentavos] = useState(centavosIniciais);
  const [origem, setOrigem] = useState<string | null>(null);
  const [destino, setDestino] = useState<string | null>(null);
  const [categoria, setCategoria] = useState<string | null>(null);
  const [descricao, setDescricao] = useState("");
  const [data, setData] = useState(hoje);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  const categoriasDeTransferencia = categorias.filter((c) => c.tipo === "transferencia" && !c.arquivada);
  // A transferência com categoria conta no item dela (história 67); a futura nasce prevista.
  const planejamento = useAvisoDePlanejamento(
    { id, valor_centavos: centavos, categoria_ids: categoria ? [categoria] : [], conta_id: origem ?? "", data, fatura_mes: null, situacao: data > hoje() ? "previsto" : "realizado" },
    null,
  );
  const podeSalvar = online && centavos > 0 && !!origem && !!destino && origem !== destino && !enviando;

  function marcarOrigem(conta: string) {
    setOrigem(conta);
    if (destino === conta) setDestino(null);
  }

  async function salvar() {
    if (!origem || !destino) return;
    setErro("");
    setEnviando(true);
    const recusa = await criarTransferencia({
      id,
      conta_origem_id: origem,
      conta_destino_id: destino,
      valor_centavos: centavos,
      data,
      descricao,
      categoria_id: categoria,
    });
    setEnviando(false);
    if (recusa) setErro(`Não foi possível salvar a transferência: ${recusa}.`);
    else window.location.hash = "#/hoje";
  }

  return (
    <section className="lancamento">
      <h2>Nova transferência</h2>
      <EscolhaDoTipo tipo="transferencia" comTransferencia onMudar={(t) => onTipo(t, centavos)} />
      <p className="valor" data-testid="valor" aria-live="polite">
        {formatarCentavos(centavos)}
      </p>
      {!online && <p className="aviso">Sem internet: a transferência precisa de internet.</p>}
      <Fileira nome="De" opcoes={contas} marcada={origem} onMarcar={marcarOrigem} />
      <Fileira nome="Para" opcoes={contas.filter((c) => c.id !== origem)} marcada={destino} onMarcar={setDestino} />
      {categoriasDeTransferencia.length > 0 && (
        <Fileira
          nome="Categoria (opcional)"
          opcoes={categoriasDeTransferencia}
          marcada={categoria}
          onMarcar={(c) => setCategoria(categoria === c ? null : c)}
        />
      )}
      {/* Uma categoria só: nunca há item a escolher, então `onEscolher` não tem o que fazer. */}
      {categoria && <AvisoDePlanejamento {...planejamento} tipo="transferencia" nomeDaCategoria={(c) => nomePorId(categorias, c)} onEscolher={() => {}} />}
      <label htmlFor="descricao">Descrição</label>
      <input id="descricao" value={descricao} onChange={(e) => setDescricao(e.target.value)} autoComplete="off" />
      <h3>Data</h3>
      <EscolhaDaData data={data} onMudar={setData} />
      {data > hoje() && <p className="vazio">Data futura: a transferência nasce prevista.</p>}
      <Teclado centavos={centavos} onMudar={setCentavos} />
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <button type="button" disabled={!podeSalvar} onClick={() => void salvar()}>
        Salvar
      </button>
      <a href="#/hoje">Cancelar</a>
    </section>
  );
}
