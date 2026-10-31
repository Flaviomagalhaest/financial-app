ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS excluido_pela_regra boolean NOT NULL DEFAULT false
