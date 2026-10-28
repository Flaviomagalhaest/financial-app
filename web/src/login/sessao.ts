// A sessão do aparelho: entra uma vez e fica por anos (refresh token de 10 anos), com um token
// de acesso de 15 minutos renovado quando precisa. Sem internet, a sessão continua: o app segue
// usável com o acesso vencido e renova quando a rede volta (ADR 0010).
import { useSyncExternalStore } from "react";
import { entrarNoCognito, ErroDeLogin, renovarNoCognito, revogarNoCognito } from "./cognito";
import { configuracaoDoCognito } from "./configuracao";
import { apagarSessao, guardarSessao, lerSessao, type SessaoGuardada } from "./guarda";

export type EstadoDaSessao =
  | { tipo: "carregando" }
  | { tipo: "fora"; aviso?: string }
  | { tipo: "dentro"; email: string };

/** Renova um pouco antes de vencer, para o token não vencer no caminho até a API. */
const FOLGA_MS = 60_000;

let estado: EstadoDaSessao = { tipo: "carregando" };
let atual: SessaoGuardada | null = null;
let renovando: Promise<string | null> | null = null;
const ouvintes = new Set<() => void>();

function mudar(novo: EstadoDaSessao) {
  estado = novo;
  ouvintes.forEach((ouvinte) => ouvinte());
}

function venceEm(token: string): number {
  const corpo = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(atob(corpo)).exp * 1000;
}

function exigirConfiguracao() {
  const cfg = configuracaoDoCognito();
  if (!cfg) throw new ErroDeLogin("outro", "O login não está configurado nesta versão do app.");
  return cfg;
}

/** Lê a sessão guardada no aparelho; chamada uma vez, ao abrir o app. */
export async function iniciarSessao(): Promise<void> {
  atual = (await lerSessao().catch(() => undefined)) ?? null;
  mudar(atual ? { tipo: "dentro", email: atual.email } : { tipo: "fora" });
}

/** Lança `ErroDeLogin` com a mensagem para mostrar quando não entra. */
export async function entrar(email: string, senha: string): Promise<void> {
  const tokens = await entrarNoCognito(exigirConfiguracao(), email, senha);
  atual = {
    email,
    tokenDeAcesso: tokens.acesso,
    acessoVenceEm: venceEm(tokens.acesso),
    tokenDeRenovacao: tokens.renovacao,
  };
  await guardarSessao(atual);
  // Pede ao navegador para não apagar o IndexedDB quando faltar espaço.
  void navigator.storage?.persist?.().catch(() => false);
  mudar({ tipo: "dentro", email });
}

/** Apaga a sessão do aparelho e, com internet, revoga o refresh token no Cognito. */
export async function sair(): Promise<void> {
  const sessao = atual;
  atual = null;
  await apagarSessao();
  mudar({ tipo: "fora" });
  const cfg = configuracaoDoCognito();
  if (sessao && cfg) await revogarNoCognito(cfg, sessao.tokenDeRenovacao).catch(() => undefined);
}

/**
 * Token de acesso para a API, renovado se estiver vencendo. `null` quando não há sessão ou
 * quando não deu para renovar (sem internet): a sessão continua e a chamada vai sem token.
 */
export function tokenDeAcesso(): Promise<string | null> {
  if (!atual) return Promise.resolve(null);
  if (atual.acessoVenceEm - FOLGA_MS > Date.now()) return Promise.resolve(atual.tokenDeAcesso);
  if (!navigator.onLine) return Promise.resolve(null);
  renovando ??= renovar(atual).finally(() => (renovando = null));
  return renovando;
}

async function renovar(sessao: SessaoGuardada): Promise<string | null> {
  const cfg = configuracaoDoCognito();
  if (!cfg) return null;
  try {
    const tokens = await renovarNoCognito(cfg, sessao.tokenDeRenovacao);
    if (atual !== sessao) return null; // saiu enquanto renovava
    atual = { ...sessao, tokenDeAcesso: tokens.acesso, acessoVenceEm: venceEm(tokens.acesso) };
    await guardarSessao(atual);
    return atual.tokenDeAcesso;
  } catch (erro) {
    // Refresh token revogado (o dono desconectou as sessões) ou vencido: só aí se entra de novo.
    if (erro instanceof ErroDeLogin && erro.motivo === "sessao-encerrada" && atual === sessao) {
      atual = null;
      await apagarSessao();
      mudar({ tipo: "fora", aviso: erro.message });
    }
    return null;
  }
}

/** A API recusou este token (relógio do aparelho errado, por exemplo): renova na próxima chamada. */
export function tokenRecusado(token: string): void {
  // Muda no lugar: uma renovação em andamento compara a sessão por identidade.
  if (atual?.tokenDeAcesso === token) atual.acessoVenceEm = 0;
}

function inscrever(ouvinte: () => void) {
  ouvintes.add(ouvinte);
  return () => void ouvintes.delete(ouvinte);
}

export function useSessao(): EstadoDaSessao {
  return useSyncExternalStore(inscrever, () => estado);
}
