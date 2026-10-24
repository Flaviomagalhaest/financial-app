---
status: accepted
---

# App web instalável em vez de app nativo

O app chega à web, ao Android e ao iPhone como um app web instalável (PWA) em React + TypeScript, uma só base de código, sem loja de apps, embora o dono já use Expo em outro repositório. No iPhone, um app nativo fora da loja exige um Mac e reinstalação a cada 7 dias, ou o Apple Developer a US$ 99 por ano, acima do teto de US$ 5 por mês. A PWA instalada na Tela de Início custa US$ 0 e fica isenta do apagamento de 7 dias do Safari. O preço é aceito: no iPhone não há atalho no ícone para o novo lançamento, e o lançamento feito sem internet só sobe com o app aberto.

## Considered Options

- **Expo (React Native com saída web)**: aproveita a experiência do dono, mas no iPhone cai na mesma regra da Apple (Mac e 7 dias, ou US$ 99/ano), e a saída web herda todos os limites da PWA.
- **App web empacotado com Capacitor**: reaproveita o código web, mas tem a mesma regra da Apple e um armazenamento no iPhone que o próprio Capacitor chama de transitório.

## Consequences

- O servidor é a fonte da verdade; o aparelho guarda cache e a fila de lançamentos a enviar.
- No Android, o toque longo no ícone abre direto o novo lançamento; no iPhone, a rapidez de lançar depende só do fluxo dentro do app.
- Se a PWA decepcionar no uso real, o plano B é empacotar o mesmo app web com Capacitor, sem reescrever as telas; voltar a React Native as reescreveria.
- A primeira etapa da v1 instala o app nos dois celulares e testa o offline antes de construir em cima dele.
