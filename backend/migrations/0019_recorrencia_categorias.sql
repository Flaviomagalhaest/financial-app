CREATE TABLE IF NOT EXISTS recorrencia_categorias (
    recorrencia_id uuid NOT NULL,
    categoria_id uuid NOT NULL,
    PRIMARY KEY (recorrencia_id, categoria_id)
)
