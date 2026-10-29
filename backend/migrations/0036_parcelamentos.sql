CREATE TABLE IF NOT EXISTS parcelamentos (
    id uuid PRIMARY KEY,
    tipo text NOT NULL CHECK (tipo IN ('despesa')),
    valor_total_centavos bigint NOT NULL CHECK (valor_total_centavos > 0),
    parcelas integer NOT NULL CHECK (parcelas > 1),
    data date NOT NULL,
    automatico boolean NOT NULL,
    descricao text NOT NULL DEFAULT '',
    conta_id uuid NOT NULL,
    pessoa text,
    geradas integer NOT NULL DEFAULT 0,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
