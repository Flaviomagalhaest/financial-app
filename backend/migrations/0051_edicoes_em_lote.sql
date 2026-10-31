CREATE TABLE IF NOT EXISTS edicoes_em_lote (
    id uuid PRIMARY KEY,
    resumo text NOT NULL,
    situacao text NOT NULL CHECK (situacao IN ('aplicando', 'aplicada', 'cancelada', 'desfeita')),
    lancamentos integer NOT NULL DEFAULT 0,
    recusa text,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    desfeita_por text,
    desfeita_em timestamptz
)
