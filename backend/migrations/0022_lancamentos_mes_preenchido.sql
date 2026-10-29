UPDATE lancamentos SET mes = date_trunc('month', data)::date WHERE mes IS NULL
