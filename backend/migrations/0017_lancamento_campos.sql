CREATE TABLE IF NOT EXISTS lancamento_campos (
    lancamento_id uuid NOT NULL,
    campo text NOT NULL,
    versao bigint NOT NULL,
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL,
    origem text,
    PRIMARY KEY (lancamento_id, campo)
)
