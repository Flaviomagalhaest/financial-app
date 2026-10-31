CREATE TABLE IF NOT EXISTS filtros_salvos (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    criterios text NOT NULL,
    ordem text NOT NULL,
    periodo_relativo text,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
