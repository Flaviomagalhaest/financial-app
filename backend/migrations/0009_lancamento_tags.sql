CREATE TABLE lancamento_tags (
    lancamento_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    PRIMARY KEY (lancamento_id, tag_id)
)
