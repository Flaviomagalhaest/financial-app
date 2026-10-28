/** User pool e cliente do ambiente, gravados no build (o deploy lê as saídas da pilha de dados). */
export interface ConfiguracaoDoCognito {
  userPoolId: string;
  clienteId: string;
  /** Só para o Cognito falso dos testes; o padrão é o endpoint da região do user pool. */
  endpoint: string;
}

export function configuracaoDoCognito(): ConfiguracaoDoCognito | null {
  const { VITE_COGNITO_USER_POOL_ID: userPoolId, VITE_COGNITO_CLIENTE_ID: clienteId } = import.meta.env;
  if (!userPoolId || !clienteId) return null;
  const regiao = userPoolId.split("_")[0];
  const endpoint = import.meta.env.VITE_COGNITO_ENDPOINT || `https://cognito-idp.${regiao}.amazonaws.com/`;
  return { userPoolId, clienteId, endpoint };
}
