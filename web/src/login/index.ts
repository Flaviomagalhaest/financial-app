// Módulo de login: o único que conhece o Cognito. O resto do app usa só isto; o envio da fila no
// service worker importa só o renovacao.ts, que não traz React nem a biblioteca do SRP.
export { iniciarSessao, sair, tokenDeAcesso, tokenRecusado, useSessao } from "./sessao";
export { TelaDeLogin } from "./TelaDeLogin";
