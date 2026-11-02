# Mudar as partes pela tela do parcelamento

Type: task
Status: ready-for-human
Blocked by: —
Skills: `grilling` (HITL: decisão do dono); depois `implement`, `tdd`, `artifact-design`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #365
Origem: [ticket 139](139-partes-na-compra-parcelada.md): a tela do parcelamento só mostra as partes

## O que decidir

No 139, a tela `#/parcelamento/<id>` mostra as partes do parcelamento em percentual, sem editá-las; para mudá-las, muda-se uma parcela e escolhe-se "Todas" ou "Esta e as próximas". A API já aceita `partes` no `PATCH /api/parcelamentos/{id}` (a proporção, dividir e juntar). Depois de uma mudança com alcance, o parcelamento guarda como proporção os valores da parcela mudada, que não somam o total dele (a leitura mostra a proporção, não o valor).

- O dono quer dividir, juntar e mudar as partes também pela tela do parcelamento? Em valor (de qual parcela, ou do total) ou em percentual?
- A leitura do parcelamento deve trazer as partes já divididas pelo total, para somarem o valor dele?

## Checklist

- [ ] Dono decide
- [ ] Implementar na tela e, se for o caso, na leitura; teste de API e de navegador; verificações do projeto e PR para `main`
