CREATE TABLE IF NOT EXISTS recorrencias (
    id uuid PRIMARY KEY,
    tipo text NOT NULL CHECK (tipo IN ('despesa', 'receita')),
    valor_centavos bigint NOT NULL CHECK (valor_centavos > 0),
    tipo_do_valor text NOT NULL CHECK (tipo_do_valor IN ('fixo', 'estimado')),
    automatico boolean NOT NULL,
    descricao text NOT NULL DEFAULT '',
    conta_id uuid NOT NULL,
    inicio date NOT NULL,
    a_cada integer NOT NULL CHECK (a_cada > 0),
    unidade text NOT NULL CHECK (unidade IN ('semanas', 'meses')),
    ate date,
    vezes integer CHECK (vezes > 0),
    geradas integer NOT NULL DEFAULT 0,
    criado_por text NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    alterado_por text NOT NULL,
    alterado_em timestamptz NOT NULL DEFAULT now()
)
