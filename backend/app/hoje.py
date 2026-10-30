"""A leitura da tela Hoje: tudo o que ela mostra numa chamada só, já somado no servidor. Não
calcula nada que o planejamento, as faturas ou os lançamentos já calculam: junta o que eles dizem."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import cartoes, lancamentos, planejamento
from app.banco import conectar
from app.config import valores_iniciais
from app.lancamentos import Lancamento, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class Hoje(BaseModel):
    dia: date
    mes: str
    # A soma dos itens do planejamento do mês.
    planejado_centavos: int
    ainda_da_para_gastar_centavos: int
    ajustes_de_fatura_centavos: int
    a_escolher: list[planejamento.AEscolher]
    # Os lançamentos de `a_escolher`, para a tela nomear cada um sem outra leitura.
    lancamentos_a_escolher: list[Lancamento]
    # Os previstos atrasados (`atrasado`) e os da semana, do mais antigo ao mais novo.
    contas_da_semana: list[Lancamento]
    # As faturas fechadas, não pagas, com vencimento vencido ou dentro da semana.
    faturas_que_vencem: list[cartoes.Fatura]
    # Os itens do planejamento a partir de `itensEmDestaqueNaHojePercentual`, do mais cheio ao menos.
    itens_em_destaque: list[planejamento.ItemDoPlanejamento]


def _faturas_que_vencem(conn, ate: date) -> list[cartoes.Fatura]:
    titulares = [
        id
        for (id,) in conn.execute(
            "SELECT id FROM cartoes WHERE titular_id IS NULL AND arquivado_em IS NULL"
        )
    ]
    que_vencem = [
        f
        for titular in titulares
        for f in cartoes._faturas(conn, titular)
        if f.situacao == "fechada" and f.vencimento and f.vencimento <= ate
    ]
    return sorted(que_vencem, key=lambda f: (f.vencimento, f.cartao_id, f.mes))


@router.get("/hoje", response_model=Hoje, operation_id="ler_hoje")
def ler_hoje(usuario: UsuarioLogado, request: Request) -> Hoje:
    config = valores_iniciais()
    dia = lancamentos.hoje()
    mes = f"{dia.year}-{dia.month:02d}"
    with conectar(url_do_banco(request)) as conn:
        plano = planejamento._ler(conn, mes)
        a_escolher_ids: list[UUID] = [a.lancamento_id for a in plano.a_escolher]
        return Hoje(
            dia=dia,
            mes=mes,
            planejado_centavos=sum(i.planejado_centavos for i in plano.itens),
            ainda_da_para_gastar_centavos=plano.ainda_da_para_gastar_centavos,
            ajustes_de_fatura_centavos=plano.ajustes_de_fatura_centavos,
            a_escolher=plano.a_escolher,
            lancamentos_a_escolher=lancamentos.por_ids(conn, a_escolher_ids),
            contas_da_semana=lancamentos.contas_da_semana_de_hoje(conn),
            faturas_que_vencem=_faturas_que_vencem(
                conn, dia + timedelta(days=config["contasDaSemanaDias"])
            ),
            itens_em_destaque=sorted(
                (
                    i
                    for i in plano.itens
                    if i.percentual >= config["itensEmDestaqueNaHojePercentual"]
                ),
                key=lambda i: -i.percentual,
            ),
        )
