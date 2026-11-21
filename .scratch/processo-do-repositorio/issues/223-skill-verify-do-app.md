# Skill verify-financial-app: provar a mudança no app real antes do PR

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `writing-for-agents`, `run`; apoio: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #579
Origem: conversa de 21/11 comparando as skills do Matt Pocock com o pstack da Lauren Tan. A ideia vem do `create-verification-skill` do pstack, que gera uma skill `verify-<app>` própria do projeto.

## O problema

As skills que usamos (`implement`, `tdd`, `code-review`) dão a mudança por pronta quando os testes e o CI passam. Nenhuma exige ver a mudança funcionando no app real nem reproduzir o bug antes e depois da correção. Um teste verde ou um build que passa não prova que quem usa vê o comportamento pedido no ticket.

## O que se quer

Uma skill de projeto em `.claude/skills/verify-financial-app/SKILL.md` que diz como provar uma mudança neste app:

- como subir o backend (`backend/`) e o web (`web/`) localmente, do zero num clone novo (instalar as dependências, banco, variáveis), e como parar;
- como dirigir a tela com o Playwright já instalado no ambiente, com uma captura de tela como evidência, e como chamar a API direto quando a mudança é só do backend;
- como ler o valor gravado (banco) quando a mudança é de dados;
- a regra de bug: reproduzir antes de corrigir e de novo depois, com o mesmo passo; "inconclusivo" não conta como passou;
- a regra geral: o build verde e os testes verdes não bastam como prova; a evidência vai para o ticket (seção de resolução) ou para o PR;
- o que fazer quando não dá para verificar (por exemplo, o recurso só existe no celular): dizer o que ficou sem prova e abrir ticket, nunca dar por verificado.

## Checklist

- [ ] Levantar como o app roda hoje (README, `backend/pyproject.toml`, `web/package.json`, `web/playwright.config.ts`, CI em `.github/workflows/`) e subir os dois lados num clone limpo, anotando cada passo que funcionou
- [ ] Escrever a skill com `writing-for-agents`, usando só comandos que rodaram nesta sessão
- [ ] Ligar a skill ao fluxo: o `implement` a chama antes de abrir o PR, e a `run` aponta para ela neste projeto
- [ ] Testar a skill numa mudança real ou num bug antigo já resolvido (reproduzir no commit anterior à correção e ver que some depois)
- [ ] Atualizar o `AGENTS.md` se a regra "provar no app real antes do PR" virar obrigatória (decisão do dono, se houver dúvida)
- [ ] Verificações do projeto e PR para `main`
