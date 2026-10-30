CREATE TABLE IF NOT EXISTS favoritos (
    id uuid PRIMARY KEY,
    estado text NOT NULL CHECK (estado IN ('favorito', 'dispensado')),
    identidade text NOT NULL,
    descricao text NOT NULL DEFAULT '',
    tipo text NOT NULL CHECK (tipo IN ('despesa', 'receita')),
    conta_id uuid NOT NULL,
    categoria_ids text NOT NULL,
    tags text NOT NULL,
    pessoa text,
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    ordem integer,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now()
)
