// A sessão fica no IndexedDB do app instalado, nunca em cookie (ADR 0010). Banco próprio do
// login, para nenhum outro módulo do app ver o refresh token.

export interface SessaoGuardada {
  email: string;
  tokenDeAcesso: string;
  /** Em milissegundos, do `exp` do token de acesso. */
  acessoVenceEm: number;
  tokenDeRenovacao: string;
}

const BANCO = "financial-app-login";
const LOJA = "sessao";
const CHAVE = "atual";

function abrir(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const pedido = indexedDB.open(BANCO, 1);
    pedido.onupgradeneeded = () => pedido.result.createObjectStore(LOJA);
    pedido.onsuccess = () => resolve(pedido.result);
    pedido.onerror = () => reject(pedido.error);
  });
}

async function naLoja<T>(modo: IDBTransactionMode, acao: (loja: IDBObjectStore) => IDBRequest): Promise<T> {
  const banco = await abrir();
  try {
    return await new Promise<T>((resolve, reject) => {
      const transacao = banco.transaction(LOJA, modo);
      const pedido = acao(transacao.objectStore(LOJA));
      transacao.oncomplete = () => resolve(pedido.result as T);
      transacao.onerror = () => reject(transacao.error);
    });
  } finally {
    banco.close();
  }
}

export const lerSessao = () => naLoja<SessaoGuardada | undefined>("readonly", (loja) => loja.get(CHAVE));
export const guardarSessao = (sessao: SessaoGuardada) => naLoja<void>("readwrite", (loja) => loja.put(sessao, CHAVE));
export const apagarSessao = () => naLoja<void>("readwrite", (loja) => loja.delete(CHAVE));
