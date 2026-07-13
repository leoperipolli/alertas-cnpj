"""Agregado semanal (semana × UF × município × CNAE) — a única saída que o bot lê.

É pequeno o bastante para viver commitado no git, e é por isso que o bot não precisa
de banco, de VPS, de nada. Os 20 GB de CSV nunca saem do PC.

Duas sutilezas que, ignoradas, fazem você postar número errado por 60 dias:

1. **Extrações se sobrepõem.** Cada extração traz uma janela de 90 dias, então junho
   e julho falam das mesmas semanas de maio. A extração mais nova é a mais completa
   (empresa aberta em maio pode só aparecer no dump de junho), então na hora de mesclar
   o histórico a extração mais recente vence — não se soma, se substitui.

2. **A semana da extração está sempre incompleta.** Ela é um corte no meio da semana,
   não uma semana fechada. Postar "essa semana caiu 60%" quando na verdade faltam 4 dias
   de dados é o tipo de erro que destrói a credibilidade do bot. Por isso `semana_parcial`.
"""

import argparse
import datetime as dt
from pathlib import Path

import duckdb

from . import config, novas


def gerar(extracao: str, incluir_filiais: bool = False) -> Path:
    con, data_ext, parquet_novas = novas.gerar(extracao, incluir_filiais)

    con.execute(f"""
        CREATE OR REPLACE TABLE agg_novo AS
        SELECT
            date_trunc('week', data_abertura)::DATE AS semana,  -- segunda-feira
            uf,
            municipio_codigo,
            municipio,
            cnae_principal,
            cnae_descricao,
            count(*)::INTEGER AS contagem,
            DATE '{data_ext}'  AS data_extracao,
            -- A semana que contém a data de extração está cortada no meio.
            (date_trunc('week', data_abertura)::DATE + INTERVAL 6 DAY)::DATE
                > DATE '{data_ext}' AS semana_parcial
        FROM '{parquet_novas.as_posix()}'
        WHERE data_abertura IS NOT NULL
          AND uf IS NOT NULL
        GROUP BY ALL
    """)

    destino = config.AGREGADOS_PARQUET
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        # Mescla com o histórico: para cada chave, a extração mais recente vence.
        con.execute(f"""
            CREATE OR REPLACE TABLE agg_final AS
            SELECT * EXCLUDE (rn) FROM (
                SELECT *, row_number() OVER (
                    PARTITION BY semana, uf, municipio_codigo, cnae_principal
                    ORDER BY data_extracao DESC
                ) AS rn
                FROM (
                    SELECT * FROM agg_novo
                    UNION ALL BY NAME
                    SELECT * FROM '{destino.as_posix()}'
                )
            ) WHERE rn = 1
        """)
    else:
        con.execute("CREATE OR REPLACE TABLE agg_final AS SELECT * FROM agg_novo")

    # Escreve num temporário: gravar direto sobre o arquivo que se está lendo o corrompe.
    tmp = config.TMP_DIR / "agregados.parquet"
    con.execute(f"""
        COPY (SELECT * FROM agg_final ORDER BY semana, uf, cnae_principal)
        TO '{tmp.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    con.close()
    tmp.replace(destino)

    con2 = duckdb.connect()
    n, semanas, mb = con2.execute(f"""
        SELECT count(*), count(DISTINCT semana), 0
        FROM '{destino.as_posix()}'
    """).fetchone()
    tamanho = destino.stat().st_size / 1e6
    print(f"\nagregados: {n:,} linhas, {semanas} semanas, {tamanho:.1f} MB -> {destino}")
    if tamanho > 50:
        print("  AVISO: passou de 50 MB. Hora de cortar para uma janela de 12 meses.")
    return destino


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--extracao", required=True, help="AAAA-MM")
    p.add_argument("--incluir-filiais", action="store_true")
    args = p.parse_args()
    gerar(args.extracao, args.incluir_filiais)
