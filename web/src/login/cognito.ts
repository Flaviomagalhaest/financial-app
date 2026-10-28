// O único arquivo do app que fala com o Cognito (ADR 0010). O SRP fica com a biblioteca;
// renovar e revogar são uma chamada só, feitas direto para não herdar as novas tentativas
// da biblioteca, que seguram o app por segundos quando não há internet.
import { AuthenticationDetails, CognitoUser, CognitoUserPool, type ICognitoStorage } from "amazon-cognito-identity-js";
import type { ConfiguracaoDoCognito } from "./configuracao";

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

function erro(motivo: MotivoDoErro, mensagem = mensagens[motivo]) {
  return new ErroDeLogin(motivo, mensagem);
}

function traduzir(codigo: string | undefined): ErroDeLogin {
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

/** A biblioteca não guarda nada: quem guarda a sessão é o módulo de login, no IndexedDB. */
function semGuardar(): ICognitoStorage {
  const itens = new Map<string, string>();
  return {
    setItem: (chave, valor) => void itens.set(chave, valor),
    getItem: (chave) => itens.get(chave) ?? null,
    removeItem: (chave) => void itens.delete(chave),
    clear: () => itens.clear(),
  };
}

export function entrarNoCognito(cfg: ConfiguracaoDoCognito, email: string, senha: string): Promise<Tokens> {
  const Storage = semGuardar();
  const pool = new CognitoUserPool({ UserPoolId: cfg.userPoolId, ClientId: cfg.clienteId, endpoint: cfg.endpoint, Storage });
  const usuario = new CognitoUser({ Username: email, Pool: pool, Storage });
  return new Promise((resolve, reject) => {
    usuario.authenticateUser(new AuthenticationDetails({ Username: email, Password: senha }), {
      onSuccess: (sessao) =>
        resolve({
          acesso: sessao.getAccessToken().getJwtToken(),
          renovacao: sessao.getRefreshToken().getToken(),
        }),
      onFailure: (e: { code?: string }) => reject(traduzir(e?.code)),
      // Os usuários são criados pelo dono já com a senha definitiva (scripts/usuarios-do-app.sh).
      newPasswordRequired: () => reject(erro("outro", "Este usuário ainda tem a senha provisória: o dono precisa definir a senha.")),
    });
  });
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
