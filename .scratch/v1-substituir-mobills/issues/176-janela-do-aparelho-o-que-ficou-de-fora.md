# Janela do aparelho: o que ficou de fora do 166

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`, `diagnosing-bugs` (o teste que falha no ambiente na nuvem)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #436
Origem: revisão do [ticket 166](166-janela-do-aparelho.md) (sub-agentes Standards e Spec): limitações da [janela do aparelho](../../../docs/adr/0024-sem-internet-so-a-janela-do-aparelho.md) que o 166 deixou registradas e testes que faltaram.

## O que construir

- **Estorno na fatura antiga**: o índice de estornos da `TelaDaFatura.tsx` junta a janela e as compras da fatura. O estorno que está nela, de uma compra que conta antes da janela e em outra fatura, aparece como "estorno de uma compra" até alguém abrir o estorno. Com internet, ler a compra (`GET /api/lancamentos/{id}`) para dar o nome.
- **O que ainda dá para estornar numa parcela**: o aparelho calcula o restante do parcelamento com as parcelas e os estornos que tem. Se a parcela está na janela e as primeiras parcelas (ou os estornos delas) estão antes dela, o restante sai maior que o do servidor. O servidor recusa com 422, e a fila mostra a recusa. Com internet, a tela do estorno de uma parcela pode ler os ligados (`GET /api/lancamentos/{id}`) mesmo com a compra no aparelho.
- **Mês que vira com conflito**: `guardarALista` (`armazem.ts`) poupa todo lançamento com item na fila, conflito incluído, mas o teste de navegador cobre só a mudança não enviada.
- **Recorrência fora da janela**: `TelaDaRecorrencia.tsx` lê do servidor o lançamento de fora da janela, sem teste de navegador. A API não gera ocorrência antes de hoje (ticket 125), então o teste precisa simular a lista sem o lançamento (`page.route`), como o `telas-leem-do-servidor.spec.ts`.
- **Edição sem `base`**: a mudança na fila sem a versão do servidor (um item de uma versão anterior do app) num lançamento que saiu da lista ainda entra no `naTela` como lançamento novo, sem os campos que só o servidor tem. Decidir se vale tratar ou registrar como aceito.
- **"Repetir último"**: o `ultimoCriado` olha a janela. O lançamento criado agora com uma data de mais de 12 meses atrás não é o último. Decidir se isso importa.
- **Teste que falha no ambiente na nuvem**: `sem-internet.spec.ts` ("a leitura da lista que a tela pediu antes da do service worker, se chega depois, não troca a guardada") falha sempre nas sessões na nuvem, também na `main` antes do 166 (`listaGuardadaTem` nunca fica `true`). Conferir se o CI passa e o que o ambiente tem de diferente.

## Checklist

- [ ] Estorno na fatura antiga mostra o nome da compra com internet, com teste de navegador
- [ ] Estorno de parcela com as primeiras parcelas fora da janela: o restante igual ao do servidor com internet, com teste
- [ ] Teste de navegador do mês que vira com conflito
- [ ] Teste de navegador da recorrência fora da janela, com e sem internet
- [ ] Edição sem `base` e "Repetir último": tratado ou registrado como aceito
- [ ] Causa da falha de `sem-internet.spec.ts` na nuvem achada e corrigida (ou registrada)
