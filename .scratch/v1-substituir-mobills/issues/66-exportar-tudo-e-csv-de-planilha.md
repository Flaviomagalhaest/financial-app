# "Exportar tudo" no app e CSV de planilha

Type: task
Status: ready-for-agent
Blocked by: 64, 31
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #120
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 157, 158, 163

## O que construir

O casal baixa os dados a qualquer momento.

## Checklist

- [ ] `POST /api/exportacoes` gera o backup ou o CSV e devolve URL assinada de 5 minutos; cada exportação a pedido fica registrada (quem e quando)
- [ ] CSV de lançamentos para planilha: separador `;`, vírgula decimal, UTF-8 com BOM, nomes no lugar dos ids, sem filtro por período
- [ ] Botão nas configurações, só com internet
- [ ] Habilita o [ticket 26](26-verificar-o-download-da-exportacao-no-iphone.md) (verificar o download no iPhone)
- [ ] Verificações do projeto rodando e PR aberto para `main`
