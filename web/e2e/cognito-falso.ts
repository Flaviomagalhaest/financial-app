// Cognito de mentira para os testes de navegador e o desenvolvimento local: responde às
// chamadas que o módulo de login faz (SRP, renovação e revogação), assina os JWTs com uma
// chave gerada na partida e serve o JWKS para a API conferir. Não confere a senha: o SRP
// de verdade é do Cognito; aqui só o e-mail decide quem entra.
// Uso: node e2e/cognito-falso.ts   (porta 9230)
import { generateKeyPairSync, randomBytes, sign } from "node:crypto";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";

export const porta = 9230;
export const userPoolId = "sa-east-1_teste";
export const clienteId = "cliente-de-teste";
export const endpoint = `http://127.0.0.1:${porta}/`;
export const emissor = `http://127.0.0.1:${porta}/${userPoolId}`;
export const usuarios: Record<string, string> = {
  "flavio@teste.com": "sub-flavio",
  "esposa@teste.com": "sub-esposa",
};

/** O que o dono faria com `AdminUserGlobalSignOut`: derruba as sessões do e-mail. */
export async function desconectar(email: string) {
  await fetch(`${endpoint}_teste/desconectar`, { method: "POST", body: email });
}

/** Quantas renovações o falso atendeu desde a partida. */
export async function renovacoes(): Promise<number> {
  return Number(await (await fetch(`${endpoint}_teste/renovacoes`)).text());
}

function servir() {
  const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwks = { keys: [{ ...publicKey.export({ format: "jwk" }), kid: "falso", alg: "RS256", use: "sig" }] };
  const emailDoSub = Object.fromEntries(Object.entries(usuarios).map(([e, s]) => [s, e]));
  const sessoes = new Map<string, { sub: string; ativa: boolean }>();
  let totalDeRenovacoes = 0;

  const b64 = (dados: object) => Buffer.from(JSON.stringify(dados)).toString("base64url");
  const jwt = (claims: object) => {
    const corpo = `${b64({ alg: "RS256", kid: "falso", typ: "JWT" })}.${b64(claims)}`;
    return `${corpo}.${sign("RSA-SHA256", Buffer.from(corpo), privateKey).toString("base64url")}`;
  };
  const tokens = (sub: string) => {
    const agora = Math.floor(Date.now() / 1000);
    const comum = { sub, iss: emissor, iat: agora, exp: agora + 900 };
    return {
      AccessToken: jwt({ ...comum, client_id: clienteId, token_use: "access", username: sub }),
      IdToken: jwt({ ...comum, aud: clienteId, token_use: "id", email: emailDoSub[sub] }),
      ExpiresIn: 900,
      TokenType: "Bearer",
    };
  };
  const recusa = (mensagem: string) => ({ status: 400, corpo: { __type: "NotAuthorizedException", message: mensagem } });

  function cognito(operacao: string, pedido: any): { status: number; corpo: object } {
    const params = pedido.AuthParameters ?? {};
    if (pedido.ClientId !== clienteId) return { status: 400, corpo: { __type: "ResourceNotFoundException" } };
    if (operacao === "InitiateAuth" && pedido.AuthFlow === "USER_SRP_AUTH") {
      const sub = usuarios[params.USERNAME];
      if (!sub) return recusa("Incorrect username or password.");
      return {
        status: 200,
        corpo: {
          ChallengeName: "PASSWORD_VERIFIER",
          ChallengeParameters: {
            SALT: randomBytes(16).toString("hex"),
            SRP_B: randomBytes(128).toString("hex"),
            SECRET_BLOCK: randomBytes(32).toString("base64"),
            USER_ID_FOR_SRP: sub,
            USERNAME: sub,
          },
        },
      };
    }
    if (operacao === "RespondToAuthChallenge") {
      const sub = pedido.ChallengeResponses?.USERNAME;
      if (!emailDoSub[sub]) return recusa("Incorrect username or password.");
      const renovacao = randomBytes(24).toString("hex");
      sessoes.set(renovacao, { sub, ativa: true });
      return { status: 200, corpo: { AuthenticationResult: { ...tokens(sub), RefreshToken: renovacao } } };
    }
    if (operacao === "InitiateAuth" && pedido.AuthFlow === "REFRESH_TOKEN_AUTH") {
      const sessao = sessoes.get(params.REFRESH_TOKEN);
      if (!sessao?.ativa) return recusa("Refresh Token has been revoked");
      totalDeRenovacoes++;
      return { status: 200, corpo: { AuthenticationResult: tokens(sessao.sub) } };
    }
    if (operacao === "RevokeToken") {
      const sessao = sessoes.get(pedido.Token);
      if (sessao) sessao.ativa = false;
      return { status: 200, corpo: {} };
    }
    return { status: 400, corpo: { __type: "InvalidParameterException", message: operacao } };
  }

  function responder(res: ServerResponse, status: number, corpo: string, tipo = "application/json") {
    res.writeHead(status, {
      "Content-Type": tipo,
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    });
    res.end(corpo);
  }

  createServer(async (req: IncomingMessage, res: ServerResponse) => {
    let texto = "";
    for await (const parte of req) texto += parte;
    const caminho = req.url ?? "/";
    if (req.method === "OPTIONS") return responder(res, 204, "");
    if (req.method === "GET" && caminho === `/${userPoolId}/.well-known/jwks.json`) {
      return responder(res, 200, JSON.stringify(jwks));
    }
    if (caminho === "/_teste/desconectar") {
      for (const sessao of sessoes.values()) if (sessao.sub === usuarios[texto]) sessao.ativa = false;
      return responder(res, 200, "ok", "text/plain");
    }
    if (caminho === "/_teste/renovacoes") return responder(res, 200, String(totalDeRenovacoes), "text/plain");
    const alvo = String(req.headers["x-amz-target"] ?? "");
    if (req.method === "POST" && alvo.startsWith("AWSCognitoIdentityProviderService.")) {
      const { status, corpo } = cognito(alvo.split(".")[1], JSON.parse(texto || "{}"));
      return responder(res, status, JSON.stringify(corpo), "application/x-amz-json-1.1");
    }
    responder(res, 404, "{}");
  }).listen(porta, "127.0.0.1", () => console.log(`Cognito falso em ${endpoint} (emissor ${emissor})`));
}

if (process.argv[1]?.endsWith("cognito-falso.ts")) servir();
