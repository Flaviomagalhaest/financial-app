CREATE TABLE IF NOT EXISTS antecipacoes (
    id uuid NOT NULL,
    lancamento_id uuid NOT NULL,
    parcelamento_id uuid NOT NULL,
    PRIMARY KEY (id, lancamento_id)
)
