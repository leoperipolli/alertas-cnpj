"""Acesso ao agregado. É a única fonte de dado do bot.

O parquet é pequeno o bastante para viver no git, então o bot roda no GitHub Actions
sem banco, sem VPS, sem nada. Os 20 GB de CSV ficam no PC.
"""

import datetime as dt
from dataclasses import dataclass

import duckdb

from etl import config


@dataclass(frozen=True)
class Dados:
    con: duckdb.DuckDBPyConnection
    data_extracao: dt.date
    mes_ref: dt.date  # primeiro dia do mês mais recente com dado completo

    def q(self, sql: str, **p) -> list[tuple]:
        return self.con.execute(sql, p).fetchall()


def abrir(parquet=None) -> Dados:
    caminho = (parquet or config.AGREGADOS_PARQUET).as_posix()
    con = duckdb.connect()
    # Semanas parciais ficam de fora de TUDO que o bot vê. A semana em que a Receita
    # cortou a extração está incompleta por construção, e postar "as aberturas caíram
    # 60%" quando na verdade faltam quatro dias de dado é o jeito mais rápido de
    # destruir a credibilidade que o bot existe para construir.
    con.execute(f"""
        CREATE VIEW agregados AS
        SELECT * FROM '{caminho}' WHERE NOT semana_parcial
    """)
    data_ext = con.execute("SELECT max(data_extracao) FROM agregados").fetchone()[0]

    # O mês de referência é o último mês CALENDÁRIO FECHADO antes da extração —
    # nunca o mês corrente dela. A extração de 13/06 tem só ~1,5 semana de junho;
    # postar esse pedaço como "junho" seria dizer que o mês despencou 75%.
    # (A janela de 90 dias sempre cobre o mês anterior inteiro, então maio está
    # completo numa extração de junho.)
    mes_ref = (data_ext.replace(day=1) - dt.timedelta(days=1)).replace(day=1)

    return Dados(con=con, data_extracao=data_ext, mes_ref=mes_ref)


def total_mes(d: Dados, mes: dt.date) -> int:
    return d.q("""
        SELECT coalesce(sum(contagem), 0) FROM agregados
        WHERE date_trunc('month', semana) = $mes
    """, mes=mes)[0][0]


def por_uf(d: Dados, mes: dt.date, limite: int = 8) -> list[tuple[str, int]]:
    return d.q("""
        SELECT uf, sum(contagem)::INT FROM agregados
        WHERE date_trunc('month', semana) = $mes
        GROUP BY uf ORDER BY 2 DESC LIMIT $limite
    """, mes=mes, limite=limite)


def por_cnae(d: Dados, mes: dt.date, uf: str | None = None,
             limite: int = 8) -> list[tuple[str, int]]:
    return d.q("""
        SELECT cnae_descricao, sum(contagem)::INT FROM agregados
        WHERE date_trunc('month', semana) = $mes
          AND cnae_descricao IS NOT NULL
          AND ($uf IS NULL OR uf = $uf)
        GROUP BY 1 ORDER BY 2 DESC LIMIT $limite
    """, mes=mes, uf=uf, limite=limite)


def por_municipio(d: Dados, mes: dt.date, codigos: list[str] | None = None,
                  uf: str | None = None, limite: int = 8) -> list[tuple[str, int]]:
    return d.q("""
        SELECT municipio || '/' || uf, sum(contagem)::INT FROM agregados
        WHERE date_trunc('month', semana) = $mes
          AND municipio IS NOT NULL
          AND ($codigos IS NULL OR cnae_principal IN (SELECT unnest($codigos)))
          AND ($uf IS NULL OR uf = $uf)
        GROUP BY 1 ORDER BY 2 DESC LIMIT $limite
    """, mes=mes, codigos=codigos, uf=uf, limite=limite)


def setor_por_uf(d: Dados, mes: dt.date, codigos: list[str],
                 limite: int = 8) -> list[tuple[str, int]]:
    """Filtra por CÓDIGO, nunca por texto da descrição — ver bot/setores.py."""
    return d.q("""
        SELECT uf, sum(contagem)::INT FROM agregados
        WHERE date_trunc('month', semana) = $mes
          AND cnae_principal IN (SELECT unnest($codigos))
        GROUP BY uf ORDER BY 2 DESC LIMIT $limite
    """, mes=mes, codigos=codigos, limite=limite)


def total_por_uf(d: Dados, mes: dt.date) -> list[tuple[str, int]]:
    """Aberturas por UF, TODAS as UFs (sem LIMIT) e sem a pseudo-UF `EX` (exterior).

    Separado de `por_uf` de propósito: os cortes per capita precisam de todas as UFs
    para ranquear por habitante, e `EX` não tem população — deixá-la contamina o
    ranking (aparece com número absoluto mas sem denominador).
    """
    return d.q("""
        SELECT uf, sum(contagem)::INT FROM agregados
        WHERE date_trunc('month', semana) = $mes AND uf <> 'EX'
        GROUP BY uf ORDER BY 2 DESC
    """, mes=mes)


def setor_por_uf_completo(d: Dados, mes: dt.date,
                          codigos: list[str]) -> list[tuple[str, int]]:
    """Como `setor_por_uf`, mas TODAS as UFs e sem `EX` — para os cortes per capita
    e as razões entre setores, que ranqueiam sobre o conjunto inteiro."""
    return d.q("""
        SELECT uf, sum(contagem)::INT FROM agregados
        WHERE date_trunc('month', semana) = $mes AND uf <> 'EX'
          AND cnae_principal IN (SELECT unnest($codigos))
        GROUP BY uf ORDER BY 2 DESC
    """, mes=mes, codigos=codigos)


def location_quotient(d: Dados, mes: dt.date, min_n: int = 40,
                      min_tcn: int = 150) -> list[tuple[str, str, str, int, int, float]]:
    """Quociente locacional (LQ) por (UF, CNAE): o quanto a UF abre daquele setor
    ACIMA do que a fração nacional esperaria.

        LQ = (peso do setor na UF) / (peso do setor no Brasil)

    LQ=2 => a UF abre o dobro daquele setor, proporcionalmente, que a média. É o que
    dá o "setor-assinatura" de cada estado (Sergipe/táxi, SC/confecção...).

    Os pisos não são detalhe: sem `min_n` (aberturas do setor na UF) e `min_tcn`
    (aberturas do setor no país), o maior LQ é sempre um par UF×CNAE minúsculo — 3
    empresas num estado pequeno estouram a razão e viram um "assinatura" que é ruído.
    Devolve (uf, cnae, descrição, n, total_nacional_do_cnae, lq).
    """
    return d.q("""
        WITH est AS (
            SELECT uf, cnae_principal, any_value(cnae_descricao) AS dsc,
                   sum(contagem)::INT AS n
            FROM agregados
            WHERE date_trunc('month', semana) = $mes AND uf <> 'EX'
              AND cnae_descricao IS NOT NULL
            GROUP BY uf, cnae_principal
        ),
        tot_uf AS (SELECT uf, sum(n) AS tuf FROM est GROUP BY uf),
        tot_cn AS (SELECT cnae_principal, sum(n) AS tcn FROM est GROUP BY cnae_principal),
        tot    AS (SELECT sum(n) AS t FROM est)
        SELECT e.uf, e.cnae_principal, e.dsc, e.n, tot_cn.tcn,
               (e.n * 1.0 / tot_uf.tuf) / (tot_cn.tcn * 1.0 / tot.t) AS lq
        FROM est e
        JOIN tot_uf USING (uf)
        JOIN tot_cn USING (cnae_principal),
        tot
        WHERE e.n >= $min_n AND tot_cn.tcn >= $min_tcn
        ORDER BY lq DESC
    """, mes=mes, min_n=min_n, min_tcn=min_tcn)


def crescimento_cnae(d: Dados, mes: dt.date, anterior: dt.date,
                     minimo: int = 300) -> list[tuple[str, int, int, float]]:
    """CNAEs que mais cresceram vs o mês anterior.

    O piso de volume não é detalhe: sem ele o "maior crescimento" é sempre um CNAE
    que saiu de 1 para 4 empresas — matematicamente +300% e jornalisticamente nada.
    """
    return d.q("""
        WITH a AS (
            SELECT cnae_descricao, sum(contagem)::INT AS n FROM agregados
            WHERE date_trunc('month', semana) = $mes AND cnae_descricao IS NOT NULL
            GROUP BY 1
        ), b AS (
            SELECT cnae_descricao, sum(contagem)::INT AS n FROM agregados
            WHERE date_trunc('month', semana) = $anterior AND cnae_descricao IS NOT NULL
            GROUP BY 1
        )
        SELECT a.cnae_descricao, a.n, b.n,
               100.0 * (a.n - b.n) / b.n AS variacao
        FROM a JOIN b USING (cnae_descricao)
        WHERE a.n >= $minimo AND b.n >= $minimo
        ORDER BY variacao DESC LIMIT 5
    """, mes=mes, anterior=anterior, minimo=minimo)
