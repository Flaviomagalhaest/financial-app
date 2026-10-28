// A fila dos lançamentos não enviados: o que se faz no aparelho entra aqui e sobe em lote, na
// ordem (ADR 0011). Sem React nem cliente da API, porque o service worker também envia.
import type { components } from "../api/schema";
import {
  comTrava,
  emTransacao,
  lerFila,
  pedido,
  type Base,
  type Conflito,
  type Guardada,
  type ItemDaFila,
  type Lancamento,
  type NovoLancamento,
} from "./armazem";

export type Acao = components["schemas"]["Lote"]["acoes"][number];
export type Resultado = components["schemas"]["Resultado"];
export type Alteracao = components["schemas"]["AlteracaoDeLancamento"];
export type Campo = components["schemas"]["CampoEmConflito"]["campo"];
/** Uma ida ao servidor: os resultados, na ordem das ações, ou o status HTTP da falha (0 sem rede). */
export type Remessa = (acoes: Acao[]) => Promise<Resultado[] | number>;

/** O `sync` que a tela pede e o service worker atende (service-worker.js). */
export const ETIQUETA_DO_ENVIO = "enviar-fila";
/** A lista de lançamentos guardada, que o resultado do envio já acerta. */
export const LISTA = "/api/lancamentos";
/** O mesmo limite do servidor (`LIMITE_DO_LOTE`). */
const LIMITE_DO_LOTE = 100;
/** Os campos que o servidor versiona um a um (`CAMPOS` em `lancamentos.py`). */
export const CAMPOS: Campo[] = ["tipo", "situacao", "valor_centavos", "data", "descricao", "conta_id", "categoria_ids", "tags"];

type Proximo = Omit<ItemDaFila, "id" | "desde" | "revisao"> | null;

async function mudar(id: string, proximo: (atual: ItemDaFila | undefined) => Proximo) {
  await emTransacao("readwrite", async (fila) => {
    const atual: ItemDaFila | undefined = await pedido(fila.get(id));
    const item = proximo(atual);
    if (!item) await pedido(fila.delete(id));
    else await pedido(fila.put({ ...item, id, desde: atual?.desde ?? Date.now(), revisao: (atual?.revisao ?? 0) + 1 }));
  });
}

/** Como o servidor compara: categorias e tags sem ordem, tags sem distinguir maiúsculas. */
function comparavel(campo: Campo, valor: unknown): unknown {
  if (campo === "categoria_ids") return [...((valor as string[]) ?? [])].sort().join();
  if (campo === "tags") return ((valor as string[]) ?? []).map((t) => t.toLowerCase()).sort().join("\u0000");
  return valor ?? "";
}

/**
 * Só os campos que mudaram desde a base. A situação vai só se escolhida à mão; sem base (item de
 * uma versão anterior do app), vai tudo sobre a versão 0, e o que o outro lado mudou vira conflito.
 */
export function alteracao(lancamento: NovoLancamento, base: Base | undefined): Alteracao {
  const mudou: Record<string, unknown> = {};
  for (const campo of CAMPOS) {
    const valor = lancamento[campo];
    if (campo === "situacao" && !valor) continue;
    if (!base || comparavel(campo, valor) !== comparavel(campo, base[campo])) mudou[campo] = valor;
  }
  return { versao: base?.versao ?? 0, ...mudou };
}

export function comoNovo(l: Lancamento): NovoLancamento {
  const { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags } = l;
  return { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags };
}

/**
 * Criar (`novo`) ou editar; editar o que ainda não subiu muda o pedido de criar. Tira a recusa e o
 * conflito. `base` é a versão do servidor que a tela mostrava; a primeira mudança a guarda.
 */
export function enfileirarSalvar(lancamento: NovoLancamento, novo: boolean, base?: Base): Promise<void> {
  return mudar(lancamento.id, (atual) =>
    atual?.acao === "criar" || novo
      ? { acao: "criar", lancamento, talvezNoServidor: atual?.talvezNoServidor, base: atual?.base }
      : // Sobre um conflito, a tela já mostrava a versão do servidor.
        { acao: "editar", lancamento, base: atual?.conflito?.lancamento ?? atual?.base ?? base },
  );
}

/** Excluir o que com certeza não chegou ao servidor só o tira da fila. */
export function enfileirarExcluir(id: string, base?: Base): Promise<void> {
  return mudar(id, (atual) =>
    atual?.acao === "criar" && atual.talvezNoServidor === undefined
      ? null
      : { acao: "excluir", base: atual?.conflito?.lancamento ?? atual?.base ?? base },
  );
}

/** Desiste da mudança não enviada: o aparelho volta a mostrar o que o servidor tem. */
export function descartar(id: string): Promise<void> {
  return mudar(id, () => null);
}

/**
 * Decide o conflito: nos campos de `ficaOMeu` vale a mudança do aparelho, nos outros a do
 * servidor. O que sobra sobe sobre a versão do servidor; sem sobra, a mudança sai da fila.
 */
export function decidirConflito(id: string, ficaOMeu: Campo[]): Promise<void> {
  return mudar(id, (atual) => {
    if (!atual?.conflito || !atual.lancamento) return atual ?? null;
    const servidor = atual.conflito.lancamento;
    const { versao: _, ...minhas } = alteracao(atual.lancamento, atual.base);
    for (const { campo } of atual.conflito.campos) if (!ficaOMeu.includes(campo)) delete minhas[campo];
    const lancamento = { ...comoNovo(servidor), ...minhas } as NovoLancamento;
    // Sem a escolha à mão, a situação segue a regra do servidor, como no pedido original.
    if (!atual.lancamento.situacao) delete lancamento.situacao;
    const sobra = Object.keys(alteracao(lancamento, servidor)).length > 1;
    return sobra ? { acao: "editar", lancamento, base: servidor } : null;
  });
}

/** Excluir mesmo assim o que o outro lado mudou: a exclusão sobe sobre a versão do servidor. */
export function excluirMesmoAssim(id: string): Promise<void> {
  return mudar(id, (atual) => (atual?.conflito ? { acao: "excluir", base: atual.conflito.lancamento } : (atual ?? null)));
}

/** A exclusão venceu: a mudança vira um lançamento novo, com outra identidade. */
export function lancarDeNovo(id: string): Promise<void> {
  const novoId = crypto.randomUUID();
  return emTransacao("readwrite", async (fila) => {
    const atual: ItemDaFila | undefined = await pedido(fila.get(id));
    if (!atual?.exclusao || !atual.lancamento) return;
    await pedido(fila.delete(id));
    await pedido(fila.put({ id: novoId, acao: "criar", lancamento: { ...atual.lancamento, id: novoId }, desde: Date.now(), revisao: 1 }));
  });
}

export function ordenar(lista: Lancamento[]): Lancamento[] {
  return lista.sort((a, b) => b.data.localeCompare(a.data) || b.criado_em.localeCompare(a.criado_em));
}

/** Põe na lista guardada a versão do servidor; enquanto o conflito espera, é a que se vê. */
async function trocarNaLista(respostas: IDBObjectStore, lancamento: Lancamento) {
  const guardada: Guardada<Lancamento[]> | undefined = await pedido(respostas.get(LISTA));
  if (!guardada) return;
  const lista = guardada.dados.filter((l) => l.id !== lancamento.id);
  await pedido(respostas.put({ dados: ordenar([...lista, lancamento]), em: guardada.em }, LISTA));
}

/**
 * A confirmação feita direto na API deu conflito (ticket 43): ela entra na fila como edição
 * sobre o previsto que a tela mostrava, já em conflito, para a mesma tela de decisão.
 */
export function guardarConflito(lancamento: NovoLancamento, base: Base, conflito: Conflito): Promise<void> {
  return emTransacao("readwrite", async (fila, respostas) => {
    const atual: ItemDaFila | undefined = await pedido(fila.get(lancamento.id));
    await pedido(
      fila.put({ id: lancamento.id, acao: "editar", lancamento, base, conflito, desde: atual?.desde ?? Date.now(), revisao: (atual?.revisao ?? 0) + 1 }),
    );
    await trocarNaLista(respostas, conflito.lancamento);
  });
}

/** Recusado, em conflito ou vencido pela exclusão: não sobe até a pessoa decidir. */
export const esperaAPessoa = (item: ItemDaFila) => !!(item.recusa || item.conflito || item.exclusao);

/**
 * As ações de um item. O criar que talvez já esteja no servidor com uma versão anterior vai com
 * a edição atrás: no servidor, reenviar o criar devolve o que já está gravado.
 */
function acoesDo(item: ItemDaFila): Acao[] {
  if (item.acao === "excluir") return [{ acao: "excluir", id: item.id, versao: item.base?.versao }];
  const lancamento = item.lancamento!;
  const editar: Acao = { acao: "editar", id: item.id, alteracao: alteracao(lancamento, item.base) };
  if (item.acao === "editar") return [editar];
  const comEdicao = item.talvezNoServidor !== undefined && item.talvezNoServidor !== item.revisao;
  return comEdicao ? [{ acao: "criar", lancamento }, editar] : [{ acao: "criar", lancamento }];
}

async function aplicar(enviados: ItemDaFila[], resultados: Resultado[]) {
  await emTransacao("readwrite", async (fila, respostas) => {
    const guardada: Guardada<Lancamento[]> | undefined = await pedido(respostas.get(LISTA));
    let lista = guardada?.dados ?? [];
    for (const [i, enviado] of enviados.entries()) {
      const { resultado, motivo, lancamento, campos, exclusao } = resultados[i];
      const atual: ItemDaFila | undefined = await pedido(fila.get(enviado.id));
      const intacto = atual?.revisao === enviado.revisao;
      if (resultado === "recusada") {
        if (intacto) await pedido(fila.put({ ...atual, recusa: motivo ?? "recusado" }));
        continue;
      }
      if (resultado === "conflito") {
        // O aparelho passa a mostrar a versão do servidor enquanto a decisão espera.
        if (lancamento) lista = [...lista.filter((l) => l.id !== enviado.id), lancamento];
        if (intacto && lancamento) await pedido(fila.put({ ...atual, conflito: { motivo: motivo ?? "conflito", lancamento, campos: campos ?? [] } }));
        continue;
      }
      lista = lista.filter((l) => l.id !== enviado.id);
      if (resultado === "descartada") {
        if (atual?.lancamento && exclusao) await pedido(fila.put({ ...atual, exclusao }));
        else if (atual) await pedido(fila.delete(enviado.id));
        continue;
      }
      // Excluído no aparelho enquanto subia: agora que existe no servidor, sai de lá também.
      const excluidoNoCaminho = !atual && enviado.acao === "criar";
      if (lancamento && !excluidoNoCaminho) lista.push(lancamento);
      if (excluidoNoCaminho) await pedido(fila.put({ id: enviado.id, acao: "excluir", base: lancamento, desde: enviado.desde, revisao: 1 }));
      else if (intacto) await pedido(fila.delete(enviado.id));
      // Mudou no caminho: a mudança nova sobe sobre a versão que acabou de ser aceita (o que era
      // criar já existe lá e sobe como edição).
      else if (atual)
        await pedido(fila.put({ ...atual, acao: atual.acao === "criar" ? "editar" : atual.acao, talvezNoServidor: undefined, base: lancamento ?? atual.base }));
    }
    if (guardada) await pedido(respostas.put({ dados: ordenar(lista), em: guardada.em }, LISTA));
  });
}

/**
 * Sem resposta, o servidor pode ter gravado o criar. Guarda a primeira revisão que talvez tenha
 * chegado, e o que ela levava como base da edição seguinte: uma tentativa depois, sem rede, não
 * prova que a anterior não chegou.
 */
async function marcarSemResposta(enviados: ItemDaFila[]) {
  await emTransacao("readwrite", async (fila) => {
    for (const enviado of enviados) {
      const atual: ItemDaFila | undefined = await pedido(fila.get(enviado.id));
      if (enviado.acao === "criar" && atual?.acao === "criar" && atual.talvezNoServidor === undefined)
        await pedido(fila.put({ ...atual, talvezNoServidor: enviado.revisao, base: { ...enviado.lancamento!, versao: 1 } }));
    }
  });
}

/** Um resultado por item: o que não foi aceito, se houver, senão o da última ação dele. */
function porItem(itens: ItemDaFila[], resultados: Resultado[]): Resultado[] {
  let i = 0;
  return itens.map((item) => {
    const deste = resultados.slice(i, (i += acoesDo(item).length));
    return deste.find((r) => r.resultado !== "aceita") ?? deste[deste.length - 1];
  });
}

/** Resultados de um lote; se o servidor recusa o formato do lote inteiro, manda um a um. */
async function remeterLote(remeter: Remessa, itens: ItemDaFila[]): Promise<Resultado[] | null> {
  const acoes = itens.flatMap(acoesDo);
  const resposta = await remeter(acoes);
  if (typeof resposta !== "number") return resposta.length === acoes.length ? porItem(itens, resposta) : null;
  if (resposta !== 422) return null;
  if (itens.length === 1) return [{ resultado: "recusada", motivo: "o servidor não aceitou este lançamento" }];
  const resultados: Resultado[] = [];
  for (const item of itens) {
    const um = await remeterLote(remeter, [item]);
    if (!um) return null;
    resultados.push(...um);
  }
  return resultados;
}

/** Os primeiros itens cujas ações cabem num lote. */
function ateOLimite(itens: ItemDaFila[]): ItemDaFila[] {
  let acoes = 0;
  return itens.filter((item) => (acoes += acoesDo(item).length) <= LIMITE_DO_LOTE);
}

/**
 * Sobe a fila em lotes, na ordem. Devolve `true` quando não sobrou nada para subir (o que espera
 * a pessoa fica) e `false` quando o servidor não respondeu: a fila fica para a próxima.
 */
export function enviarFila(remeter: Remessa): Promise<boolean> {
  return comTrava("exclusive", async () => {
    for (;;) {
      const lote = ateOLimite((await lerFila()).filter((item) => !esperaAPessoa(item)));
      if (lote.length === 0) return true;
      const resultados = await remeterLote(remeter, lote).catch(() => null);
      if (!resultados) {
        await marcarSemResposta(lote);
        return false;
      }
      await aplicar(lote, resultados);
    }
  });
}
