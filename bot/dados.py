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
    data_ext, ultima = con.execute("""
        SELECT max(data_extracao), max(semana) FROM agregados
    """).fetchone()

    return Dados(con=con, data_extracao=data_ext,
                 mes_ref=ultima.replace(day=1))


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
