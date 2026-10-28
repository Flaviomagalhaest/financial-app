CREATE TABLE IF NOT EXISTS exportacoes (
    id uuid PRIMARY KEY,
    usuario text NOT NULL,
    formato text NOT NULL,
    criada_em timestamptz NOT NULL DEFAULT now()
)
