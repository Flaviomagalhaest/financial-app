CREATE TABLE IF NOT EXISTS edicao_em_lote_partes (
    lote_id uuid NOT NULL,
    parte_id uuid NOT NULL,
    dono_id uuid NOT NULL,
    categoria_ids_antes text NOT NULL,
    tag_ids_antes text NOT NULL,
    item_categoria_id_antes uuid,
    item_atual_categoria_id_antes uuid,
    categoria_ids_depois text NOT NULL,
    tag_ids_depois text NOT NULL,
    PRIMARY KEY (lote_id, parte_id)
)
