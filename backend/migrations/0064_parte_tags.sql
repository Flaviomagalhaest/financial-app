CREATE TABLE IF NOT EXISTS parte_tags (
    parte_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    PRIMARY KEY (parte_id, tag_id)
)
