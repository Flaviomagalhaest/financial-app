// A fila dos lançamentos, das recorrências e dos parcelamentos não enviados: o que se faz no
// aparelho entra aqui e sobe em lote, na ordem (ADR 0011). Sem React nem cliente da API, porque o
// service worker também envia.
import type { components } from "../api/schema";
import { config } from "../config";
import { hoje } from "../lancamentos/datas";
import {
  comTrava,
  deLancamento,
  emTransacao,
  lerFila,
  pedido,
  type Base,
  type Guardada,
  type ItemDaFila,
  type ItemDeLancamento,
  type Lancamento,
  type NovaRecorrencia,
  type NovoLancamento,
  type NovoParcelamento,
} from "./armazem";

export type Acao = components["schemas"]["Lote"]["acoes"][number];
type LeituraDaHoje = components["schemas"]["Hoje"];
export type Resultado = components["schemas"]["Resultado"];
export type Alteracao = components["schemas"]["AlteracaoDeLancamento"];
export type Campo = components["schemas"]["CampoEmConflito"]["campo"];
/** Uma ida ao servidor: os resultados, na ordem das ações, ou o status HTTP da falha (0 sem rede). */
export type Remessa = (acoes: Acao[]) => Promise<Resultado[] | number>;

/** O `sync` que a tela pede e o service worker atende (service-worker.js). */
export const ETIQUETA_DO_ENVIO = "enviar-fila";
/** A lista de lançamentos guardada, que o resultado do envio já acerta. */
export const LISTA = "/api/lancamentos";
/** A leitura da Hoje guardada: o resultado do envio acerta as contas da semana dela. */
export const HOJE = "/api/hoje";
/**
 * Nas respostas guardadas, o último lançamento aceito de cada mudança que saiu da fila: a tela que
 * abriu a mudança ainda "não enviada" edita sobre a versão que ela gerou (ticket 113).
 */
const ACEITOS = "fila/aceitos";
/** Quantos aceitos ficam guardados; os mais antigos saem. */
const MAXIMO_DE_ACEITOS = 100;
type Aceitos = Record<string, { base: Base; em: number }>;
/** O mesmo limite do servidor (`LIMITE_DO_LOTE`). */
const LIMITE_DO_LOTE = 100;
/**
 * As parcelas que os parcelamentos de um lote geram, juntas: o servidor gera todas antes de
 * responder, e um lote cheio de parcelamentos longos passaria do tempo limite da Lambda (29 s).
 * Um parcelamento do tamanho máximo vai sozinho; se mesmo assim faltar tempo, o reenvio continua
 * a geração de onde parou.
 */
const PARCELAS_POR_LOTE = config.maximoDeParcelas;
/** Os campos que o servidor versiona um a um (`CAMPOS` em `lancamentos.py`). */
export const CAMPOS: Campo[] = ["tipo", "situacao", "valor_centavos", "data", "descricao", "conta_id", "categoria_ids", "tags", "pessoa", "fatura_mes", "item_categoria_id"];

/** O pedido sem o que a fila controla; um `Omit` por tipo, para a união continuar pela `acao`. */
type SemControle<I> = I extends ItemDaFila ? Omit<I, "id" | "desde" | "revisao"> : never;
type Proximo = SemControle<ItemDaFila> | null;

/**
 * `proximo` recebe a mudança de lançamento que já está na fila (a regra não se edita) e, para a
 * tela que não tinha a versão do servidor, a do último aceito deste lançamento.
 */
async function mudar(id: string, proximo: (atual: ItemDeLancamento | undefined, aceito: Base | undefined) => Proximo) {
  await emTransacao("readwrite", async (fila, respostas) => {
    const atual: ItemDaFila | undefined = await pedido(fila.get(id));
    const aceitos: Aceitos | undefined = await pedido(respostas.get(ACEITOS));
    const item = proximo(atual && deLancamento(atual) ? atual : undefined, aceitos?.[id]?.base);
    if (!item) await pedido(fila.delete(id));
    else await pedido(fila.put({ ...item, id, desde: atual?.desde ?? Date.now(), feitoEm: Date.now(), revisao: (atual?.revisao ?? 0) + 1 }));
  });
}

/** Como o servidor compara (`_iguais`): categorias e tags sem ordem, tags sem distinguir
 * maiúsculas (o `toLowerCase` faz aqui o papel do `casefold`). */
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
    // Sem fatura, o servidor escolhe; mandar a fatura é trocá-la à mão. Sem escolha de item, a
    // que o servidor tem fica (ela sai com a categoria dela).
    if ((campo === "situacao" || campo === "fatura_mes" || campo === "item_categoria_id") && !valor) continue;
    // O servidor lê `pessoa` ausente como "fica" e vazia como "do conjunto".
    if (!base || comparavel(campo, valor) !== comparavel(campo, base[campo])) mudou[campo] = campo === "pessoa" ? (valor ?? "") : valor;
  }
  return { versao: base?.versao ?? 0, ...mudou };
}

export function comoNovo(l: NovoLancamento): NovoLancamento {
  const { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags, pessoa } = l;
  return { id, tipo, valor_centavos, data, descricao, conta_id, categoria_ids, situacao, tags, pessoa };
}

/** O pedido de criar ou de editar que fica na fila no lugar de `atual`. */
function pedidoDeSalvar(atual: ItemDeLancamento | undefined, mudado: NovoLancamento, novo: boolean, base?: Base): Proximo {
  // A situação escolhida antes (à mão ou ao confirmar) fica enquanto a data não muda, como a tela a mostra.
  const antes = atual?.conflito ? undefined : atual?.lancamento;
  const ficaASituacao = !mudado.situacao && antes?.situacao && antes.data === mudado.data;
  const lancamento = ficaASituacao ? { ...mudado, situacao: antes.situacao } : mudado;
  return atual?.acao === "criar" || novo
    ? { acao: "criar", lancamento, talvezNoServidor: atual?.talvezNoServidor, base: atual?.base }
    : // Sobre um conflito, a tela já mostrava a versão do servidor.
      { acao: "editar", lancamento, base: atual?.conflito?.lancamento ?? atual?.base ?? base };
}

/**
 * Criar (`novo`) ou editar; editar o que ainda não subiu muda o pedido de criar. Tira a recusa e o
 * conflito. `base` é a versão do servidor que a tela mostrava; a primeira mudança a guarda. Sem
 * ela (a tela mostrava a mudança não enviada, que subiu depois), vale a versão que a mudança gerou.
 */
export function enfileirarSalvar(lancamento: NovoLancamento, novo: boolean, base?: Base): Promise<void> {
  return mudar(lancamento.id, (atual, aceito) => pedidoDeSalvar(atual, lancamento, novo, base ?? aceito));
}

const AJUSTAVEIS = ["valor_centavos", "data", "conta_id"] as const;
/** O que a pessoa acertou ao confirmar o previsto; o que falta fica como estava. */
export type Ajustes = Partial<Pick<NovoLancamento, (typeof AJUSTAVEIS)[number]>>;

/**
 * Confirmar o previsto que a tela mostrava. Sobre uma mudança que ainda não subiu, muda o pedido
 * que já está lá (o criar sobe realizado, a edição leva a situação); senão, sobe como confirmação
 * sobre a versão `base`.
 */
export function enfileirarConfirmar(mostrado: NovoLancamento, ajustes: Ajustes, base?: Base): Promise<void> {
  return mudar(mostrado.id, (atual, aceito) => {
    base ??= aceito;
    const antes = atual?.lancamento && !atual.conflito ? atual.lancamento : comoNovo(mostrado);
    const lancamento: NovoLancamento = { ...antes, ...ajustes, situacao: "realizado" };
    return !atual || (atual.acao === "confirmar" && !atual.conflito)
      ? { acao: "confirmar", lancamento, base: atual?.base ?? base }
      : pedidoDeSalvar(atual, lancamento, false, base);
  });
}

/** A recorrência sobe como um pedido só; os previstos o servidor gera ao receber. */
export function enfileirarRecorrencia(recorrencia: NovaRecorrencia): Promise<void> {
  return mudar(recorrencia.id, () => ({ acao: "criar_recorrencia", recorrencia }));
}

/** O parcelamento sobe como um pedido só; as parcelas o servidor gera ao receber. */
export function enfileirarParcelamento(parcelamento: NovoParcelamento): Promise<void> {
  return mudar(parcelamento.id, () => ({ acao: "criar_parcelamento", parcelamento }));
}

/** Excluir o que com certeza não chegou ao servidor só o tira da fila. */
export function enfileirarExcluir(id: string, base?: Base): Promise<void> {
  return mudar(id, (atual, aceito) =>
    atual?.acao === "criar" && atual.talvezNoServidor === undefined
      ? null
      : { acao: "excluir", base: atual?.conflito?.lancamento ?? atual?.base ?? base ?? aceito },
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
    if (!atual || !deLancamento(atual) || !atual.exclusao || !atual.lancamento) return;
    await pedido(fila.delete(id));
    await pedido(
      fila.put({ id: novoId, acao: "criar", lancamento: { ...atual.lancamento, id: novoId }, desde: Date.now(), feitoEm: Date.now(), revisao: 1 }),
    );
  });
}

export function ordenar(lista: Lancamento[]): Lancamento[] {
  return lista.sort((a, b) => b.data.localeCompare(a.data) || b.criado_em.localeCompare(a.criado_em));
}

/** Recusado, em conflito ou vencido pela exclusão: não sobe até a pessoa decidir. */
export const esperaAPessoa = (item: ItemDaFila) => !!(item.recusa || (deLancamento(item) && (item.conflito || item.exclusao)));

/**
 * As ações de um item. O criar que talvez já esteja no servidor com uma versão anterior vai com
 * a edição atrás: no servidor, reenviar o criar devolve o que já está gravado.
 */
function acoesDo(item: ItemDaFila): Acao[] {
  // A hora da ação no aparelho; item de uma versão anterior do app não a tem e vale a da chegada.
  const acao_em = item.feitoEm ? new Date(item.feitoEm).toISOString() : undefined;
  if (item.acao === "criar_recorrencia") return [{ acao: "criar_recorrencia", recorrencia: item.recorrencia }];
  if (item.acao === "criar_parcelamento") return [{ acao: "criar_parcelamento", parcelamento: item.parcelamento }];
  if (item.acao === "excluir") return [{ acao: "excluir", id: item.id, versao: item.base?.versao, acao_em }];
  if (item.acao === "confirmar") {
    // Só os ajustes que a pessoa fez, sobre a versão que a tela mostrava, como na rota de confirmar.
    const lancamento = item.lancamento!;
    const ajustes: Ajustes = Object.fromEntries(AJUSTAVEIS.filter((campo) => lancamento[campo] !== item.base?.[campo]).map((campo) => [campo, lancamento[campo]]));
    return [{ acao: "confirmar", id: item.id, confirmacao: { versao: item.base?.versao, ...ajustes, acao_em } }];
  }
  const lancamento = { ...item.lancamento!, acao_em };
  const editar: Acao = { acao: "editar", id: item.id, alteracao: { ...alteracao(lancamento, item.base), acao_em } };
  if (item.acao === "editar") return [editar];
  const comEdicao = item.talvezNoServidor !== undefined && item.talvezNoServidor !== item.revisao;
  return comEdicao ? [{ acao: "criar", lancamento }, editar] : [{ acao: "criar", lancamento }];
}

/** Previsto que pede confirmação, atrasado ou até `contasDaSemanaDias` dias depois de hoje (`contas_da_semana_de_hoje`). */
export function naSemana(l: Pick<Lancamento, "data"> & { situacao?: Lancamento["situacao"]; automatico?: Lancamento["automatico"] }): boolean {
  const [ano, mes, dia] = hoje().split("-").map(Number);
  const ate = new Date(Date.UTC(ano, mes - 1, dia + config.contasDaSemanaDias)).toISOString().slice(0, 10);
  return l.situacao === "previsto" && !l.automatico && l.data <= ate;
}

/** Do mais antigo ao mais novo, como o servidor; o que só existe no aparelho fecha o dia. */
export const pelaData = (a: { data: string; criado_em?: string }, b: { data: string; criado_em?: string }) =>
  a.data.localeCompare(b.data) || (a.criado_em ?? "\uffff").localeCompare(b.criado_em ?? "\uffff");

async function aplicar(enviados: ItemDaFila[], resultados: Resultado[]) {
  await emTransacao("readwrite", async (fila, respostas) => {
    const guardada: Guardada<Lancamento[]> | undefined = await pedido(respostas.get(LISTA));
    let lista = guardada?.dados ?? [];
    const daHoje: Guardada<LeituraDaHoje> | undefined = await pedido(respostas.get(HOJE));
    let previstos = daHoje?.dados.contas_da_semana ?? [];
    const aceitos: Aceitos = (await pedido(respostas.get(ACEITOS))) ?? {};
    for (const [i, enviado] of enviados.entries()) {
      const { resultado, motivo, lancamento, campos, exclusao } = resultados[i];
      // Nas contas da semana, vale a versão do servidor: o confirmado ou excluído sai, e o conflito
      // fica (com a do servidor, mesmo já realizada) para o bloco mostrar "Decidir".
      if (resultado !== "recusada") {
        previstos = previstos.filter((l) => l.id !== enviado.id);
        if (lancamento && (resultado === "conflito" || naSemana(lancamento))) previstos = [...previstos, lancamento].sort(pelaData);
      }
      const guardado: ItemDaFila | undefined = await pedido(fila.get(enviado.id));
      const intacto = guardado?.revisao === enviado.revisao;
      // A regra não muda no caminho: aceita, sai da fila (as parcelas e os previstos vêm na
      // leitura dos lançamentos); recusada, espera ser descartada. Descartada no caminho, já saiu.
      if (!deLancamento(enviado)) {
        if (intacto && resultado === "recusada") await pedido(fila.put({ ...guardado, recusa: motivo ?? "recusado" }));
        else if (intacto) await pedido(fila.delete(enviado.id));
        continue;
      }
      const atual = guardado && deLancamento(guardado) ? guardado : undefined;
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
      if (lancamento) aceitos[enviado.id] = { base: lancamento, em: Date.now() };
      if (excluidoNoCaminho) await pedido(fila.put({ id: enviado.id, acao: "excluir", base: lancamento, desde: enviado.desde, revisao: 1 }));
      else if (intacto) await pedido(fila.delete(enviado.id));
      // Mudou no caminho: a mudança nova sobe sobre a versão que acabou de ser aceita (o que era
      // criar já existe lá e sobe como edição).
      else if (atual)
        await pedido(fila.put({ ...atual, acao: atual.acao === "criar" ? "editar" : atual.acao, talvezNoServidor: undefined, base: lancamento ?? atual.base }));
    }
    const recentes = Object.entries(aceitos).sort(([, a], [, b]) => b.em - a.em).slice(0, MAXIMO_DE_ACEITOS);
    await pedido(respostas.put(Object.fromEntries(recentes), ACEITOS));
    if (guardada) await pedido(respostas.put({ dados: ordenar(lista), em: guardada.em }, LISTA));
    if (daHoje) await pedido(respostas.put({ dados: { ...daHoje.dados, contas_da_semana: previstos }, em: daHoje.em }, HOJE));
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
      // A regra talvez gravada não se descarta mais no aparelho: os previstos e as parcelas viriam
      // mesmo assim. Sem rede no aparelho, o pedido nem saiu, e ela segue descartável.
      if (atual && !deLancamento(atual) && atual.talvezNoServidor === undefined && navigator.onLine)
        await pedido(fila.put({ ...atual, talvezNoServidor: enviado.revisao }));
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

const NOME_DO_PEDIDO: Record<ItemDaFila["acao"], string> = {
  criar: "este lançamento",
  editar: "este lançamento",
  excluir: "este lançamento",
  confirmar: "este lançamento",
  criar_recorrencia: "esta recorrência",
  criar_parcelamento: "este parcelamento",
};

/** Resultados de um lote; se o servidor recusa o formato do lote inteiro, manda um a um. */
async function remeterLote(remeter: Remessa, itens: ItemDaFila[]): Promise<Resultado[] | null> {
  const acoes = itens.flatMap(acoesDo);
  const resposta = await remeter(acoes);
  if (typeof resposta !== "number") return resposta.length === acoes.length ? porItem(itens, resposta) : null;
  if (resposta !== 422) return null;
  if (itens.length === 1) return [{ resultado: "recusada", motivo: `o servidor não aceitou ${NOME_DO_PEDIDO[itens[0].acao]}` }];
  const resultados: Resultado[] = [];
  for (const item of itens) {
    const um = await remeterLote(remeter, [item]);
    if (!um) return null;
    resultados.push(...um);
  }
  return resultados;
}

/** Os primeiros itens cujas ações e parcelas cabem num lote; o primeiro vai sempre. */
function ateOLimite(itens: ItemDaFila[]): ItemDaFila[] {
  let acoes = 0;
  let parcelas = 0;
  const lote: ItemDaFila[] = [];
  for (const item of itens) {
    acoes += acoesDo(item).length;
    if (item.acao === "criar_parcelamento") parcelas += item.parcelamento.parcelas;
    if (lote.length > 0 && (acoes > LIMITE_DO_LOTE || parcelas > PARCELAS_POR_LOTE)) break;
    lote.push(item);
  }
  return lote;
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
