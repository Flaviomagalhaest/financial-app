CREATE TABLE IF NOT EXISTS parcelamento_parte_categorias (
    parte_id uuid NOT NULL,
    categoria_id uuid NOT NULL,
    PRIMARY KEY (parte_id, categoria_id)
)
