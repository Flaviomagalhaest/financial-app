# Estorno de uma parte e de todas as parcelas

Type: task
Status: resolved
Blocked by: 133, 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #326
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O estorno passa a ser de uma parte da compra e, na compra parcelada, de uma parcela ou de todas.

## Checklist

- [x] Compra com partes: o estorno escolhe a parte, herda as categorias e tags dela e vai até o valor dela
- [x] Compra parcelada (com ou sem partes): "Só esta parcela" ou "Todas as parcelas"; "Todas" cria um estorno só, ligado ao parcelamento (ou à parte dele), até a soma das parcelas menos o já estornado, preenchido com esse restante
- [x] O estorno de todas conta inteiro no mês da fatura em que aparece
- [x] O caso "o banco antecipa e depois estorna" é a quitação que já existe seguida do estorno de todas; sem atalho
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q30, Q37, Q41 e Q42 do ticket 94; adendo da ADR 0016.
- O 137 deixou o estorno de compra com partes recusado na API ("o estorno de uma parte da compra ainda não existe", em `_conferir_estorno`) e sem "Estornar" na tela (`podeEstornar`); dividir uma compra que já tem estorno também é recusado. Este ticket tira as duas travas.

## Entregue

- **Parte**: `estorno_parte_id` (com `estorno_de` na compra). Na compra com partes a parte é obrigatória; o estorno herda categorias, tags e item dela (`acompanhar_estornos` segue a parte) e vai até o valor dela, sem passar do total da compra. A parte com estorno não some, não encolhe abaixo do estornado e as partes só se juntam sem estorno de parte. Dividir compra que já tem estorno passou a valer.
- **Todas as parcelas**: `estorno_parcelamento_id` (sem `estorno_de`), um estorno só, até `valor_total_centavos` menos o já estornado (de cada parcela e de todas), com a classificação do parcelamento (acompanhada na correção e na edição em lote). Conta inteiro no mês da fatura em que aparece e trava a exclusão do parcelamento. A antecipação seguida de estorno é a quitação mais o estorno de todas, sem atalho.
- Backup na versão 29 (migrations 0067 e 0068), `e_estorno()` em `app/partes.py` para quem soma, OpenAPI e tipos regenerados.
- Telas: "Parte estornada" (escolha da parte) e "Só esta parcela" / "Todas as parcelas" ao estornar; o restante vem do aparelho (lançamentos e parcelamentos guardados), também sem internet.
- Testes: `test_estorno_de_parte_e_de_parcelas.py`, `test_restauracao.py` (versão 27) e `e2e/estorno-de-parte-e-parcelas.spec.ts`.
- Pendência: [ticket 153](153-estorno-de-parte-e-de-parcelas-pendencias.md) (decisões provisórias, ready-for-human).
