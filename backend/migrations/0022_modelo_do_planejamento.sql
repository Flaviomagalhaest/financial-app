CREATE TABLE IF NOT EXISTS modelo_do_planejamento (
    categoria_id uuid PRIMARY KEY,
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
