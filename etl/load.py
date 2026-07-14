"""Extrai os zips e registra views DuckDB sobre os CSVs.

Tudo é lido como VARCHAR. O cast vem depois, em SQL, porque deixar o DuckDB
adivinhar tipo é como o pipeline passa a carregar lixo em silêncio quando a Receita
muda o layout — e ela muda.
"""

import datetime as dt
import re
import zipfile
from pathlib import Path

from . import config
from .layout import ATUAL as layout


def extrair(extracao: str) -> None:
    """Descompacta os zips em CSV_DIR/<extracao>/<tabela>/."""
    origem = config.ZIP_DIR / extracao
    for tabela, spec in layout.ARQUIVOS.items():
        destino = config.CSV_DIR / extracao / tabela
        destino.mkdir(parents=True, exist_ok=True)
        for nome_zip in spec["zips"]:
            caminho = origem / nome_zip
            with zipfile.ZipFile(caminho) as zf:
                for info in zf.infolist():
                    saida = destino / info.filename
                    if saida.exists() and saida.stat().st_size == info.file_size:
                        continue
                    print(f"  {nome_zip:26} -> {info.filename}", flush=True)
                    zf.extract(info, destino)


def data_extracao(extracao: str) -> dt.date:
    """Lê a data real da extração do nome interno do arquivo.

    A Receita codifica a data no nome (F.K03200$Z.D60613.CNAECSV -> 2026-06-13):
    D + último dígito do ano + MM + DD. É a data que vai em toda mensagem ao
    assinante (RF-3), então ela vem da fonte, não de um palpite sobre a pasta.
    """
    pasta = config.CSV_DIR / extracao / "cnaes"
    arquivos = list(pasta.glob(layout.ARQUIVOS["cnaes"]["glob"]))
    if not arquivos:
        raise RuntimeError(f"nenhum CSV de cnaes em {pasta} — rodou extrair()?")

    m = re.search(r"\.D(\d)(\d{2})(\d{2})\.", arquivos[0].name)
    if not m:
        raise RuntimeError(f"nao achei a data no nome {arquivos[0].name}")

    digito_ano, mes, dia = m.group(1), int(m.group(2)), int(m.group(3))
    ano_pasta = int(extracao[:4])
    # O nome só traz o último dígito do ano; a pasta traz o ano cheio. Se não
    # baterem, a pasta e o conteúdo estão em desacordo e é melhor parar.
    if ano_pasta % 10 != int(digito_ano):
        raise RuntimeError(
            f"ano do arquivo ({digito_ano}) nao bate com a pasta ({ano_pasta})"
        )

    data = dt.date(ano_pasta, mes, dia)
    if data.strftime("%Y-%m") != extracao:
        raise RuntimeError(f"data {data} fora do mes da extracao {extracao}")
    return data


def _colunas_sql(colunas: list[str]) -> str:
    return ", ".join(f"'{c}': 'VARCHAR'" for c in colunas)


def criar_views(con, extracao: str) -> None:
    """Materializa cada tabela em Parquet (uma vez) e registra views sobre eles.

    Por que Parquet no meio, e não views direto sobre o CSV:

    1. O decoder CP1252 da extensão `encodings` no DuckDB 1.5.4 tem um bug de
       pushdown: queries com filtro + projeção parcial sobre o scan completo
       estouram com "Attempted to access index N within vector of size M".
       A materialização decodifica com `SELECT *` — sem filtro, sem projeção —
       que é o caminho que funciona, e todas as queries do pipeline passam a
       rodar no leitor nativo de Parquet.
    2. Decodificar 26 GB de CSV custa minutos; sem staging, CADA query (novas,
       sanity, análises) pagava esse custo de novo.

    O `.tmp` + rename dá atomicidade: um processo morto no meio da escrita não
    deixa um parquet incompleto passando por staging pronto.
    """
    opts = layout.CSV_OPTS
    for tabela, spec in layout.ARQUIVOS.items():
        padrao = (config.CSV_DIR / extracao / tabela / spec["glob"]).as_posix()
        stg = config.STAGING_DIR / extracao / f"{tabela}.parquet"
        if not stg.exists():
            stg.parent.mkdir(parents=True, exist_ok=True)
            print(f"  staging {tabela}...", flush=True)
            tmp = stg.with_name(stg.name + ".tmp")
            con.execute(f"""
                COPY (
                    SELECT * FROM read_csv(
                        '{padrao}',
                        columns = {{{_colunas_sql(spec["colunas"])}}},
                        delim = '{opts["delim"]}',
                        header = {str(opts["header"]).lower()},
                        quote = '{opts["quote"]}',
                        escape = '{opts["escape"]}',
                        encoding = '{opts["encoding"]}',
                        ignore_errors = false
                    )
                ) TO '{tmp.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)
            tmp.replace(stg)
        con.execute(f"""
            CREATE OR REPLACE VIEW {tabela} AS SELECT * FROM '{stg.as_posix()}'
        """)


def preparar(extracao: str):
    """Extrai, abre a conexão e registra as views. Devolve (con, data_extracao)."""
    config.ensure_dirs()
    extrair(extracao)
    con = config.duckdb_connect()
    criar_views(con, extracao)
    return con, data_extracao(extracao)
