from app.config import valores_iniciais


def test_valores_iniciais_da_spec():
    valores = valores_iniciais()

    assert valores["favoritos"] == {"sugeridos": 3, "usosMinimos": 5}
    assert valores["avisoDeNaoEnviadoHoras"] == 24
    assert valores["itensEmDestaqueNaHojePercentual"] == 80
