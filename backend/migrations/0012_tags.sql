CREATE TABLE IF NOT EXISTS tags (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    arquivada_em timestamptz,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now()
)
