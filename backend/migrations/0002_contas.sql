CREATE TABLE contas (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    tipo text NOT NULL CHECK (tipo IN ('corrente', 'poupanca', 'carteira')),
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now()
)
