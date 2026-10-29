CREATE TABLE IF NOT EXISTS parcelamento_tags (
    parcelamento_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    PRIMARY KEY (parcelamento_id, tag_id)
)
