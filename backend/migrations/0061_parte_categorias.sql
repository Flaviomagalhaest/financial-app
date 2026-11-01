CREATE TABLE IF NOT EXISTS parte_categorias (
    parte_id uuid NOT NULL,
    categoria_id uuid NOT NULL,
    PRIMARY KEY (parte_id, categoria_id)
)
