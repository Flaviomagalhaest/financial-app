"""Quem está chamando a API: o usuário sai de um JWT padrão, com emissor e audiência em
configuração. A API não conhece o Cognito; só o módulo de login do app conhece (ADR 0010)."""

import os
from collections.abc import Callable
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class TokenInvalido(Exception):
    pass


class EmissorFora(Exception):
    """As chaves do emissor não puderam ser buscadas: não é culpa do token."""


class VerificadorDeJwt:
    """Confere assinatura (chaves do JWKS do emissor), emissor, audiência e validade."""

    def __init__(
        self,
        emissor: str,
        audiencia: str,
        chave_publica: Callable[[str], Any] | None = None,
    ) -> None:
        self.emissor = emissor
        self.audiencia = audiencia
        if chave_publica is None:
            # JWKS no caminho padrão do OIDC; as chaves ficam em cache enquanto a Lambda vive.
            jwks = jwt.PyJWKClient(f"{emissor}/.well-known/jwks.json", lifespan=86400)
            chave_publica = lambda token: jwks.get_signing_key_from_jwt(token).key
        self._chave_publica = chave_publica

    def usuario(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self._chave_publica(token),
                algorithms=["RS256"],
                issuer=self.emissor,
                options={"require": ["exp", "iss", "sub"], "verify_aud": False},
            )
        except jwt.PyJWKClientConnectionError as erro:
            raise EmissorFora(str(erro)) from erro
        except jwt.PyJWTError as erro:
            raise TokenInvalido(str(erro)) from erro
        # Como o authorizer da HTTP API: `aud` quando existe (padrão), senão `client_id`
        # (o token de acesso do Cognito não traz `aud`).
        audiencia = claims.get("aud", claims.get("client_id"))
        if self.audiencia not in (audiencia if isinstance(audiencia, list) else [audiencia]):
            raise TokenInvalido("audiência errada")
        return claims["sub"]


def verificador_da_configuracao() -> VerificadorDeJwt | None:
    """Emissor e audiência vêm de JWT_EMISSOR e JWT_AUDIENCIA; sem eles, ninguém entra."""
    emissor, audiencia = os.environ.get("JWT_EMISSOR"), os.environ.get("JWT_AUDIENCIA")
    if not emissor or not audiencia:
        return None
    return VerificadorDeJwt(emissor.rstrip("/"), audiencia)


_bearer = HTTPBearer(auto_error=False)


def usuario_logado(
    request: Request,
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Dependência das rotas protegidas: devolve o usuário (o `sub` do token) ou 401."""
    verificador: VerificadorDeJwt | None = request.app.state.verificador
    if verificador is None:
        raise HTTPException(status_code=503, detail="login não configurado")
    if credenciais is None:
        raise _nao_autenticado("falta o token")
    try:
        return verificador.usuario(credenciais.credentials)
    except TokenInvalido:
        raise _nao_autenticado("token inválido")
    except EmissorFora:
        raise HTTPException(status_code=503, detail="chaves do login indisponíveis")


UsuarioLogado = Annotated[str, Depends(usuario_logado)]
"""Tipo do parâmetro das rotas protegidas: `def rota(usuario: UsuarioLogado)`."""


def _nao_autenticado(detalhe: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detalhe, headers={"WWW-Authenticate": "Bearer"})
