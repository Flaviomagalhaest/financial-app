ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS estorno_parte_id uuid;
ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS estorno_parcelamento_id uuid
