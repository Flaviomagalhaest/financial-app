CREATE TABLE IF NOT EXISTS parcelamento_categorias (
    parcelamento_id uuid NOT NULL,
    categoria_id uuid NOT NULL,
    PRIMARY KEY (parcelamento_id, categoria_id)
)
