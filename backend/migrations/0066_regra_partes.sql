CREATE TABLE IF NOT EXISTS regra_partes (
    id uuid PRIMARY KEY,
    regra_id uuid NOT NULL,
    ordem integer NOT NULL,
    descricao text NOT NULL DEFAULT '',
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    pessoa text,
    item_categoria_id uuid
)
