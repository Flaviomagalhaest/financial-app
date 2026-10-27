# Verificar o download da exportação no iPhone

Type: task
Status: open
Blocked by: —
Skills: `run`, `implement` (só depois que o "exportar tudo" existir)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #76
Origem: decisão do [ticket 25](25-exportacao.md): a entrega do arquivo no iPhone é de melhor esforço (abrir a URL assinada) e nunca foi verificada num aparelho

## Question

Abrir a URL assinada da exportação, a partir da PWA instalada no iPhone, deixa o casal salvar o arquivo (Arquivos ou Compartilhar)?

## Checklist

- [ ] Testar o "exportar tudo" (zip e CSV) na PWA instalada no iPhone
- [ ] Se falhar, decidir o caminho alternativo (tela de download própria, link por e-mail ou usar o backup do S3)
