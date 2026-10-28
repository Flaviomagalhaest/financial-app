import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.login import VerificadorDeJwt


class Emissor:
    """Faz o papel do Cognito nos testes: assina JWTs de teste com uma chave própria."""

    emissor = "https://emissor.teste/pool"
    audiencia = "cliente-do-app"

    def __init__(self) -> None:
        self.chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def jwks(self) -> dict:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.chave.public_key()))
        return {"keys": [jwk | {"kid": "teste", "alg": "RS256", "use": "sig"}]}

    def verificador(self) -> VerificadorDeJwt:
        return VerificadorDeJwt(
            self.emissor, self.audiencia, chave_publica=lambda _token: self.chave.public_key()
        )

    def token(self, usuario: str, *, chave=None, **claims) -> str:
        agora = int(time.time())
        payload = {
            "sub": usuario,
            "iss": self.emissor,
            "client_id": self.audiencia,
            "token_use": "access",
            "iat": agora,
            "exp": agora + 900,
        } | claims
        return jwt.encode(
            {k: v for k, v in payload.items() if v is not None},
            chave or self.chave,
            algorithm="RS256",
            headers={"kid": "teste"},
        )

    def cabecalho(self, usuario: str, **claims) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(usuario, **claims)}"}
