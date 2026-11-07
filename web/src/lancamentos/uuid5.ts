// uuid5 (RFC 9562) síncrono, sem dependência: o servidor liga a parte da parcela à do parcelamento por
// `uuid5(parcela_id, parte_id)` (`id_na_parcela`, ticket 190) e o aparelho repete a conta (ADR 0018).
// Síncrono porque as somas da tela o chamam; por isso não usa `crypto.subtle`.

const rotl = (x: number, n: number) => (x << n) | (x >>> (32 - n));

/** SHA-1 (FIPS 180-4) dos bytes. */
function sha1(bytes: Uint8Array): Uint8Array {
  const tamanho = Math.ceil((bytes.length + 9) / 64) * 64;
  const m = new Uint8Array(tamanho);
  m.set(bytes);
  m[bytes.length] = 0x80;
  const visao = new DataView(m.buffer);
  visao.setUint32(tamanho - 8, Math.floor((bytes.length * 8) / 2 ** 32));
  visao.setUint32(tamanho - 4, (bytes.length * 8) >>> 0);
  let h0 = 0x67452301, h1 = 0xefcdab89 | 0, h2 = 0x98badcfe | 0, h3 = 0x10325476, h4 = 0xc3d2e1f0 | 0;
  const w = new Int32Array(80);
  for (let bloco = 0; bloco < tamanho; bloco += 64) {
    for (let i = 0; i < 16; i++) w[i] = visao.getInt32(bloco + i * 4);
    for (let i = 16; i < 80; i++) w[i] = rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
    let a = h0, b = h1, c = h2, d = h3, e = h4;
    for (let i = 0; i < 80; i++) {
      const [f, k] =
        i < 20 ? [(b & c) | (~b & d), 0x5a827999] : i < 40 ? [b ^ c ^ d, 0x6ed9eba1] : i < 60 ? [(b & c) | (b & d) | (c & d), 0x8f1bbcdc] : [b ^ c ^ d, 0xca62c1d6];
      const t = (rotl(a, 5) + f + e + k + w[i]) | 0;
      e = d; d = c; c = rotl(b, 30); b = a; a = t;
    }
    h0 = (h0 + a) | 0; h1 = (h1 + b) | 0; h2 = (h2 + c) | 0; h3 = (h3 + d) | 0; h4 = (h4 + e) | 0;
  }
  const saida = new DataView(new ArrayBuffer(20));
  [h0, h1, h2, h3, h4].forEach((h, i) => saida.setInt32(i * 4, h));
  return new Uint8Array(saida.buffer);
}

const bytesDoUuid = (uuid: string) => Uint8Array.from(uuid.replace(/-/g, "").match(/../g)!.map((b) => parseInt(b, 16)));

/** `uuid.uuid5(namespace, nome)` do Python: SHA-1 do namespace em bytes mais o nome em UTF-8, com versão 5 e variante RFC. */
export function uuid5(namespace: string, nome: string): string {
  const ns = bytesDoUuid(namespace);
  const n = new TextEncoder().encode(nome);
  const entrada = new Uint8Array(ns.length + n.length);
  entrada.set(ns);
  entrada.set(n, ns.length);
  const h = sha1(entrada).slice(0, 16);
  h[6] = (h[6] & 0x0f) | 0x50;
  h[8] = (h[8] & 0x3f) | 0x80;
  const hex = Array.from(h, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** O id da parte do parcelamento numa parcela, como `id_na_parcela` do servidor. */
export const idNaParcela = (parcelaId: string, parteId: string) => uuid5(parcelaId, parteId);
