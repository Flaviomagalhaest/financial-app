CREATE TABLE IF NOT EXISTS cartoes (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    dia_fechamento integer CHECK (dia_fechamento BETWEEN 1 AND 31),
    dia_vencimento integer CHECK (dia_vencimento BETWEEN 1 AND 31),
    limite_centavos bigint CHECK (limite_centavos > 0),
    mes_anterior_ao_fechamento boolean NOT NULL DEFAULT false,
    titular_id uuid,
    arquivado_em timestamptz,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now()
)
