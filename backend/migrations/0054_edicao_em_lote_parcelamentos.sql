CREATE TABLE IF NOT EXISTS edicao_em_lote_parcelamentos (
    lote_id uuid NOT NULL,
    parcelamento_id uuid NOT NULL,
    categoria_ids_antes text NOT NULL,
    tag_ids_antes text NOT NULL,
    item_categoria_id_antes uuid,
    categoria_ids_depois text NOT NULL,
    tag_ids_depois text NOT NULL,
    resultado_do_desfazer text CHECK (resultado_do_desfazer IN ('desfeito', 'mudou_depois', 'saiu')),
    PRIMARY KEY (lote_id, parcelamento_id)
)
