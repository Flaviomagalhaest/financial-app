CREATE TABLE IF NOT EXISTS edicao_em_lote_lancamentos (
    lote_id uuid NOT NULL,
    lancamento_id uuid NOT NULL,
    versao bigint NOT NULL,
    categoria_ids_antes text NOT NULL,
    tag_ids_antes text NOT NULL,
    item_categoria_id_antes uuid,
    item_atual_categoria_id_antes uuid,
    desfazer text CHECK (desfazer IN ('desfeito', 'mudou_depois', 'excluido', 'saiu')),
    PRIMARY KEY (lote_id, lancamento_id)
)
