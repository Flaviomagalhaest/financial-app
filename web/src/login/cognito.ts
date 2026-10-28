// O login com SRP, o único ponto do app que usa a biblioteca do Cognito (ADR 0010). Renovar e
// revogar ficam em renovacao.ts, sem a biblioteca.
import { AuthenticationDetails, CognitoUser, CognitoUserPool, type ICognitoStorage } from "amazon-cognito-identity-js";
import type { ConfiguracaoDoCognito } from "./configuracao";
import { erro, traduzir, type Tokens } from "./renovacao";

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
