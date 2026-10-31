CREATE INDEX ASYNC IF NOT EXISTS lancamentos_por_conta_e_valor ON lancamentos (conta_id, valor_centavos)
