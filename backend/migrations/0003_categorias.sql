CREATE TABLE categorias (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    tipo text NOT NULL CHECK (tipo IN ('despesa', 'receita', 'transferencia')),
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now()
)
