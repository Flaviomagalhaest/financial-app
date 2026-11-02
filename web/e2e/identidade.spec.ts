import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { identidadeDe } from "../src/dados/identidade";

// Os mesmos vetores de `backend/tests/test_favoritos.py`: servidor e app geram a mesma identidade.
const vetores = JSON.parse(readFileSync(new URL("../../docs/vetores/identidade.json", import.meta.url), "utf-8"));
const sem = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().replace(/\(\s*\d+\s*\/\s*\d+\s*\)/g, " ").split(/\s+/).filter(Boolean).join(" ");

for (const v of vetores) {
  test(`identidade: ${v.nome}`, () => {
    const e = v.entrada;
    const esperado = JSON.stringify([sem(e.descricao), e.tipo, e.conta_id, [...e.categoria_ids].sort(), e.tags.map((t: string) => t.toLowerCase()).sort(), e.pessoa]);
    expect(identidadeDe(e)).toBe(esperado);
  });
}
