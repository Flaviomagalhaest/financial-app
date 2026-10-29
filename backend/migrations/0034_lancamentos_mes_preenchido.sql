UPDATE lancamentos SET mes = date_trunc('month', data)::date WHERE id IN (SELECT id FROM lancamentos WHERE mes IS NULL LIMIT 3000)
