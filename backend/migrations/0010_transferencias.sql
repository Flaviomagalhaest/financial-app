CREATE TABLE transferencias (
    id uuid PRIMARY KEY,
    situacao text NOT NULL CHECK (situacao IN ('previsto', 'realizado')),
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    data date NOT NULL,
    descricao text NOT NULL DEFAULT '',
    conta_origem_id uuid NOT NULL,
    conta_destino_id uuid NOT NULL,
    categoria_id uuid,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
