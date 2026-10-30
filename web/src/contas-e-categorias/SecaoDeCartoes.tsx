import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/cliente";
import { useCartoesComArquivados, useFaturas, type Cartao } from "../dados";
import { mesPorExtenso } from "../cartoes/apresentacao";
import { emCentavos, formatarCentavos } from "../lancamentos/dinheiro";

type Executar = (acao: string, chamar: () => Promise<{ data?: unknown; response: Response; error?: unknown }>) => Promise<boolean>;

/** Os cartões da configuração: titulares com dias e limite, adicionais ligados a um titular. Tudo exige internet. */
export function SecaoDeCartoes({ executar, setErro }: { executar: Executar; setErro: (erro: string) => void }) {
  const { cartoes, recarregar } = useCartoesComArquivados();
  const titulares = cartoes.filter((c) => !c.titular_id && !c.arquivado);
  const nomeDe = (id: string | null | undefined) => cartoes.find((c) => c.id === id)?.nome ?? "";
  const [titularId, setTitularId] = useState("");

  async function salvar(cartao: Cartao, mudanca: Partial<Cartao>): Promise<boolean> {
    const atual = { ...cartao, ...mudanca };
    const ok = await executar("alterar o cartão", () =>
      api.PUT("/api/cartoes/{id}", {
        params: { path: { id: cartao.id } },
        body: {
          nome: atual.nome,
          titular_id: atual.titular_id ?? null,
          dia_fechamento: atual.dia_fechamento ?? null,
          dia_vencimento: atual.dia_vencimento ?? null,
          limite_centavos: atual.limite_centavos ?? null,
          mes_anterior_ao_fechamento: atual.mes_anterior_ao_fechamento,
          arquivado: atual.arquivado,
        },
      }),
    );
    if (ok) await recarregar();
    return ok;
  }

  async function criar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const dados = new FormData(form);
    const adicional = titularId !== "";
    const limite = adicional ? null : emCentavos(String(dados.get("limite") ?? ""));
    if (limite === undefined) return setErro("Informe o limite em reais (ex.: 5000,00).");
    const dia = (campo: string) => (adicional || dados.get(campo) === "" ? null : Number(dados.get(campo)));
    const ok = await executar("cadastrar o cartão", () =>
      api.POST("/api/cartoes", {
        body: {
          nome: String(dados.get("nome")).trim(),
          titular_id: adicional ? titularId : null,
          dia_fechamento: dia("dia_fechamento"),
          dia_vencimento: dia("dia_vencimento"),
          limite_centavos: limite,
          mes_anterior_ao_fechamento: !adicional && dados.get("mes_anterior") === "on",
        },
      }),
    );
    if (!ok) return;
    form.reset();
    setTitularId("");
    await recarregar();
  }

  return (
    <section aria-labelledby="titulo-cartoes">
      <h3 id="titulo-cartoes">Cartões</h3>
      <ul className="lista">
        {cartoes.map((c) => (
          <LinhaDeCartao key={c.id} cartao={c} titular={nomeDe(c.titular_id)} aoSalvar={salvar} />
        ))}
      </ul>
      <form aria-label="Novo cartão" onSubmit={(e) => void criar(e)}>
        <label htmlFor="cartao-nome">Nome</label>
        <input id="cartao-nome" name="nome" required pattern=".*\S.*" />
        <label htmlFor="cartao-titular">Titular</label>
        <select id="cartao-titular" value={titularId} onChange={(e) => setTitularId(e.target.value)}>
          <option value="">Nenhum (cartão titular)</option>
          {titulares.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nome}
            </option>
          ))}
        </select>
        {!titularId && (
          <>
            <label htmlFor="cartao-fechamento">Dia de fechamento</label>
            <input id="cartao-fechamento" name="dia_fechamento" type="number" min={1} max={31} inputMode="numeric" />
            <label htmlFor="cartao-vencimento">Dia de vencimento</label>
            <input id="cartao-vencimento" name="dia_vencimento" type="number" min={1} max={31} inputMode="numeric" />
            <label htmlFor="cartao-limite">Limite (opcional)</label>
            <input id="cartao-limite" name="limite" inputMode="decimal" placeholder="0,00" />
            <label>
              <input type="checkbox" name="mes_anterior" /> Conta no mês anterior ao fechamento
            </label>
          </>
        )}
        <button type="submit">Cadastrar cartão</button>
      </form>
    </section>
  );
}

function resumoDoTitular(c: Cartao): string {
  const partes = [
    c.dia_fechamento ? `fecha dia ${c.dia_fechamento}` : "",
    c.dia_vencimento ? `vence dia ${c.dia_vencimento}` : "",
    c.limite_centavos != null ? `limite ${formatarCentavos(c.limite_centavos)}` : "",
  ].filter(Boolean);
  return partes.join(" · ");
}

const AVISO_DO_DIA_PADRAO =
  "Mudar o dia padrão vale só para as faturas abertas e futuras: só as faturas abertas e futuras mudam, e as compras delas vão para a fatura certa. As fechadas e pagas ficam como estão.";

function LinhaDeCartao({
  cartao,
  titular,
  aoSalvar,
}: {
  cartao: Cartao;
  titular: string;
  aoSalvar: (cartao: Cartao, mudanca: Partial<Cartao>) => Promise<boolean>;
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(cartao.nome);
  const [fechamento, setFechamento] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [limite, setLimite] = useState("");
  const [mesAnterior, setMesAnterior] = useState(cartao.mes_anterior_ao_fechamento);
  const [acertando, setAcertando] = useState(false);
  const adicional = !!cartao.titular_id;

  if (acertando) {
    return (
      <li>
        <FormularioDeFatura cartao={cartao} aoFechar={() => setAcertando(false)} />
      </li>
    );
  }
  if (editando) {
    const dia = (texto: string) => (texto === "" ? null : Number(texto));
    return (
      <li>
        <form
          aria-label={`Editar cartão ${cartao.nome}`}
          onSubmit={(e) => {
            e.preventDefault();
            const centavos = adicional ? null : emCentavos(limite);
            if (centavos === undefined) return;
            const mudanca: Partial<Cartao> = { nome: nome.trim() };
            if (!adicional) {
              Object.assign(mudanca, {
                dia_fechamento: dia(fechamento),
                dia_vencimento: dia(vencimento),
                limite_centavos: centavos,
                mes_anterior_ao_fechamento: mesAnterior,
              });
            }
            void aoSalvar(cartao, mudanca).then((ok) => ok && setEditando(false));
          }}
        >
          <label htmlFor={`nome-cartao-${cartao.id}`}>Novo nome de {cartao.nome}</label>
          <input id={`nome-cartao-${cartao.id}`} value={nome} onChange={(e) => setNome(e.target.value)} pattern=".*\S.*" required />
          {!adicional && (
            <>
              <label htmlFor={`fechamento-cartao-${cartao.id}`}>Dia de fechamento de {cartao.nome}</label>
              <input id={`fechamento-cartao-${cartao.id}`} type="number" min={1} max={31} value={fechamento} onChange={(e) => setFechamento(e.target.value)} />
              <label htmlFor={`vencimento-cartao-${cartao.id}`}>Dia de vencimento de {cartao.nome}</label>
              <input id={`vencimento-cartao-${cartao.id}`} type="number" min={1} max={31} value={vencimento} onChange={(e) => setVencimento(e.target.value)} />
              <label htmlFor={`limite-cartao-${cartao.id}`}>Limite de {cartao.nome}</label>
              <input id={`limite-cartao-${cartao.id}`} value={limite} onChange={(e) => setLimite(e.target.value)} inputMode="decimal" placeholder="0,00" />
              <label>
                <input type="checkbox" checked={mesAnterior} onChange={(e) => setMesAnterior(e.target.checked)} /> Conta no mês anterior ao fechamento
              </label>
              <p className="aviso">{AVISO_DO_DIA_PADRAO}</p>
            </>
          )}
          <button type="submit">Salvar cartão</button>
          <button type="button" className="secundario" onClick={() => setEditando(false)}>
            Cancelar
          </button>
        </form>
      </li>
    );
  }
  return (
    <li className={cartao.arquivado ? "arquivada" : undefined}>
      <div>
        <span>
          {cartao.nome}
          {cartao.arquivado && " (arquivado)"}
        </span>
        <span>{adicional ? `adicional de ${titular}` : resumoDoTitular(cartao)}</span>
      </div>
      <div className="acoes">
        <button
          type="button"
          className="secundario"
          onClick={() => {
            setNome(cartao.nome);
            setFechamento(cartao.dia_fechamento == null ? "" : String(cartao.dia_fechamento));
            setVencimento(cartao.dia_vencimento == null ? "" : String(cartao.dia_vencimento));
            setLimite(cartao.limite_centavos == null ? "" : String(cartao.limite_centavos / 100).replace(".", ","));
            setMesAnterior(cartao.mes_anterior_ao_fechamento);
            setEditando(true);
          }}
        >
          Editar cartão {cartao.nome}
        </button>
        {!adicional && !cartao.arquivado && (
          <button type="button" className="secundario" onClick={() => setAcertando(true)}>
            Acertar fatura de {cartao.nome}
          </button>
        )}
        <button type="button" className="secundario" onClick={() => void aoSalvar(cartao, { arquivado: !cartao.arquivado })}>
          {cartao.arquivado ? "Desarquivar" : "Arquivar"} cartão {cartao.nome}
        </button>
      </div>
    </li>
  );
}

const AVISO_DA_FATURA =
  "Acertar o fechamento ou o vencimento de uma fatura muda a fatura em que cada compra cai: as compras delas se redistribuem entre a fatura acertada e as abertas e futuras.";

/** Acerta as datas de uma fatura que já nasceu ou, por "outro mês", de uma que ainda vai nascer. */
function FormularioDeFatura({ cartao, aoFechar }: { cartao: Cartao; aoFechar: () => void }) {
  const { dados: faturas, buscar } = useFaturas(cartao.id);
  const [escolha, setEscolha] = useState("");
  const [outroMes, setOutroMes] = useState("");
  const [fechamento, setFechamento] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [erro, setErro] = useState("");
  const existentes = faturas ?? [];
  const atual = existentes.find((f) => f.situacao === "aberta") ?? existentes[existentes.length - 1];
  const mes = escolha === "outro" ? (outroMes ? `${outroMes}-01` : "") : escolha || atual?.mes || "";

  function escolher(valor: string) {
    setEscolha(valor);
    const fatura = existentes.find((f) => f.mes === valor);
    setFechamento(fatura?.fechamento ?? "");
    setVencimento(fatura?.vencimento ?? "");
  }

  // Abre já na fatura atual, com as datas dela.
  const mesAtual = atual?.mes;
  useEffect(() => {
    // Só se a pessoa ainda não escolheu: a lista pode chegar depois do primeiro toque.
    if (mesAtual && escolha === "") escolher(mesAtual);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mesAtual]);

  async function salvar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErro("");
    try {
      const { response, error } = await api.PATCH("/api/cartoes/{id}/faturas/{mes}", {
        params: { path: { id: cartao.id, mes } },
        body: { fechamento: fechamento || null, vencimento: vencimento || null },
      });
      if (!response.ok) {
        const motivo = (error as { detail?: unknown } | undefined)?.detail;
        return setErro(`Não foi possível acertar a fatura${typeof motivo === "string" ? `: ${motivo}` : ""}.`);
      }
      await buscar();
      aoFechar();
    } catch {
      setErro("Sem internet: a alteração precisa de internet.");
    }
  }

  return (
    <form aria-label={`Acertar fatura de ${cartao.nome}`} onSubmit={(e) => void salvar(e)}>
      <label htmlFor={`fatura-${cartao.id}`}>Fatura</label>
      <select id={`fatura-${cartao.id}`} value={escolha} onChange={(e) => escolher(e.target.value)}>
        {existentes.map((f) => (
          <option key={f.mes} value={f.mes}>
            {mesPorExtenso(f.mes)}
          </option>
        ))}
        <option value="outro">Outro mês…</option>
      </select>
      {escolha === "outro" && (
        <>
          <label htmlFor={`mes-fatura-${cartao.id}`}>Mês da fatura</label>
          <input id={`mes-fatura-${cartao.id}`} type="month" value={outroMes} onChange={(e) => setOutroMes(e.target.value)} required />
        </>
      )}
      <label htmlFor={`fechamento-fatura-${cartao.id}`}>Fechamento</label>
      <input id={`fechamento-fatura-${cartao.id}`} type="date" value={fechamento} onChange={(e) => setFechamento(e.target.value)} />
      <label htmlFor={`vencimento-fatura-${cartao.id}`}>Vencimento</label>
      <input id={`vencimento-fatura-${cartao.id}`} type="date" value={vencimento} onChange={(e) => setVencimento(e.target.value)} />
      <p className="aviso">{AVISO_DA_FATURA}</p>
      {erro && (
        <p role="alert" className="erro">
          {erro}
        </p>
      )}
      <button type="submit" disabled={!mes}>
        Salvar fatura
      </button>
      <button type="button" className="secundario" onClick={aoFechar}>
        Cancelar
      </button>
    </form>
  );
}
