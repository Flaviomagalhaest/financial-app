"""Ticket 163: cria lançamentos sintéticos no dev para passar de 1 KiB e conferir o gzip.
Uso: BASE=https://<cloudfront> TOKEN=<jwt> python3 teste163.py [criar|apagar]
Os ids ficam em teste163.ids.json para o 'apagar'. Só usa a biblioteca padrão."""
import json, os, sys, uuid, urllib.request, urllib.error
from datetime import date

BASE, TOKEN = os.environ["BASE"].rstrip("/"), os.environ["TOKEN"]
ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teste163.ids.json")

def chamar(metodo, caminho, corpo=None):
    req = urllib.request.Request(BASE + "/api" + caminho, method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            t = r.read()
            return json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        sys.exit(f"{metodo} {caminho} -> {e.code}: {e.read().decode()[:300]}")

if (sys.argv[1:] or ["criar"])[0] == "apagar":
    for i in json.load(open(ARQ))["lancamentos"]:
        chamar("DELETE", f"/lancamentos/{i}")
    print("lançamentos de teste apagados (a conta e a categoria 'teste-163' ficam)")
    sys.exit()

conta = chamar("POST", "/contas", {"nome": "teste-163", "tipo": "corrente"})
cat = chamar("POST", "/categorias", {"nome": "teste-163", "tipo": "despesa"})
ids = []
for n in range(20):
    i = str(uuid.uuid4())
    chamar("POST", "/lancamentos", {"id": i, "tipo": "despesa", "valor_centavos": 1000 + n,
        "data": date.today().isoformat(), "conta_id": conta["id"], "categoria_ids": [cat["id"]],
        "descricao": f"teste-163 lançamento sintético número {n} para passar de 1 KiB"})
    ids.append(i)
json.dump({"lancamentos": ids}, open(ARQ, "w"))
print(len(ids), "lançamentos criados")
