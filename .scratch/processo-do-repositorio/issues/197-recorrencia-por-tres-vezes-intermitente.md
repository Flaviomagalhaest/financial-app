# Teste da recorrência por três vezes falha de vez em quando

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #498
Origem: [ticket 187](../../v1-substituir-mobills/issues/187-conta-em-todas-vai-para-o-parcelamento.md): a suíte inteira do backend falhou uma vez em `tests/test_recorrencias.py::test_recorrencia_por_tres_vezes_para_na_terceira_mesmo_com_horizonte_sobrando` (em 07/11/2026, com `pytest -x`), e passou isolada e na execução seguinte da suíte. O diff do ticket 187 não mexe em recorrências.

## O problema

O teste cria uma recorrência a partir de 15/11/2026, a cada 6 meses, por 3 vezes, sem fixar o "hoje". A suspeita é a dependência do relógio real ou de estado deixado por outro teste. A mensagem da falha não ficou registrada (`pytest -q -x | tail`).

## Diagnóstico (sessão de 07/11/2026)

Não reproduzido. Rodado em 07/11/2026: o teste isolado 15 vezes, `tests/test_recorrencias.py` inteiro 3 vezes e a suíte completa 1 vez (890 passaram), tudo com Postgres local.

Hipóteses descartadas pela leitura do código:
- **Relógio real**: o arquivo fixa `lancamentos.hoje` (autouse, `HOJE = 28/10/2026`). A geração (`horizonte()`, `_gerar_um_lote`) e a listagem (`inicio_da_janela`, `ler_lancamentos`) leem `lancamentos.hoje()` pelo módulo, então o monkeypatch vale. Os únicos `from app.lancamentos import hoje` estão em `filtros_salvos.py` e `favoritos.py`, fora desse caminho. O horizonte (24 meses) cobre 15/11/2027 com folga.
- **Geração assíncrona**: `criar` gera em lotes de forma síncrona antes de responder.
- **Ordem da listagem**: `data DESC, criado_em DESC, id` com três datas distintas é determinística.

Resta a falha que não deixou mensagem (`SerializationFailure` entre lotes, carga do banco no CI/ambiente). Sem a mensagem não há causa a corrigir.

## Checklist

- [x] Reproduzir (não reproduz: ver acima)
- [ ] Achar a causa e corrigir o teste ou o código, sem desligar o teste — **precisa da mensagem da próxima falha** (`pytest -x --tb=short`, sem `| tail`)
- [ ] Verificações do projeto e PR para `main`

Fechar como `wontfix` se não voltar a falhar nas próximas semanas.
