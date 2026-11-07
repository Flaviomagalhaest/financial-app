# Mudar as partes pela tela do parcelamento

Type: task
Status: claimed
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

- [x] Dono decide
- [ ] Implementar na tela e, se for o caso, na leitura; teste de API e de navegador; verificações do projeto e PR para `main`

## Decisões do dono

- **Q1**: a tela do parcelamento divide, muda e junta as partes, com o mesmo editor da tela de lançamento; no parcelamento sem partes, "Dividir em partes" ao lado das categorias.
- **Q2**: as partes se digitam em valor, somando o total ou o da parcela, pela escolha "O total / O da parcela" que a tela já tem; o app guarda a proporção.
- **Q3**: a mudança vale para todas as parcelas, inclusive as realizadas, sem confirmação só por causa das partes; a parcela com partes próprias fica, e o aviso diz quantas ficaram.
- **Q4**: a leitura do parcelamento traz as partes divididas pelo total (os centavos na maior parte, a primeira no empate), somando o valor dele; a proporção fica só no banco.
- **Q5**: ao trocar entre o total e o da parcela, as partes se convertem na proporção; ao mudar o valor, acompanham enquanto ninguém mexeu nelas.
- **Q6**: um "Salvar correção" só, num `PATCH` único, com o aviso de realizadas de sempre.
- **Q7**: o caminho pela parcela ("Todas", "Esta e as próximas") continua.
