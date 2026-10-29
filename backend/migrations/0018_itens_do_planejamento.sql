CREATE TABLE IF NOT EXISTS itens_do_planejamento (
    id uuid PRIMARY KEY,
    mes date NOT NULL,
    categoria_id uuid NOT NULL,
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
