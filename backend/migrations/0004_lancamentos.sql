CREATE TABLE lancamentos (
    id uuid PRIMARY KEY,
    tipo text NOT NULL CHECK (tipo IN ('despesa', 'receita')),
    situacao text NOT NULL CHECK (situacao IN ('previsto', 'realizado')),
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    data date NOT NULL,
    descricao text NOT NULL DEFAULT '',
    conta_id uuid NOT NULL,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
