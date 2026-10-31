# Tela de edição descarta o dígito digitado antes de o lançamento carregar

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #290
Origem: [ticket 109](109-testes-de-navegador-sob-cpu-saturada.md) (31/10). Com a CPU saturada, o teste "criado com a resposta perdida e depois editado..." clicava "9" na tela de edição antes de a lista chegar do IndexedDB; a hidratação (`TelaDeLancamento.tsx`, `setCentavos(achado.valor_centavos)`) apagou o dígito e o "Salvar", habilitado só depois, gravou o valor antigo (R$ 0,01 em vez de 0,19). O teste passou a esperar o valor; o app não mudou.

## O que construir

Quem toca numa tecla do teclado antes de a edição carregar perde o toque sem aviso. Decidir e implementar: o teclado fica desativado até o lançamento carregar, ou a tela mostra "carregando" no lugar do valor. Em aparelho lento o carregamento pode demorar, e o toque perdido grava um valor errado.

## Checklist

- [ ] Teste de navegador que toca a tecla assim que a tela abre (sem esperar o valor) e confere que o dígito não se perde ou que o teclado está desativado
- [ ] Ajuste na `TelaDeLancamento.tsx`
- [ ] Verificações do projeto rodando e PR aberto para `main`
