import { useState, type FormEvent } from "react";
import { ErroDeLogin } from "./cognito";
import { entrar } from "./sessao";

export function TelaDeLogin({ aviso }: { aviso?: string }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [entrando, setEntrando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setEntrando(true);
    setErro(null);
    try {
      await entrar(email.trim(), senha);
    } catch (e) {
      setErro(e instanceof ErroDeLogin ? e.message : "Não deu para entrar agora. Tente de novo em instantes.");
      setEntrando(false);
    }
  }

  return (
    <main className="login">
      <h1>Financial App</h1>
      {aviso && <p className="aviso">{aviso}</p>}
      <form onSubmit={(e) => void enviar(e)}>
        <label htmlFor="login-email">E-mail</label>
        <input
          id="login-email"
          type="email"
          autoComplete="username"
          inputMode="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <label htmlFor="login-senha">Senha</label>
        <input
          id="login-senha"
          type="password"
          autoComplete="current-password"
          required
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />
        {erro && (
          <p role="alert" className="erro">
            {erro}
          </p>
        )}
        <button type="submit" disabled={entrando}>
          {entrando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
