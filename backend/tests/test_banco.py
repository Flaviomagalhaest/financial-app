import pytest

from app import banco


class DsqlFalso:
    def __init__(self):
        self.chamadas: list[str] = []

    def generate_db_connect_auth_token(self, endpoint, regiao):
        self.chamadas.append("api")
        return "token-api"

    def generate_db_connect_admin_auth_token(self, endpoint, regiao):
        self.chamadas.append("admin")
        return "token-admin"


@pytest.fixture
def dsql(monkeypatch: pytest.MonkeyPatch):
    falso = DsqlFalso()
    conexoes: list[dict] = []
    monkeypatch.setenv("DSQL_ENDPOINT", "banco.dsql.exemplo")
    monkeypatch.setenv("AWS_REGION", "sa-east-1")
    monkeypatch.setattr(banco.boto3, "client", lambda *_a, **_k: falso)
    monkeypatch.setattr(banco.psycopg, "connect", lambda **kw: conexoes.append(kw))
    falso.conexoes = conexoes
    return falso


def test_api_entra_no_dsql_com_o_papel_proprio_e_token_comum(dsql):
    banco.conectar()

    assert dsql.chamadas == ["api"]
    assert dsql.conexoes[0]["user"] == "api"
    assert dsql.conexoes[0]["password"] == "token-api"


def test_migrations_entram_no_dsql_como_admin(dsql):
    banco.conectar(admin=True)

    assert dsql.chamadas == ["admin"]
    assert dsql.conexoes[0]["user"] == "admin"
    assert dsql.conexoes[0]["password"] == "token-admin"
