# Estorno de uma parte e de todas as parcelas

Type: task
Status: ready-for-agent
Blocked by: 133, 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #326
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O estorno passa a ser de uma parte da compra e, na compra parcelada, de uma parcela ou de todas.

## Checklist

- [ ] Compra com partes: o estorno escolhe a parte, herda as categorias e tags dela e vai até o valor dela
- [ ] Ocorrência da recorrência com partes (ticket 140): o estorno é de uma parte da ocorrência (as partes do lançamento, não as da regra), como na compra à vista
- [ ] Compra parcelada (com ou sem partes): "Só esta parcela" ou "Todas as parcelas"; "Todas" cria um estorno só, ligado ao parcelamento (ou à parte dele), até a soma das parcelas menos o já estornado, preenchido com esse restante
- [ ] O estorno de todas conta inteiro no mês da fatura em que aparece
- [ ] O caso "o banco antecipa e depois estorna" é a quitação que já existe seguida do estorno de todas; sem atalho
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q30, Q37, Q41 e Q42 do ticket 94; adendo da ADR 0016.
- O 137 deixou o estorno de compra com partes recusado na API ("o estorno de uma parte da compra ainda não existe", em `_conferir_estorno`) e sem "Estornar" na tela (`podeEstornar`); dividir uma compra que já tem estorno também é recusado. Este ticket tira as duas travas.
- O 140 deixou a ocorrência da recorrência com partes como a compra à vista com partes: cada uma tem as partes dela em `lancamento_partes`, e a mesma trava (`_conferir_estorno`) recusa o estorno. O teste `test_o_estorno_de_uma_ocorrencia_com_partes_espera_o_estorno_de_uma_parte` (`backend/tests/test_partes_na_recorrencia.py`) prende a trava e muda junto com ela.
