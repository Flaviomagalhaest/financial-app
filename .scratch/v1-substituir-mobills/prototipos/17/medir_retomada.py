#!/usr/bin/env python3
"""Mede os segundos da primeira conexão + SELECT 1 depois de um período ocioso.

Uso (credenciais AWS reais do dono; região us-east-2 por padrão,
troque com MEDIR_REGIAO=sa-east-1):
  pip install boto3 'psycopg[binary]'
  python3 medir_retomada.py dsql   <endpoint-do-cluster>
  python3 medir_retomada.py aurora <endpoint> <usuario> <senha> [banco]

Rode uma vez com o banco quente (linha de base) e depois de esperar:
  DSQL:   2 h e uma noite sem conexões.
  Aurora: fora do escopo do ticket 17 (só volta se o DSQL cair); o modo existe no script.
Cada execução imprime uma linha CSV:
  motor,regiao,ocioso_informado,segundos_conexao,segundos_select,rtt_tcp_ms
rtt_tcp_ms é a mediana de 5 conexões TCP à porta 5432 feitas depois da medição (para não
acordar o banco antes). É a latência de rede da sua máquina até a região: subtraia de
segundos_conexao para isolar a retomada.
"""
import os, socket, statistics, sys, time
import boto3, psycopg

REGION = os.environ.get("MEDIR_REGIAO", "us-east-2")


def conectar(args):
    motor = args[0]
    if motor == "dsql":
        host = args[1]
        token = boto3.client("dsql", region_name=REGION).generate_db_connect_admin_auth_token(host, REGION)
        return psycopg.connect(host=host, user="admin", password=token, dbname="postgres", sslmode="require", connect_timeout=120)
    host, user, senha = args[1:4]
    banco = args[4] if len(args) > 4 else "postgres"
    return psycopg.connect(host=host, user=user, password=senha, dbname=banco, sslmode="require", connect_timeout=120)


def rtt_tcp_ms(args, n=5):
    host = args[1]
    amostras = []
    for _ in range(n):
        t = time.perf_counter()
        with socket.create_connection((host, 5432), timeout=30):
            amostras.append((time.perf_counter() - t) * 1000)
    return statistics.median(amostras)


ociosidade = input("Quanto tempo o banco ficou ocioso (ex.: 30min, 24h, quente)? ")
t0 = time.perf_counter()
with conectar(sys.argv[1:]) as con:
    t1 = time.perf_counter()
    con.execute("select 1").fetchone()
    t2 = time.perf_counter()
rtt = rtt_tcp_ms(sys.argv[1:])
print(f"{sys.argv[1]},{REGION},{ociosidade},{t1 - t0:.2f},{t2 - t1:.2f},{rtt:.0f}")
