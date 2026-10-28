// Módulo de login: o único que conhece o Cognito. O resto do app usa só isto.
export { iniciarSessao, sair, tokenDeAcesso, tokenRecusado, useSessao, type EstadoDaSessao } from "./sessao";
export { TelaDeLogin } from "./TelaDeLogin";
