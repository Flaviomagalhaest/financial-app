CREATE TABLE IF NOT EXISTS faturas (
    cartao_id uuid NOT NULL,
    mes date NOT NULL,
    fechamento date,
    vencimento date,
    criado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cartao_id, mes)
)
