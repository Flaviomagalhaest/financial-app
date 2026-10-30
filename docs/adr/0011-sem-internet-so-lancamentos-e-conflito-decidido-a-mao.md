---
status: accepted
---

# Sem internet, só lançamentos; conflito no mesmo campo decidido por quem mudou

Sem internet, o app só mexe em lançamentos um a um: criar (inclusive parcelado e recorrente, que vão como um pedido só e são gerados pelo servidor), editar, excluir e confirmar previsto. Planejamento, contas, cartões, categorias, tags, favoritos e mudanças de regras precisam de internet. Cada mudança leva a versão do lançamento sobre a qual foi feita. Quando outra pessoa (ou uma regra) mudou depois os mesmos campos, o servidor recusa a mudança, e ela vira um **conflito** que espera quem a fez escolher campo a campo. Campos diferentes e mudanças idênticas entram sozinhos. Quem decidiu foi o dono: mesmo sendo raro, ele prefere escolher a perder uma mudança em silêncio.

## Considered Options

- **O último a chegar sobrescreve o lançamento inteiro**: o mais simples, mas perde em silêncio a mudança do outro em campos que ele nem tocou.
- **Campo a campo com desempate automático**: nunca deixa nada parado, e a fila do Android, que sai em segundo plano, não esperaria ninguém. O dono preferiu decidir à mão o caso raro dos dois mexerem no mesmo campo.
- **Tudo funciona sem internet, regras e planejamento inclusive**: o aparelho teria de repetir as regras de fatura, de recorrência e de parcelamento, e os conflitos se espalhariam por entidades que mudam pouco.

## Consequences

- O servidor guarda, por campo do lançamento, a versão em que ele mudou pela última vez; o lançamento nasce no aparelho com identidade própria, e reenviar a fila nunca duplica.
- A fila sai em lote, na ordem das ações. Um conflito ou uma recusa (cartão arquivado, por exemplo) fica marcado no aparelho de quem fez a mudança, e o resto da fila segue. Enquanto espera, o aparelho mostra a versão do servidor.
- Exclusão vence edição: editar algo já excluído descarta a edição, com aviso e "Lançar de novo". Excluir algo que outro mudou depois é conflito.
- Mudanças feitas pelo próprio app (recorrência alterada "daqui para frente", automático que vira realizado) contam como o outro lado, e a tela de conflito diz de onde veio a mudança.
- O aviso de planejamento repete no aparelho, só para mostrar, as regras de fatura e de item do servidor ([ADR 0017](0017-aviso-de-planejamento-repete-regras-do-servidor-so-para-mostrar.md)); gravar continua sendo do servidor.
