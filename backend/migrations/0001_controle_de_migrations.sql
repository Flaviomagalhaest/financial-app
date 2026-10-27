CREATE TABLE controle_de_migrations (
    nome text PRIMARY KEY,
    aplicada_em timestamptz NOT NULL DEFAULT now()
)
