CREATE TABLE IF NOT EXISTS recorrencia_tags (
    recorrencia_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    PRIMARY KEY (recorrencia_id, tag_id)
)
