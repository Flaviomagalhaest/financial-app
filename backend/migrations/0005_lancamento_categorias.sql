CREATE TABLE lancamento_categorias (
    lancamento_id uuid NOT NULL,
    categoria_id uuid NOT NULL,
    PRIMARY KEY (lancamento_id, categoria_id)
)
