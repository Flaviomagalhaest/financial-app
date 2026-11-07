# Teste da recorrência por três vezes falha de vez em quando

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #498
Origem: [ticket 187](../../v1-substituir-mobills/issues/187-conta-em-todas-vai-para-o-parcelamento.md): a suíte inteira do backend falhou uma vez em `tests/test_recorrencias.py::test_recorrencia_por_tres_vezes_para_na_terceira_mesmo_com_horizonte_sobrando` (em 07/11/2026, com `pytest -x`), e passou isolada e na execução seguinte da suíte. O diff do ticket 187 não mexe em recorrências.

## O problema

O teste cria uma recorrência a partir de 15/11/2026, a cada 6 meses, por 3 vezes, sem fixar o "hoje". A suspeita é a dependência do relógio real ou de estado deixado por outro teste. A mensagem da falha não ficou registrada (`pytest -q -x | tail`).

## Checklist

- [ ] Reproduzir (a suíte em ordem, ou o teste com o relógio em datas próximas de 15/11/2026)
- [ ] Achar a causa e corrigir o teste ou o código, sem desligar o teste
- [ ] Verificações do projeto e PR para `main`
