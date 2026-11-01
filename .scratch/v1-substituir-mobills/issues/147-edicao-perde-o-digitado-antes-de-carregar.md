# A edição perde o que se digita antes de o lançamento carregar

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #343
Origem: [ticket 136](136-alcance-da-mudanca-na-parcela.md): o teste de navegador da mudança com alcance falhava às vezes por isso

## O que construir

Em `web/src/lancamentos/TelaDeLancamento.tsx`, editar um lançamento (`#/novo/<id>`) preenche o formulário uma vez, quando o lançamento aparece na lista do aparelho. Até lá, o teclado fica desativado, mas "Detalhes" já abre. A descrição, as tags, a pessoa e a data digitadas nesse meio-tempo são apagadas pelo preenchimento, e "Salvar" manda a edição sem a mudança. O teste do 136 espera o valor aparecer antes de editar; uma pessoa com a rede lenta não tem esse aviso.

## Checklist

- [x] Reproduzir num teste de navegador: abrir a edição antes de a lista carregar e digitar a descrição
- [x] "Detalhes" (e o resto do formulário) só vale depois de o lançamento carregar, como o teclado, ou o preenchimento não apaga o que já foi digitado
- [ ] Verificações do projeto e PR para `main`
