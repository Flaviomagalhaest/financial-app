// Renovar e revogar direto no Cognito, uma chamada só, sem a biblioteca do SRP: não herdam as
// novas tentativas da biblioteca, que seguram o app por segundos sem internet, e o service worker
// renova sem levá-la junto (envio da fila em segundo plano). O SRP do login fica em cognito.ts.
import { configuracaoDoCognito, type ConfiguracaoDoCognito } from "./configuracao";
import { guardarSessao, lerSessao } from "./guarda";

/** Renova um pouco antes de vencer, para o token não vencer no caminho até a API. */
export const FOLGA_MS = 60_000;

export function venceEm(token: string): number {
  const corpo = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(atob(corpo)).exp * 1000;
}

export interface Tokens {
  acesso: string;
  renovacao: string;
}

export type MotivoDoErro = "credenciais" | "rede" | "sessao-encerrada" | "outro";

export const mensagemDeFalhaGenerica = "Não deu para entrar agora. Tente de novo em instantes.";

export class ErroDeLogin extends Error {
  constructor(
    readonly motivo: MotivoDoErro,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

const mensagens: Record<MotivoDoErro, string> = {
  credenciais: "E-mail ou senha incorretos.",
  rede: "Sem internet. Tente de novo quando a conexão voltar.",
  "sessao-encerrada": "Sua sessão foi encerrada. Entre de novo.",
  outro: mensagemDeFalhaGenerica,
};

export function erro(motivo: MotivoDoErro, mensagem = mensagens[motivo]) {
  return new ErroDeLogin(motivo, mensagem);
}

export function traduzir(codigo: string | undefined): ErroDeLogin {
  switch (codigo) {
    case "NotAuthorizedException":
    case "UserNotFoundException":
      return erro("credenciais");
    case "PasswordResetRequiredException":
      return erro("outro", "Esta senha precisa ser trocada pelo dono antes de entrar.");
    case "TooManyRequestsException":
    case "LimitExceededException":
      return erro("outro", "Muitas tentativas. Espere um pouco e tente de novo.");
    case "NetworkError":
      return erro("rede");
    default:
      return erro("outro");
  }
}

async function chamar(cfg: ConfiguracaoDoCognito, operacao: string, corpo: object) {
  let resposta: Response;
  try {
    resposta = await fetch(cfg.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": `AWSCognitoIdentityProviderService.${operacao}`,
      },
      body: JSON.stringify(corpo),
    });
  } catch {
    throw erro("rede");
  }
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw traduzir(String(dados.__type ?? dados.code ?? "").split("#").pop());
  return dados;
}

/** Novo token de acesso pelo refresh token, que não muda (sem rotação). */
export async function renovarNoCognito(cfg: ConfiguracaoDoCognito, renovacao: string): Promise<Tokens> {
  try {
    const dados = await chamar(cfg, "InitiateAuth", {
      ClientId: cfg.clienteId,
      AuthFlow: "REFRESH_TOKEN_AUTH",
      AuthParameters: { REFRESH_TOKEN: renovacao },
    });
    return { acesso: dados.AuthenticationResult.AccessToken, renovacao };
  } catch (e) {
    // Na renovação, refresh token recusado quer dizer sessão revogada ou vencida.
    throw e instanceof ErroDeLogin && e.motivo === "credenciais" ? erro("sessao-encerrada") : e;
  }
}

/** Invalida o refresh token no Cognito; o token de acesso vale até vencer. */
export async function revogarNoCognito(cfg: ConfiguracaoDoCognito, renovacao: string): Promise<void> {
  await chamar(cfg, "RevokeToken", { ClientId: cfg.clienteId, Token: renovacao });
}

/**
 * Token de acesso para o service worker, sem a sessão em memória da tela: lê a guardada e, se
 * vencer, renova e guarda. `null` sem sessão ou sem renovar; sessão encerrada só a tela trata.
 */
export async function tokenEmSegundoPlano(): Promise<string | null> {
  const sessao = await lerSessao();
  if (!sessao) return null;
  if (sessao.acessoVenceEm - FOLGA_MS > Date.now()) return sessao.tokenDeAcesso;
  const cfg = configuracaoDoCognito();
  const tokens = cfg && (await renovarNoCognito(cfg, sessao.tokenDeRenovacao).catch(() => null));
  if (!tokens) return null;
  // Saiu da conta enquanto renovava: não grava a sessão de volta.
  if ((await lerSessao())?.tokenDeRenovacao !== sessao.tokenDeRenovacao) return null;
  await guardarSessao({ ...sessao, tokenDeAcesso: tokens.acesso, acessoVenceEm: venceEm(tokens.acesso) });
  return tokens.acesso;
}
